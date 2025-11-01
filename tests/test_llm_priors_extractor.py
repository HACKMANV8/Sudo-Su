from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from openschema.llm.gemini_client import LLMError, LLMNetworkError
from openschema.llm.prior_extractor import (
    LLMPriorsExtractor,
    PriorsParseError,
    extract_priors_from_description,
)


@pytest.fixture
def valid_priors_json():
    """Valid priors JSON structure."""
    return {
        "schema_hint": {
            "columns": [
                {"name": "department", "type": "categorical", "notes": "Company departments"},
                {"name": "salary", "type": "numeric", "notes": "Annual salary"},
            ],
            "notes": "Employee data",
        },
        "priors": {
            "department": {
                "type": "categorical",
                "categories": ["engineering", "sales", "hr"],
                "probs": [0.5, 0.3, 0.2],
                "notes": "Department distribution",
            },
            "salary": {
                "type": "numeric",
                "distribution": {
                    "type": "normal",
                    "params": {"mean": 80000, "std": 20000, "min": 40000, "max": 200000},
                },
                "notes": "Salary distribution",
            },
        },
        "dependencies": [
            {"parent": "department", "child": "salary", "explanation": "Salary depends on department"},
        ],
        "examples": [
            {"department": "engineering", "salary": 120000},
            {"department": "sales", "salary": 75000},
        ],
    }


@pytest.fixture
def mock_llm_response(valid_priors_json):
    """Mock LLM response with valid priors."""
    return json.dumps(valid_priors_json, indent=2)


def test_cache_hit(tmp_path, mock_llm_response):
    """Test that cached priors are used on second call."""
    cache_dir = str(tmp_path / "cache")
    extractor = LLMPriorsExtractor(cache_dir=cache_dir, bypass_cache=False)
    
    schema = {
        "name": "test_schema",
        "fields": [{"name": "department", "type": "category"}, {"name": "salary", "type": "float"}],
    }
    
    # First call - should call LLM and cache
    with patch("openschema.llm.prior_extractor.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_llm_response
        result1 = asyncio.run(
            extractor.extract_priors_from_description(
                schema=schema,
                user_description="test",
                model="mock",
            )
        )
        assert mock_call.called
        assert result1["priors_json"]["priors"]["department"]["categories"] == ["engineering", "sales", "hr"]
    
    # Second call - should use cache
    with patch("openschema.llm.prior_extractor.call_llm", new_callable=AsyncMock) as mock_call:
        result2 = asyncio.run(
            extractor.extract_priors_from_description(
                schema=schema,
                user_description="test",
                model="mock",
            )
        )
        assert not mock_call.called  # Should not call LLM
        assert result1["cache_key"] == result2["cache_key"]


def test_priors_parsing_valid(valid_priors_json, mock_llm_response):
    """Test parsing of valid priors JSON."""
    extractor = LLMPriorsExtractor()
    
    # Should not raise
    extractor._validate_priors(valid_priors_json)
    
    # Test with LLM call
    schema = {"name": "test", "fields": [{"name": "department", "type": "category"}]}
    with patch("openschema.llm.prior_extractor.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_llm_response
        result = asyncio.run(
            extractor.extract_priors_from_description(schema=schema, user_description="test", model="mock")
        )
        assert "priors_json" in result
        assert result["priors_json"]["priors"]["department"]["categories"] == ["engineering", "sales", "hr"]


def test_priors_parsing_invalid():
    """Test parsing of invalid priors JSON falls back to cache or raises."""
    extractor = LLMPriorsExtractor()
    
    # Missing required keys
    invalid_priors = {"priors": {}}
    with pytest.raises(PriorsParseError):
        extractor._validate_priors(invalid_priors)
    
    # Invalid categorical
    invalid_cat = {
        "schema_hint": {},
        "priors": {"department": {"type": "categorical"}},  # Missing categories/probs
        "dependencies": [],
        "examples": [],
    }
    with pytest.raises(PriorsParseError):
        extractor._validate_priors(invalid_cat)


def test_bad_json_fallback(tmp_path, valid_priors_json):
    """Test fallback when LLM returns invalid JSON."""
    cache_dir = str(tmp_path / "cache")
    extractor = LLMPriorsExtractor(cache_dir=cache_dir)
    
    # First, cache valid response
    schema = {"name": "test", "fields": [{"name": "x", "type": "category"}]}
    valid_response = json.dumps(valid_priors_json)
    
    with patch("openschema.llm.prior_extractor.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = valid_response
        asyncio.run(extractor.extract_priors_from_description(schema=schema, user_description="test", model="mock"))
    
    # Now, try invalid JSON but cache should be used
    with patch("openschema.llm.prior_extractor.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "This is not JSON"
        extractor.bypass_cache = False
        result = asyncio.run(
            extractor.extract_priors_from_description(
                schema=schema, user_description="test", model="mock"
            )
        )
        # Should use cached valid response
        assert "priors_json" in result
        assert "department" in result["priors_json"]["priors"]


def test_pii_redaction():
    """Test PII redaction in LLM responses."""
    extractor = LLMPriorsExtractor()
    
    text_with_pii = "Contact: john.doe@example.com or call 555-123-4567. SSN: 123-45-6789."
    redacted, counts = extractor._redact_pii(text_with_pii)
    
    assert "<REDACTED_EMAIL>" in redacted
    assert "<REDACTED_PHONE>" in redacted
    assert "<REDACTED_SSN>" in redacted
    assert counts["email"] > 0
    assert counts["phone"] > 0
    assert counts["ssn"] > 0


def test_integration_smoke(tmp_path):
    """Smoke test: run extractor with mocked LLM and check output structure."""
    cache_dir = str(tmp_path / "cache")
    schema = {
        "name": "employee",
        "fields": [
            {"name": "department", "type": "category"},
            {"name": "salary", "type": "float"},
        ],
    }
    
    valid_priors = {
        "schema_hint": {"columns": [], "notes": ""},
        "priors": {
            "department": {
                "type": "categorical",
                "categories": ["eng", "sales"],
                "probs": [0.6, 0.4],
            },
            "salary": {
                "type": "numeric",
                "distribution": {"type": "normal", "params": {"mean": 80000, "std": 20000}},
            },
        },
        "dependencies": [],
        "examples": [],
    }
    
    mock_response = json.dumps(valid_priors)
    
    with patch("openschema.llm.prior_extractor.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_response
        result = extract_priors_from_description(
            schema=schema,
            user_description="test description",
            cache_dir=cache_dir,
            model="mock",
        )
    
    assert "priors_json" in result
    assert "cache_key" in result
    assert "llm_meta" in result
    assert result["priors_json"]["priors"]["department"]["categories"] == ["eng", "sales"]


def test_network_error_cache_fallback(tmp_path, mock_llm_response):
    """Test that network errors fall back to cache if available."""
    cache_dir = str(tmp_path / "cache")
    extractor = LLMPriorsExtractor(cache_dir=cache_dir)
    
    schema = {"name": "test", "fields": [{"name": "x", "type": "category"}]}
    
    # First, cache valid response
    with patch("openschema.llm.prior_extractor.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_llm_response
        asyncio.run(extractor.extract_priors_from_description(schema=schema, user_description="test", model="mock"))
    
    # Now simulate network error
    with patch("openschema.llm.prior_extractor.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = LLMNetworkError("Network timeout")
        extractor.bypass_cache = False
        result = asyncio.run(
            extractor.extract_priors_from_description(
                schema=schema, user_description="test", model="mock"
            )
        )
        # Should use cached response
        assert "priors_json" in result

