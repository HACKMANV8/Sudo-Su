from __future__ import annotations

# Re-export generate_from_schema from the generator.py file in parent directory
# We need to import from the file, not create circular import
import importlib.util
from pathlib import Path

_parent_file = Path(__file__).parent.parent / "generator.py"
if _parent_file.exists():
    spec = importlib.util.spec_from_file_location("openschema._generator_file", _parent_file)
    _gen_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_gen_module)
    generate_from_schema = _gen_module.generate_from_schema
else:
    raise ImportError("Could not find openschema/generator.py")

__all__ = ["relational_generator", "generate_from_schema"]

