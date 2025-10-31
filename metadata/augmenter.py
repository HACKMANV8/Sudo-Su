import os
import json
import pandas as pd
from typing import Any, Dict
from utils.genai_json import generate_json, essential_rules


def _profile_csv(csv_path: str, n_rows: int = 50) -> Dict[str, Any]:
    df = pd.read_csv(csv_path)
    sample = df.head(n_rows)
    profile = {
        "columns": [],
        "samples": sample.to_dict(orient="records"),
    }
    for col in df.columns:
        series = df[col]
        uniq = series.dropna().unique()
        top_uniqs = [str(x) for x in uniq[:20]]
        profile["columns"].append({
            "name": col,
            "dtype": str(series.dtype),
            "non_null": int(series.notna().sum()),
            "nulls": int(series.isna().sum()),
            "unique_count": int(series.nunique(dropna=True)),
            "example_values": top_uniqs,
        })
    return profile


def augment_metadata(csv_path: str, schema: Dict[str, Any] | None = None, natural_prompt: str | None = None, n_rows: int = 50) -> Dict[str, Any]:
    """Use Gemini to augment column descriptions/metadata based on CSV profile and optional schema/intent."""
    profile = _profile_csv(csv_path, n_rows=n_rows)
    filename = os.path.basename(csv_path)

    intent_part = f"<intent>\n{natural_prompt}\n</intent>\n\n" if natural_prompt else ""
    schema_part = f"<schema>\n{json.dumps(schema)}\n</schema>\n\n" if schema else ""

    instructions = (
        "You are a data documentation assistant. Propose concise, helpful descriptions and metadata for each column. "
        "Use profile stats and examples; suggest enums where appropriate; mark potential PII; and note reasonable constraints."
    )

    prompt = (
        f"{instructions}\n\n"
        f"{intent_part}{schema_part}"
        f"<file>\n{filename}\n</file>\n\n"
        f"<profile_json>\n{json.dumps(profile)}\n</profile_json>\n\n"
        "Output JSON format:\n"
        "{\n"
        "  \"dataset_description\"?: string,\n"
        "  \"columns\": [\n"
        "    { \"name\": string, \"description\"?: string, \"constraints\"?: {\n"
        "        \"min\"?: number|string, \"max\"?: number|string, \"regex\"?: string, \"enum\"?: [string|number|boolean], \"unique\"?: boolean, \"pii\"?: boolean\n"
        "    }, \"examples\"?: [string] }\n"
        "  ]\n"
        "}\n\n"
        f"{essential_rules}"
    )

    data = generate_json(prompt)

    # Light validation
    cols = data.get("columns", [])
    if not isinstance(cols, list) or not cols:
        raise ValueError("Generated metadata missing non-empty 'columns' array")

    return data


def augment_from_schema(schema: Dict[str, Any], natural_prompt: str | None = None) -> Dict[str, Any]:
    """Augment column descriptions and constraints using only the schema and optional intent text.

    Returns a structure similar to CSV-based augmentation:
      { dataset_description?, columns: [ {name, description?, constraints?, examples?} ] }
    """
    intent_part = f"<intent>\n{natural_prompt}\n</intent>\n\n" if natural_prompt else ""
    instructions = (
        "You are a data documentation assistant. Improve and fill concise descriptions and sensible constraints for each column. "
        "Use the given schema (types, names) and the intent context if provided."
    )

    prompt = (
        f"{instructions}\n\n"
        f"{intent_part}"
        f"<schema_json>\n{json.dumps(schema)}\n</schema_json>\n\n"
        "Output JSON format:\n"
        "{\n"
        "  \"dataset_description\"?: string,\n"
        "  \"columns\": [\n"
        "    { \"name\": string, \"description\"?: string, \"constraints\"?: {\n"
        "        \"min\"?: number|string, \"max\"?: number|string, \"regex\"?: string, \"enum\"?: [string|number|boolean], \"unique\"?: boolean, \"pii\"?: boolean\n"
        "    }, \"examples\"?: [string] }\n"
        "  ]\n"
        "}\n\n"
        f"{essential_rules}"
    )

    data = generate_json(prompt)
    cols = data.get("columns", [])
    if not isinstance(cols, list) or not cols:
        raise ValueError("Generated metadata (schema-only) missing non-empty 'columns' array")
    return data
