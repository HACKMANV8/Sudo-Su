import os
import re
import json
from typing import Any, Dict
from dotenv import load_dotenv
from google import genai

DEFAULT_MODEL = 'gemini-2.5-flash'


def _extract_json_block(text: str) -> str:
    m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        return m.group(1)
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text


def _get_response_text(resp: Any) -> str:
    text = getattr(resp, 'text', None)
    if text:
        return text
    try:
        cand = resp.candidates[0]
        parts = getattr(cand.content, 'parts', None) or []
        if parts:
            first = parts[0]
            return getattr(first, 'text', str(first))
    except Exception:
        pass
    return ''


essential_rules = (
    "Output MUST be only valid JSON. No prose, no code fences, no comments."
)


def generate_json(prompt: str, model: str | None = None) -> Dict[str, Any]:
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    client = genai.Client(api_key=api_key) if api_key else genai.Client()
    chosen_model = model or os.getenv('INTENT_MODEL', DEFAULT_MODEL)

    # First attempt with JSON MIME type
    resp = client.models.generate_content(
        model=chosen_model,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    text = _get_response_text(resp)
    json_str = _extract_json_block(text or '')
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Retry once with essential rules prepended and JSON MIME type
        strict = f"{essential_rules}\n\n{prompt}"
        resp2 = client.models.generate_content(
            model=chosen_model,
            contents=strict,
            config={"response_mime_type": "application/json"},
        )
        text2 = _get_response_text(resp2)
        json_str2 = _extract_json_block(text2 or '')
        try:
            return json.loads(json_str2)
        except json.JSONDecodeError as e2:
            raise ValueError(
                f"Model did not return valid JSON. Parse error: {e2}. Raw: {(text2 or text)[:500]}"
            )
