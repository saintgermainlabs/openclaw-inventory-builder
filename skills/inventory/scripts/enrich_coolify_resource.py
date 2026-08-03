#!/usr/bin/env python3
"""Merge one Coolify app/service detail into lean inventory.yaml.

Cron-ready: update a single row from get_application / get_service JSON.
Does not make network calls. Phase 1 fields: id, name, project, tags.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Reuse normalizers from the lean builder
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_coolify_lean import (  # noqa: E402
    dump_lean_yaml,
    load_json,
    normalize_resource,
)


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def load_inventory(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json" or text.lstrip().startswith("{"):
        data = json.loads(text)
    else:
        try:
            import yaml
        except ImportError:
            die("PyYAML required to load inventory.yaml; pass inventory.json or install pyyaml")
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        die("inventory must be a mapping")
    return data


def section_for_kind(kind: str) -> str:
    if kind == "app":
        return "apps"
    if kind == "service":
        return "services"
    die(f"kind must be app|service, got {kind!r}")


def merge_row(
    inventory: dict[str, Any],
    kind: str,
    resource_id: str,
    detail: Any,
) -> dict[str, Any]:
    section = section_for_kind(kind)
    items = inventory.get(section)
    if not isinstance(items, list):
        die(f"{section} must be a list")

    if isinstance(detail, dict) and "result" in detail and isinstance(detail["result"], dict):
        detail = detail["result"]

    normalized = normalize_resource(detail)
    if normalized is None:
        die("detail JSON must be an object")

    # Prefer explicit CLI id if detail omitted it
    if not normalized["id"]:
        normalized["id"] = resource_id
    elif resource_id and normalized["id"] != resource_id:
        # Keep CLI target id as the row key; still allow name/project/tags from detail
        normalized["id"] = resource_id

    found = False
    for i, item in enumerate(items):
        if isinstance(item, dict) and str(item.get("id", "")) == resource_id:
            # Fill only the four lean fields; preserve unknown future keys on the row
            merged = dict(item)
            for key in ("id", "name", "project", "tags"):
                new_val = normalized.get(key)
                if key == "tags":
                    merged[key] = new_val if isinstance(new_val, list) else []
                elif new_val:
                    merged[key] = new_val
                elif key not in merged:
                    merged[key] = "" if key != "tags" else []
            items[i] = merged
            found = True
            break

    if not found:
        items.append(normalized)
        items.sort(key=lambda r: (str(r.get("name", "")).lower(), str(r.get("id", ""))))

    inventory[section] = items
    return inventory


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kind", choices=("app", "service"), required=True)
    p.add_argument("--id", required=True, help="Resource id to update")
    p.add_argument(
        "--detail-json",
        type=Path,
        required=True,
        help="Path to get_application / get_service JSON response",
    )
    p.add_argument(
        "--inventory",
        type=Path,
        default=Path("/knowledge/inventory/coolify/inventory.yaml"),
    )
    p.add_argument(
        "--also-json",
        type=Path,
        default=None,
        help="Optional inventory.json to rewrite alongside YAML",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.inventory.exists():
        die(f"missing inventory: {args.inventory}")
    inventory = load_inventory(args.inventory)
    detail = load_json(args.detail_json)
    merge_row(inventory, args.kind, args.id, detail)

    if args.inventory.suffix.lower() == ".json":
        args.inventory.write_text(
            json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        args.inventory.write_text(dump_lean_yaml(inventory), encoding="utf-8")
    print(f"Updated {args.kind} id={args.id} in {args.inventory}")

    if args.also_json and args.also_json.resolve() != args.inventory.resolve():
        args.also_json.write_text(
            json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {args.also_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
