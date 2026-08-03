#!/usr/bin/env python3
"""Validate a services.yaml against the inventory JSON Schema."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inventory_lib import load_schema, load_yaml, validate_services_dict  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("services_yaml", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=ROOT
        / "skills"
        / "infrastructure-inventory"
        / "schemas"
        / "inventory.schema.json",
    )
    args = parser.parse_args()
    data = load_yaml(args.services_yaml)
    if not isinstance(data, dict):
        print("services.yaml must be a mapping", file=sys.stderr)
        return 1
    schema = load_schema(args.schema)
    errors = validate_services_dict(data, schema)
    if errors:
        print("Validation failed:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
