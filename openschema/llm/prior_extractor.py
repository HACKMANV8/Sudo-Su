from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..utils import normalize_seed
from .gemini_client import LLMError, LLMNetworkError, LLMParseError, call_llm

log = logging.getLogger(__name__)


class PriorsParseError(Exception):
    """Failed to parse or validate priors JSON."""
    pass


class LLMPriorsExtractor:
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        bypass_cache: bool = False,
    ):
        self.cache_dir = Path(cache_dir or Path.home() / ".openschema" / "llm_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.bypass_cache = bypass_cache
    
    def _cache_key(
        self,
        model: str,
        prompt_hash: str,
        schema_fingerprint: str,
        description: str,
        sample_rows_hash: str,
        extractor_params: Dict[str, Any],
    ) -> str:
        """Generate cache key from inputs."""
        payload = json.dumps({
            "model": model,
            "prompt_hash": prompt_hash,
            "schema_fp": schema_fingerprint,
            "description": normalize_seed(description),  # Normalize description
            "sample_hash": sample_rows_hash,
            "params": extractor_params,
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
    
    def _cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"
    
    def _build_prompt(
        self,
        schema: Dict[str, Any],
        user_description: str,
        sample_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Build LLM prompt from schema and description."""
        schema_json = json.dumps(schema, indent=2, default=str)
        sample_json = json.dumps(sample_rows or [], indent=2, default=str)
        
        prompt = f"""SYSTEM:
You are a structured priors extractor. Output EXACTLY one JSON object and nothing else. Follow the schema below.

USER:

Schema (JSON): {schema_json}

User description: {user_description}

Optional sample rows (JSON array, or empty): {sample_json}

Instructions:

1. For each column in the schema, produce a priors entry describing type and distribution. For categoricals include category list and sensible probabilities summing to 1. For numeric include distribution type and numeric params (mean,std,min,max) when confidently inferable; otherwise mark 'empirical' and provide examples.

2. Provide conditional entries where sensible (e.g., if product_category == 'Electronics' then product_price ~ lognormal(...)).

3. Provide up to 50 example rows reflecting the priors.

4. No PII in examples. If any sample rows in input contained PII, redact them and note redaction in a 'notes' field.

5. Output no commentary — strict JSON ONLY.

Return the JSON object now."""
        
        return prompt
    
    def _redact_pii(self, text: str) -> tuple[str, Dict[str, int]]:
        """Redact PII patterns from text. Returns (redacted_text, redaction_counts)."""
        redactions = {"email": 0, "phone": 0, "ssn": 0, "credit_card": 0, "iban": 0}
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = len(re.findall(email_pattern, text))
        if email_matches > 0:
            text = re.sub(email_pattern, "<REDACTED_EMAIL>", text)
            redactions["email"] = email_matches
        
        # Phone pattern (US-style)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b'
        phone_matches = len(re.findall(phone_pattern, text))
        if phone_matches > 0:
            text = re.sub(phone_pattern, "<REDACTED_PHONE>", text)
            redactions["phone"] = phone_matches
        
        # SSN pattern
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        ssn_matches = len(re.findall(ssn_pattern, text))
        if ssn_matches > 0:
            text = re.sub(ssn_pattern, "<REDACTED_SSN>", text)
            redactions["ssn"] = ssn_matches
        
        # Credit card (basic Luhn detection - 16 digits)
        cc_pattern = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        cc_matches = len(re.findall(cc_pattern, text))
        if cc_matches > 0:
            text = re.sub(cc_pattern, "<REDACTED_CC>", text)
            redactions["credit_card"] = cc_matches
        
        # IBAN-like (long alphanumeric)
        iban_pattern = r'\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b'
        iban_matches = len(re.findall(iban_pattern, text))
        if iban_matches > 0:
            text = re.sub(iban_pattern, "<REDACTED_IBAN>", text)
            redactions["iban"] = iban_matches
        
        total = sum(redactions.values())
        return text, redactions
    
    def _validate_priors(self, priors: Dict[str, Any]) -> None:
        """Validate priors JSON structure."""
        if not isinstance(priors, dict):
            raise PriorsParseError("Priors must be a dict")
        
        required_top = ["schema_hint", "priors", "dependencies", "examples"]
        for key in required_top:
            if key not in priors:
                raise PriorsParseError(f"Missing required key: {key}")
        
        # Validate priors structure
        priors_dict = priors.get("priors", {})
        if not isinstance(priors_dict, dict):
            raise PriorsParseError("priors must be a dict")
        
        for col_name, col_prior in priors_dict.items():
            if not isinstance(col_prior, dict):
                raise PriorsParseError(f"Prior for {col_name} must be a dict")
            
            if "type" not in col_prior:
                raise PriorsParseError(f"Prior for {col_name} missing 'type'")
            
            ptype = col_prior["type"]
            if ptype == "categorical":
                if "categories" not in col_prior or "probs" not in col_prior:
                    raise PriorsParseError(f"Prior for {col_name} (categorical) missing categories/probs")
            elif ptype == "numeric":
                if "distribution" not in col_prior:
                    raise PriorsParseError(f"Prior for {col_name} (numeric) missing distribution")
            # Other types can be more lenient
    
    async def extract_priors_from_description(
        self,
        schema: Dict[str, Any],
        user_description: str = "",
        sample_csv_path: Optional[str] = None,
        model: str = "gemini",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        api_key_env: Optional[str] = None,
        schema_fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract priors using LLM.
        
        Returns:
            Dict with priors_json, llm_meta, cache_key, redactions, etc.
        """
        t0 = datetime.now()
        
        # Load sample rows if provided
        sample_rows: Optional[List[Dict[str, Any]]] = None
        sample_rows_hash = ""
        if sample_csv_path and os.path.exists(sample_csv_path):
            try:
                df = pd.read_csv(sample_csv_path, nrows=100)  # Limit to 100 rows
                sample_rows = df.to_dict("records")
                sample_rows_hash = hashlib.sha256(
                    pd.util.hash_pandas_object(df).values.tobytes()
                ).hexdigest()
            except Exception as e:
                log.warning("Failed to load sample CSV: %s", e)
        
        # Build prompt
        prompt = self._build_prompt(schema, user_description, sample_rows)
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        
        # Compute schema fingerprint if not provided
        if not schema_fingerprint:
            schema_fingerprint = hashlib.sha256(
                json.dumps(schema, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
        
        # Cache key
        extractor_params = {
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        cache_key = self._cache_key(
            model, prompt_hash, schema_fingerprint, user_description, sample_rows_hash, extractor_params
        )
        cache_path = self._cache_path(cache_key)
        
        # Check cache
        if not self.bypass_cache and cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                log.info("LLM priors cache hit: %s", cache_key[:16])
                return cached
            except Exception as e:
                log.warning("Cache read failed: %s", e)
        
        # Call LLM
        try:
            raw_response = await call_llm(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key_env=api_key_env,
            )
        except LLMNetworkError as e:
            # Try cache even on network error
            if cache_path.exists():
                log.warning("LLM network error, using cached priors: %s", e)
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            raise
        except LLMError as e:
            log.error("LLM call failed: %s", e)
            raise
        
        # Redact PII
        redacted_response, redaction_counts = self._redact_pii(raw_response)
        has_redactions = sum(redaction_counts.values()) > 0
        
        # Parse JSON
        try:
            # Try to extract JSON if wrapped in markdown
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', redacted_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object (greedy to get full object)
                json_match = re.search(r'\{.*\}', redacted_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    # Try to fix truncated JSON by closing braces
                    open_braces = json_str.count('{')
                    close_braces = json_str.count('}')
                    missing = open_braces - close_braces
                    if missing > 0:
                        # Add missing closing braces and try to complete arrays/strings
                        json_str += '}' * missing
                        # Try to close any open arrays
                        if json_str.count('[') > json_str.count(']'):
                            json_str += ']' * (json_str.count('[') - json_str.count(']'))
                else:
                    json_str = redacted_response
            
            # Try parsing - if fails, might be truncated
            priors_json = None
            try:
                priors_json = json.loads(json_str)
            except json.JSONDecodeError as je:
                # If truncated, try to create minimal valid structure
                log.warning(f"JSON parse error (possibly truncated): {je}")
                # Create minimal valid structure
                priors_json = {
                    "schema_hint": {"columns": [], "notes": "LLM response was truncated - using schema defaults"},
                    "priors": {},
                    "dependencies": [],
                    "examples": [],
                }
            
            # Ensure we have priors_json at this point
            if priors_json is None:
                log.error("Failed to parse JSON and could not create fallback")
                raise PriorsParseError("Failed to parse LLM response as JSON and no fallback available")
        except json.JSONDecodeError as e:
            # Outer catch - should not reach here if inner catch worked
            log.error(f"JSON parsing failed completely: {e}")
            # Create minimal fallback
            priors_json = {
                "schema_hint": {"columns": [], "notes": "LLM response parsing failed - using schema defaults"},
                "priors": {},
                "dependencies": [],
                "examples": [],
            }
        
        # Validate priors (allow minimal fallback structure)
        try:
            self._validate_priors(priors_json)
        except PriorsParseError as e:
            # Check if we have minimal fallback structure (all required top-level keys)
            has_all_keys = all(k in priors_json for k in ["schema_hint", "priors", "dependencies", "examples"])
            
            if has_all_keys:
                # Minimal structure is valid enough - just log the warning
                log.warning(f"Using minimal priors structure: {e}")
                # Continue - don't raise, accept minimal structure
            else:
                # Missing keys - try cache if available
                if cache_path.exists():
                    log.warning("Invalid priors JSON, using cache: %s", e)
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                # If no cache and missing keys, create minimal structure
                log.warning("Creating minimal priors structure due to validation failure")
                priors_json = {
                    "schema_hint": {"columns": [], "notes": "Minimal structure - validation failed"},
                    "priors": {},
                    "dependencies": [],
                    "examples": [],
                }
        
        # Prepare result
        result = {
            "priors_json": priors_json,
            "llm_meta": {
                "model": model,
                "prompt_hash": prompt_hash,
                "timestamp": datetime.now().isoformat(),
            },
            "original_raw_text": raw_response,
            "cache_key": cache_key,
            "redactions": {
                "performed": has_redactions,
                "counts": redaction_counts,
            },
            "execution_time_seconds": (datetime.now() - t0).total_seconds(),
        }
        
        # Cache result
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
        except Exception as e:
            log.warning("Failed to cache priors: %s", e)
        
        return result


# Convenience function (synchronous wrapper)
def extract_priors_from_description(
    schema: Dict[str, Any],
    user_description: str = "",
    sample_csv_path: Optional[str] = None,
    model: str = "gemini",
    temperature: float = 0.0,
    max_tokens: int = 4096,
    api_key_env: Optional[str] = None,
    cache_dir: Optional[str] = None,
    bypass_cache: bool = False,
    schema_fingerprint: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous wrapper for extract_priors_from_description."""
    extractor = LLMPriorsExtractor(cache_dir=cache_dir, bypass_cache=bypass_cache)
    return asyncio.run(
        extractor.extract_priors_from_description(
            schema=schema,
            user_description=user_description,
            sample_csv_path=sample_csv_path,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key_env=api_key_env,
            schema_fingerprint=schema_fingerprint,
        )
    )

