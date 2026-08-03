#!/usr/bin/env python3
"""Atomically write YAML after optional schema validation; rotate history."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inventory_lib import (  # noqa: E402
    atomic_write_yaml,
    load_schema,
    load_yaml,
    validate_services_dict,
    write_history,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="Candidate services YAML")
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("/knowledge/inventory/services.yaml"),
    )
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=Path("/knowledge/inventory/history"),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=ROOT
        / "skills"
        / "infrastructure-inventory"
        / "schemas"
        / "inventory.schema.json",
    )
    parser.add_argument(
        "--invalid-out",
        type=Path,
        default=Path("/knowledge/inventory/generated/services.invalid.yaml"),
    )
    args = parser.parse_args()

    data = load_yaml(args.candidate)
    if not isinstance(data, dict):
        print("candidate must be a YAML mapping", file=sys.stderr)
        return 1

    schema = load_schema(args.schema)
    errors = validate_services_dict(data, schema)
    if errors:
        atomic_write_yaml(data, args.invalid_out)
        print("Validation failed; wrote invalid candidate to", args.invalid_out, file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    if args.dest.exists():
        write_history(args.dest, args.history_dir)
    atomic_write_yaml(data, args.dest)
    print(f"Wrote {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
