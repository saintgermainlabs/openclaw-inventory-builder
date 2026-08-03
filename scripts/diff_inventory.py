#!/usr/bin/env python3
"""Diff two services.yaml files and print the inventory summary."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inventory_lib import format_diff_summary, inventory_diff, load_yaml  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    before = load_yaml(args.before) if args.before.exists() else None
    after = load_yaml(args.after)
    if after is None or not isinstance(after, dict):
        print("after must be a YAML mapping", file=sys.stderr)
        return 1
    if before is not None and not isinstance(before, dict):
        print("before must be a YAML mapping", file=sys.stderr)
        return 1
    print(format_diff_summary(inventory_diff(before, after)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
