from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field as PydField, validator


ALLOWED_TYPES: set[str] = {
    "int",
    "float",
    "string",
    "datetime",
    "category",
    "bool",
    "ip",
}


def to_snake_case(name: str) -> str:
    name = re.sub(r"[\s\-]+", "_", name.strip())
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.lower().strip("_")


class Field(BaseModel):
    name: str
    type: str
    nullable: float = 0.0
    unique: bool = False
    distribution: Optional[str] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    categories: Optional[List[Union[str, int]]] = None
    probs: Optional[List[float]] = None
    examples: List[Any] = []
    metadata: Optional[Dict[str, Any]] = None

    # Optional statistics if present in inputs; not required by spec but useful for summary
    mean: Optional[float] = None
    std: Optional[float] = None

    @validator("name", pre=True)
    def _normalize_name(cls, v: str) -> str:
        return to_snake_case(v)

    @validator("type", pre=True)
    def _normalize_type(cls, v: str) -> str:
        if isinstance(v, str):
            t = v.strip().lower()
            # common aliases
            aliases = {
                "integer": "int",
                "double": "float",
                "number": "float",
                "str": "string",
                "datetime64": "datetime",
                "timestamp": "datetime",
                "categorical": "category",
                "boolean": "bool",
            }
            t = aliases.get(t, t)
            if t not in ALLOWED_TYPES:
                raise ValueError(f"Unsupported field type: {v}")
            return t
        raise ValueError("type must be a string")

    @validator("distribution", always=True)
    def _fill_distribution(cls, v: Optional[str]) -> str:
        return v or "uniform"

    @validator("min", "max", always=True)
    def _fill_numeric_minmax(cls, v, values):
        field_type = values.get("type")
        if field_type in {"int", "float"}:
            # Provide defaults if either missing
            min_v = values.get("min") if v is not None else None
            max_v = values.get("max") if v is not None else None
            # pydantic calls separately, so derive from existing
            return v
        return v

    @validator("examples", pre=True, always=True)
    def _default_examples(cls, v):
        return v or []


class Schema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    n_rows: int = 1000
    fields: List[Field]
    class_balance: Optional[Dict[Union[str, int, bool], float]] = None

    @validator("name", pre=True)
    def _normalize_schema_name(cls, v: str) -> str:
        return to_snake_case(v)


def _fill_missing_defaults(field: Dict[str, Any]) -> Dict[str, Any]:
    ftype = field.get("type")

    field.setdefault("nullable", 0.0)
    field.setdefault("unique", False)
    field.setdefault("distribution", "uniform")
    field.setdefault("categories", None)
    field.setdefault("examples", [])
    field.setdefault("metadata", None)

    if ftype in {"int", "float"}:
        fname = str(field.get("name", ""))
        # Avoid constraining obvious domain fields like salaries if unspecified
        if "salary" not in fname:
            field.setdefault("min", 0)
            field.setdefault("max", 100)

    return field


def load_schema_from_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        if not data:
            raise ValueError("Schema file contains an empty list")
        return validate_schema(dict(data[0]))
    if not isinstance(data, dict):
        raise ValueError("Schema file must contain a dict or list of dicts")
    return validate_schema(dict(data))


def validate_schema(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    # Normalize top-level name
    if "name" in schema_dict:
        schema_dict["name"] = to_snake_case(schema_dict["name"])

    fields = schema_dict.get("fields", [])
    normalized_fields: List[Dict[str, Any]] = []
    for fld in fields:
        fld = dict(fld)
        if "name" in fld:
            fld["name"] = to_snake_case(str(fld["name"]))
        if "type" in fld and isinstance(fld["type"], str):
            # leverage Field model normalization and validation
            try:
                tmp = Field(**_fill_missing_defaults({**fld}))
                fld = tmp.dict()
            except Exception as e:
                raise ValueError(str(e))
        else:
            raise ValueError("Each field must have a string 'type'")

        # After model defaulting, ensure min/max present for numeric unless domain implies otherwise
        if fld["type"] in {"int", "float"}:
            fname = str(fld.get("name", ""))
            if "salary" not in fname:
                if fld.get("min") is None:
                    fld["min"] = 0
                if fld.get("max") is None:
                    fld["max"] = 100

        normalized_fields.append(fld)

    schema_dict["fields"] = normalized_fields

    # Fill top-level defaults
    schema_dict.setdefault("n_rows", 1000)

    # Validate by constructing Schema instance
    _ = Schema(**schema_dict)  # noqa: F841
    return schema_dict


def to_json_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    properties: Dict[str, Any] = {}
    required: List[str] = []

    type_mapping = {
        "int": ("integer", None),
        "float": ("number", None),
        "string": ("string", None),
        "datetime": ("string", "date-time"),
        "category": ("string", None),
        "bool": ("boolean", None),
        "ip": ("string", "ipv4"),
    }

    for f in schema.get("fields", []):
        ftype = f.get("type")
        json_type, fmt = type_mapping.get(ftype, ("string", None))
        prop: Dict[str, Any] = {"type": json_type}
        if fmt:
            prop["format"] = fmt
        if ftype == "category" and f.get("categories"):
            prop["enum"] = f["categories"]
        if ftype in {"int", "float"}:
            if f.get("min") is not None:
                prop["minimum"] = f["min"]
            if f.get("max") is not None:
                prop["maximum"] = f["max"]
        properties[f["name"]] = prop
        if float(f.get("nullable", 0.0)) == 0.0:
            required.append(f["name"])

    return {
        "title": schema.get("name", "schema"),
        "description": schema.get("description", ""),
        "type": "object",
        "properties": properties,
        "required": required,
    }


def schema_summary(schema: Dict[str, Any]) -> str:
    fields = schema.get("fields", [])
    parts: List[str] = []
    for f in fields:
        fname = f.get("name", "")
        ftype = f.get("type", "")
        entry = fname + "(" + ftype
        if f.get("unique"):
            entry += " unique"
        if ftype == "category" and f.get("categories"):
            entry += f" {len(f['categories'])}"
        entry += ")"
        parts.append(entry)
    return f"{len(fields)} fields: " + ", ".join(parts)


