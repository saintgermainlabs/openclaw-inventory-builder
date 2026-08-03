#!/usr/bin/env python3
"""Build lean Coolify inventory from list_applications + list_services MCP JSON.

Does not make network calls. Output fields per resource: id, name, project, tags.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"missing input: {path}")
    except json.JSONDecodeError as e:
        die(f"invalid JSON in {path}: {e}")


def as_list(payload: Any) -> list[Any]:
    """Normalize MCP list payloads into a list of resource dicts."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in (
            "applications",
            "apps",
            "services",
            "data",
            "items",
            "results",
            "resources",
        ):
            val = payload.get(key)
            if isinstance(val, list):
                return val
        # Single resource object
        if any(k in payload for k in ("id", "uuid", "name")):
            return [payload]
    die(f"cannot normalize list payload of type {type(payload).__name__}")


def pick_id(item: dict[str, Any]) -> str:
    for key in ("id", "uuid", "uuid_short", "application_id", "service_id"):
        val = item.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def pick_name(item: dict[str, Any]) -> str:
    for key in ("name", "title", "hostname"):
        val = item.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def pick_project(item: dict[str, Any]) -> str:
    for key in ("project", "project_name", "projectName"):
        val = item.get(key)
        if isinstance(val, dict):
            for inner in ("name", "id"):
                if val.get(inner) is not None and str(val[inner]).strip():
                    return str(val[inner]).strip()
        elif val is not None and str(val).strip():
            return str(val).strip()
    nested = item.get("project")
    if isinstance(nested, dict):
        for inner in ("name", "id"):
            if nested.get(inner) is not None and str(nested[inner]).strip():
                return str(nested[inner]).strip()
    return ""


def pick_tags(item: dict[str, Any]) -> list[str]:
    tags = item.get("tags")
    if tags is None:
        return []
    if isinstance(tags, list):
        out: list[str] = []
        for t in tags:
            if isinstance(t, dict):
                name = t.get("name") or t.get("value") or t.get("tag")
                if name is not None and str(name).strip():
                    out.append(str(name).strip())
            elif t is not None and str(t).strip():
                out.append(str(t).strip())
        return out
    if isinstance(tags, str) and tags.strip():
        return [tags.strip()]
    return []


def normalize_resource(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    return {
        "id": pick_id(item),
        "name": pick_name(item),
        "project": pick_project(item),
        "tags": pick_tags(item),
    }


def normalize_resources(payload: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in as_list(payload):
        row = normalize_resource(item)
        if row is None:
            continue
        out.append(row)
    out.sort(key=lambda r: (r["name"].lower(), r["id"]))
    return out


def build_inventory(
    applications: Any,
    services: Any,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "version": 1,
        "source": {
            "type": "coolify",
            "mcp_server": "coolify-readonly",
            "tools": ["list_applications", "list_services"],
        },
        "generated_at": generated_at or utc_now(),
        "apps": normalize_resources(applications),
        "services": normalize_resources(services),
    }


def yaml_escape(value: str) -> str:
    if value == "":
        return '""'
    if any(c in value for c in (":", "#", "{", "}", "[", "]", ",", "&", "*", "!", "|", ">", "%", "@", "`", "'", '"', "\n")) or value.strip() != value:
        return json.dumps(value, ensure_ascii=False)
    return value


def dump_lean_yaml(data: dict[str, Any]) -> str:
    lines: list[str] = [
        f"version: {data['version']}",
        "source:",
        f"  type: {data['source']['type']}",
        f"  mcp_server: {data['source']['mcp_server']}",
        "  tools:",
    ]
    for tool in data["source"]["tools"]:
        lines.append(f"    - {tool}")
    lines.append(f"generated_at: {yaml_escape(data['generated_at'])}")

    for section in ("apps", "services"):
        items = data.get(section) or []
        if not items:
            lines.append(f"{section}: []")
            continue
        lines.append(f"{section}:")
        for item in items:
            lines.append(f"  - id: {yaml_escape(str(item.get('id', '')))}")
            lines.append(f"    name: {yaml_escape(str(item.get('name', '')))}")
            lines.append(f"    project: {yaml_escape(str(item.get('project', '')))}")
            tags = item.get("tags") or []
            if not tags:
                lines.append("    tags: []")
            else:
                lines.append("    tags:")
                for tag in tags:
                    lines.append(f"      - {yaml_escape(str(tag))}")
    return "\n".join(lines) + "\n"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--applications",
        type=Path,
        required=True,
        help="Path to list_applications.json",
    )
    p.add_argument(
        "--services",
        type=Path,
        required=True,
        help="Path to list_services.json",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("/knowledge/inventory/coolify/inventory.yaml"),
        help="Output inventory.yaml path",
    )
    p.add_argument(
        "--also-json",
        type=Path,
        default=None,
        help="Optional sibling inventory.json path",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    inventory = build_inventory(
        load_json(args.applications),
        load_json(args.services),
    )
    atomic_write_text(args.output, dump_lean_yaml(inventory))
    print(f"Wrote {args.output}")
    if args.also_json:
        atomic_write_text(
            args.also_json,
            json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
        )
        print(f"Wrote {args.also_json}")
    print(f"apps={len(inventory['apps'])} services={len(inventory['services'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
