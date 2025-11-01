from __future__ import annotations

import logging
import os
from typing import Optional

log = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM client errors."""
    pass


class LLMNetworkError(LLMError):
    """Network or API error."""
    pass


class LLMParseError(LLMError):
    """Failed to parse LLM response."""
    pass


async def call_llm(
    prompt: str,
    model: str = "gemini",
    temperature: float = 0.0,
    max_tokens: int = 4096,
    api_key_env: Optional[str] = None,
) -> str:
    """Call LLM with prompt and return response text.
    
    Args:
        prompt: The prompt text
        model: Model identifier ('gemini', 'openai', 'mock')
        temperature: Sampling temperature (0.0 for deterministic)
        max_tokens: Maximum tokens in response
        api_key_env: Environment variable name for API key
    
    Returns:
        Response text from LLM
    
    Raises:
        LLMNetworkError: On network/API errors
        LLMParseError: On response parsing errors
    """
    if model == "mock":
        # Mock for testing
        return '{"schema_hint": {}, "priors": {}, "dependencies": [], "examples": []}'
    
    api_key_env = api_key_env or f"{model.upper()}_API_KEY"
    api_key = os.environ.get(api_key_env)
    
    if not api_key:
        raise LLMNetworkError(f"API key not found in environment variable {api_key_env}")
    
    if model == "gemini" or model.startswith("gemini"):
        return await _call_gemini(prompt, model, temperature, max_tokens, api_key)
    elif model == "openai" or model.startswith("gpt"):
        return await _call_openai(prompt, model, temperature, max_tokens, api_key)
    else:
        raise LLMError(f"Unsupported model: {model}")


async def _call_gemini(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    api_key: str,
) -> str:
    """Call Google Gemini API."""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        
        # Select model - strip models/ prefix if present
        model_clean = model.lower().replace("models/", "")
        
        if "2.5" in model_clean or "2.0" in model_clean or "2" in model_clean:
            if "pro" in model_clean:
                model_name = "gemini-2.5-pro-preview-05-06"
            else:
                model_name = "gemini-2.5-flash"  # Stable flash model
        elif "pro" in model_clean:
            model_name = "gemini-2.5-pro-preview-05-06"
        else:
            # Default to stable flash model
            model_name = "gemini-2.5-flash"
        
        model_obj = genai.GenerativeModel(model_name)
        
        # Configure generation
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        # Configure safety settings - allow more content for data generation
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }
        except ImportError:
            # Fallback if enum types not available
            safety_settings = None
        
        response = model_obj.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        
        # Check for valid response
        if not response.candidates:
            raise LLMParseError("No candidates in Gemini response")
        
        candidate = response.candidates[0]
        
        # Extract text from parts first
        text = ""
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, 'text') and part.text:
                    text += part.text
        
        # Check finish reason (handle as enum or int)
        finish_reason_val = getattr(candidate, 'finish_reason', None)
        finish_reason_int = getattr(finish_reason_val, 'value', finish_reason_val) if finish_reason_val else None
        
        # finish_reason enum values: 1 = STOP (success), 2 = MAX_TOKENS, 3 = SAFETY, 4 = RECITATION, 5 = OTHER
        if finish_reason_int == 3:  # SAFETY
            if not text:
                raise LLMParseError("Gemini response blocked by safety filters")
            else:
                # Got some text despite safety warning - use it but log warning
                log.warning("Gemini returned content despite safety filter trigger")
        elif finish_reason_int == 2:  # MAX_TOKENS
            if text:
                log.warning("Gemini response truncated (max tokens) - using partial response")
            else:
                raise LLMParseError("Gemini response empty after hitting max tokens - try increasing --llm-max-tokens")
        elif finish_reason_int and finish_reason_int != 1:  # Not STOP
            log.warning(f"Gemini finish_reason: {finish_reason_int}")
        
        if not text:
            raise LLMParseError(f"Empty text in Gemini response (finish_reason={finish_reason_int})")
        
        return text.strip()
    
    except ImportError:
        raise LLMNetworkError("google-generativeai package not installed. Install with: pip install google-generativeai")
    except Exception as e:
        if "network" in str(e).lower() or "api" in str(e).lower() or "http" in str(e).lower():
            raise LLMNetworkError(f"Gemini API error: {e}") from e
        raise LLMError(f"Gemini call failed: {e}") from e


async def _call_openai(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    api_key: str,
) -> str:
    """Call OpenAI API."""
    try:
        import openai
        
        client = openai.AsyncOpenAI(api_key=api_key)
        
        # Map model names
        if model == "openai" or not model.startswith("gpt"):
            model = "gpt-4o-mini"
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a structured data priors extractor. Output only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        content = response.choices[0].message.content
        if not content:
            raise LLMParseError("Empty response from OpenAI")
        
        return content.strip()
    
    except ImportError:
        raise LLMNetworkError("openai package not installed. Install with: pip install openai")
    except Exception as e:
        if "network" in str(e).lower() or "api" in str(e).lower() or "http" in str(e).lower():
            raise LLMNetworkError(f"OpenAI API error: {e}") from e
        raise LLMError(f"OpenAI call failed: {e}") from e

