import os
import json
import pandas as pd
from typing import Any, Dict, List
from utils.genai_json import generate_json, essential_rules


ALLOWED_TYPES = ["string", "integer", "float", "boolean", "date", "datetime", "enum"]


def _sample_csv(csv_path: str, n_rows: int = 20) -> Dict[str, Any]:
    df = pd.read_csv(csv_path)
    sample = df.head(n_rows)
    # Convert sample to JSON records for stable formatting
    return {
        "columns": list(sample.columns),
        "rows": sample.to_dict(orient="records"),
    }


def build_schema_for_csv(csv_path: str, natural_prompt: str | None = None, n_rows: int = 20) -> Dict[str, Any]:
    """Use Gemini to infer a JSON schema for a CSV file.

    Returns a dict with at least: { columns: [ {name, type, description?, constraints?} ], dataset_description? }
    """
    sample = _sample_csv(csv_path, n_rows=n_rows)
    filename = os.path.basename(csv_path)

    intent_part = f"<intent>\n{natural_prompt}\n</intent>\n\n" if natural_prompt else ""

    instructions = (
        "You are a data modeling expert. Infer a JSON schema from the provided CSV sample. "
        "Types must be one of: string | integer | float | boolean | date | datetime | enum. "
        "Add constraints where apparent (regex, min, max, enum for small categorical sets), and brief descriptions."
    )

    prompt = (
        f"{instructions}\n\n"
        f"{intent_part}"
        f"<file>\n{filename}\n</file>\n\n"
        f"<csv_sample_json>\n{json.dumps(sample)}\n</csv_sample_json>\n\n"
        "Output format:\n"
        "{\n"
        "  \"dataset_description\": string,\n"
        "  \"columns\": [\n"
        "    { \"name\": string, \"type\": one-of(ALLOWED_TYPES), \"description\"?: string, \"constraints\"?: {\n"
        "        \"min\"?: number|string, \"max\"?: number|string, \"regex\"?: string, \"enum\"?: [string|number|boolean], \"unique\"?: boolean, \"pii\"?: boolean\n"
        "    }}\n"
        "  ]\n"
        "}\n\n"
        f"{essential_rules}"
    )

    data = generate_json(prompt)

    # Light validation: ensure 'columns' exists and types are allowed
    cols = data.get("columns", [])
    if not isinstance(cols, list) or not cols:
        raise ValueError("Generated schema missing non-empty 'columns' array")
    for c in cols:
        t = c.get("type")
        if t not in ALLOWED_TYPES:
            raise ValueError(f"Column '{c.get('name')}' has invalid type '{t}'")

    return data


def build_schema_from_intent(natural_prompt: str) -> Dict[str, Any]:
    """Use Gemini to infer a JSON schema purely from the user's natural language intent.

    Returns a dict similar to CSV-based schema: { dataset_description?, columns: [...] }
    """
    instructions = (
        "You are a data modeling expert. Given a natural language dataset request, propose a concise JSON schema. "
        "Types must be one of: string | integer | float | boolean | date | datetime | enum. "
        "Add constraints where implied (regex, min, max, enum), and short descriptions."
    )

    prompt = (
        f"{instructions}\n\n"
        f"<intent>\n{natural_prompt}\n</intent>\n\n"
        "Output format:\n"
        "{\n"
        "  \"dataset_description\": string,\n"
        "  \"columns\": [\n"
        "    { \"name\": string, \"type\": one-of(ALLOWED_TYPES), \"description\"?: string, \"constraints\"?: {\n"
        "        \"min\"?: number|string, \"max\"?: number|string, \"regex\"?: string, \"enum\"?: [string|number|boolean], \"unique\"?: boolean, \"pii\"?: boolean\n"
        "    }}\n"
        "  ]\n"
        "}\n\n"
        f"{essential_rules}"
    )

    data = generate_json(prompt)
    cols = data.get("columns", [])
    if not isinstance(cols, list) or not cols:
        raise ValueError("Generated schema (intent-only) missing non-empty 'columns' array")
    for c in cols:
        t = c.get("type")
        if t not in ALLOWED_TYPES:
            raise ValueError(f"Column '{c.get('name')}' has invalid type '{t}' in intent-only schema")
    return data
