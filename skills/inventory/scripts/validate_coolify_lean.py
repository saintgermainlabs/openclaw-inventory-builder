#!/usr/bin/env python3
"""Validate lean Coolify inventory (apps + services with id/name/project/tags)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ("id", "name", "project", "tags")


def load_doc(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError:
            # Minimal parse for our lean schema without PyYAML
            return parse_lean_yaml(text)
        return yaml.safe_load(text)
    return json.loads(text)


def parse_lean_yaml(text: str) -> dict[str, Any]:
    """Best-effort loader for the lean schema when PyYAML is unavailable."""
    # Prefer json if the file is actually json
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return json.loads(text)

    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ImportError:
        pass

    # Fallback: require JSON sibling — instruct operator
    print(
        "PyYAML not installed; validate with inventory.json or: pip install pyyaml",
        file=sys.stderr,
    )
    raise SystemExit(2)


def err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def validate_resource(item: Any, where: str, errors: list[str], seen_ids: set[str]) -> None:
    if not isinstance(item, dict):
        err(errors, f"{where}: must be an object")
        return
    for field in REQUIRED_FIELDS:
        if field not in item:
            err(errors, f"{where}: missing {field}")
    rid = item.get("id")
    if rid is not None and not isinstance(rid, str):
        err(errors, f"{where}.id: must be a string")
    name = item.get("name")
    if name is not None and not isinstance(name, str):
        err(errors, f"{where}.name: must be a string")
    project = item.get("project")
    if project is not None and not isinstance(project, str):
        err(errors, f"{where}.project: must be a string")
    tags = item.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            err(errors, f"{where}.tags: must be a list")
        else:
            for i, tag in enumerate(tags):
                if not isinstance(tag, str):
                    err(errors, f"{where}.tags[{i}]: must be a string")
    if isinstance(rid, str) and rid:
        if rid in seen_ids:
            err(errors, f"duplicate id {rid!r} at {where}")
        seen_ids.add(rid)


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["document must be a mapping/object"]

    version = data.get("version")
    if not isinstance(version, int) or version < 1:
        err(errors, "version must be an integer >= 1")

    if not data.get("generated_at"):
        err(errors, "generated_at is required")

    source = data.get("source")
    if not isinstance(source, dict):
        err(errors, "source must be an object")
    else:
        if source.get("type") != "coolify":
            err(errors, "source.type must be 'coolify'")
        if not source.get("mcp_server"):
            err(errors, "source.mcp_server is required")
        tools = source.get("tools")
        if not isinstance(tools, list) or not tools:
            err(errors, "source.tools must be a non-empty list")

    seen_ids: set[str] = set()
    for section in ("apps", "services"):
        items = data.get(section)
        if not isinstance(items, list):
            err(errors, f"{section} must be a list")
            continue
        for i, item in enumerate(items):
            validate_resource(item, f"{section}[{i}]", errors, seen_ids)

    return errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="inventory.yaml or inventory.json")
    args = p.parse_args()
    if not args.path.exists():
        print(f"missing file: {args.path}", file=sys.stderr)
        return 1
    data = load_doc(args.path)
    errors = validate(data)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print(f"OK {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
