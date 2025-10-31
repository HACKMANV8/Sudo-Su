import os
import json
from typing import List, Dict, Any


def _print_schema_summary(schema: Dict[str, Any]) -> None:
    print("\nSchema summary:")
    ds = schema.get("dataset_description")
    if ds:
        print(f"- Dataset: {ds}")
    cols = schema.get("columns", [])
    print(f"- Columns: {len(cols)}")
    for c in cols[:20]:
        name = c.get("name")
        ctype = c.get("type")
        desc = c.get("description", "")
        print(f"  • {name} ({ctype}) - {desc[:80]}")
    if len(cols) > 20:
        print(f"  ... and {len(cols)-20} more")


def review_schema_file(schema_path: str, output_dir: str | None = None) -> Dict[str, Any]:
    """Interactive review for a single schema file. Returns result dict."""
    output_dir = output_dir or os.path.dirname(schema_path)
    with open(schema_path, 'r') as f:
        schema = json.load(f)

    _print_schema_summary(schema)

    print("\nReview options:")
    print("  [A]ccept  (default)")
    print("  [E]dit (paste full JSON)" )
    print("  [R]eject")
    print("  [S]kip")

    try:
        choice = input("Choice [A/e/r/s]: ").strip().lower() or 'a'
    except Exception:
        choice = 'a'

    result = {
        "status": "accepted",
        "notes": "",
        "schema": schema,
    }

    if choice == 'e':
        print("Paste edited JSON for the schema (single-line or multiline). End with Ctrl-D (Unix) or Ctrl-Z (Windows).")
        print("--- BEGIN PASTE ---")
        try:
            edited = []
            while True:
                line = input()
                edited.append(line)
        except EOFError:
            pass
        print("--- END PASTE ---")
        edited_text = "\n".join(edited)
        try:
            edited_schema = json.loads(edited_text)
            result["status"] = "edited"
            result["schema"] = edited_schema
        except Exception as e:
            print(f"Invalid JSON. Keeping original. Error: {e}")
            result["status"] = "accepted"

    elif choice == 'r':
        result["status"] = "rejected"
        try:
            notes = input("Short reason (optional): ").strip()
        except Exception:
            notes = ""
        result["notes"] = notes

    elif choice == 's':
        result["status"] = "pending"

    base = os.path.splitext(os.path.basename(schema_path))[0]
    reviewed_out = os.path.join(output_dir, f"{base}.reviewed.json")
    with open(reviewed_out, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Saved review: {reviewed_out}")
    return result


def review_schemas_in_dir(dir_path: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(dir_path)):
        if not name.endswith("_schema.json"):
            continue
        path = os.path.join(dir_path, name)
        try:
            res = review_schema_file(path, output_dir=dir_path)
            results.append(res)
        except Exception as e:
            print(f"Failed to review {name}: {e}")
    return results
