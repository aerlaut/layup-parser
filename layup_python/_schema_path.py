"""Resolves the bundled JSON Schema path."""
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "diagram.schema.json"
SCHEMA_VERSION = 2
