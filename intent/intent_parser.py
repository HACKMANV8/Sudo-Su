import os
import re
import json
from typing import Any, Dict
from dotenv import load_dotenv
from jsonschema import Draft7Validator
from google import genai

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'intent_schema.json')
DEFAULT_MODEL = 'gemini-2.5-flash'


def _load_schema() -> Dict[str, Any]:
    with open(SCHEMA_PATH, 'r') as f:
        return json.load(f)


def _extract_json_block(text: str) -> str:
    """Return the first top-level JSON object substring from text or original text if none."""
    # Try fenced block first
    m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        return m.group(1)
    # Fallback: greedy top-level braces
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text


def _get_response_text(resp: Any) -> str:
    # Preferred convenience property
    text = getattr(resp, 'text', None)
    if text:
        return text
    # Fall back to candidates structure
    try:
        cand = resp.candidates[0]
        parts = getattr(cand.content, 'parts', None) or []
        if parts:
            # parts items often have a 'text' attribute
            first = parts[0]
            return getattr(first, 'text', str(first))
    except Exception:
        pass
    return ''


def parse_intent(natural_prompt: str, save_path: str = 'specs/intent.json') -> Dict[str, Any]:
    """Use Gemini to parse user intent into a validated DatasetIntent JSON.

    Args:
        natural_prompt: Free-form description of the desired dataset.
        save_path: Where to save the validated JSON (default: specs/intent.json).

    Returns:
        The validated intent dict.
    """
    load_dotenv()
    model = os.getenv('INTENT_MODEL', DEFAULT_MODEL)
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    client = genai.Client(api_key=api_key) if api_key else genai.Client()

    schema = _load_schema()

    # Compose a robust, delimiter-based prompt to avoid format confusion
    instructions = (
        "You are a data product analyst. Extract a DatasetIntent JSON object from the user's request. "
        "Output MUST be only valid JSON per the schema. No prose, no code fences, no comments."
    )
    prompt = (
        f"{instructions}\n\n"
        f"<request>\n{natural_prompt}\n</request>\n\n"
        f"<schema>\n{json.dumps(schema)}\n</schema>\n\n"
        "Rules:\n"
        "- Fill: domain, goal, records_target (estimate if unknown), columns.\n"
        "- Include if implied: audience, entities, constraints, privacy_flags, examples.\n"
        "- Column names: lowercase_snake_case, unique.\n"
        "- Types: string | integer | float | boolean | date | datetime | enum.\n"
        "- If enum used, include constraints.enum values.\n"
        "- Be concise. Return ONLY JSON."
    )

    # First attempt: force JSON MIME type
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    text = _get_response_text(resp)

    json_str = _extract_json_block(text or '')
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Retry once with a stricter instruction and JSON MIME type
        strict_prompt = (
            "Return ONLY a valid JSON object that conforms to the schema below. No prose, no fences, no extra characters.\n\n"
            f"<request>\n{natural_prompt}\n</request>\n\n"
            f"<schema>\n{json.dumps(schema)}\n</schema>\n"
        )
        resp2 = client.models.generate_content(
            model=model,
            contents=strict_prompt,
            config={"response_mime_type": "application/json"},
        )
        text2 = _get_response_text(resp2)
        json_str2 = _extract_json_block(text2 or '')
        try:
            data = json.loads(json_str2)
        except json.JSONDecodeError as e2:
            raise ValueError(
                f"Model did not return valid JSON. Parse error: {e2}. Raw: {(text2 or text)[:500]}"
            )

    # Validate
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        msg = "; ".join([f"{'/'.join([str(p) for p in e.path])}: {e.message}" for e in errors])
        raise ValueError(f"Intent JSON failed validation: {msg}")

    # Ensure output directory
    out_dir = os.path.dirname(save_path) or '.'
    os.makedirs(out_dir, exist_ok=True)
    with open(save_path, 'w') as f:
        json.dump(data, f, indent=2)

    return data


if __name__ == "__main__":
    example = (
        "Generate a customer feedback dataset for a food delivery app with sentiment, category, and timestamps. ~5k rows."
    )
    intent = parse_intent(example)
    print(json.dumps(intent, indent=2))
