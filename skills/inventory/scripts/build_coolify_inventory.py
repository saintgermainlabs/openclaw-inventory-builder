#!/usr/bin/env python3
"""Build hierarchical Coolify inventory YAML/JSON from normalized raw JSON.

Does not make network calls.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SLUG_RE = re.compile(r"[^a-z0-9]+")


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(value: str, fallback: str = "item") -> str:
    s = SLUG_RE.sub("-", (value or "").strip().lower()).strip("-")
    return s or fallback


def drop_nulls(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: drop_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [drop_nulls(v) for v in obj if v is not None]
    return obj


def require_raw(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        die("raw input must be a JSON object")
    projects = data.get("projects")
    if projects is None:
        die("raw input missing 'projects'")
    if not isinstance(projects, list):
        die("'projects' must be a list")
    return data


def resource_map(items: Any) -> dict[str, Any]:
    if not items:
        return {}
    if not isinstance(items, list):
        die("applications/services/databases must be lists in raw JSON")
    out: dict[str, Any] = {}
    used: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        rid = item.get("id")
        name = item.get("name")
        if not rid or not name:
            die(f"resource missing id/name: {item!r}")
        key = slugify(str(name), fallback=slugify(str(rid), "resource"))
        base = key
        n = 2
        while key in used:
            key = f"{base}-{n}"
            n += 1
        used.add(key)
        entry: dict[str, Any] = {"id": str(rid), "name": str(name)}
        for optional in ("status", "type", "domains", "git", "server"):
            if optional in item and item[optional] is not None:
                entry[optional] = item[optional]
        # preserve extra non-null keys except reserved
        for k, v in item.items():
            if k in entry or k in {"id", "name"} or v is None:
                continue
            entry[k] = v
        out[key] = entry
    # sort by name
    return dict(sorted(out.items(), key=lambda kv: kv[1]["name"].lower()))


def build_inventory(raw: dict[str, Any], generated_at: str) -> dict[str, Any]:
    raw_projects = raw.get("projects") or []
    projects_out: dict[str, Any] = {}
    used_project_keys: set[str] = set()

    sorted_projects = sorted(
        raw_projects,
        key=lambda p: str(p.get("name") or p.get("id") or "").lower(),
    )

    for project in sorted_projects:
        if not isinstance(project, dict):
            continue
        pid = project.get("id")
        pname = project.get("name")
        if not pid or not pname:
            die(f"project missing id/name: {project!r}")
        pkey = slugify(str(pname), fallback=slugify(str(pid), "project"))
        base = pkey
        n = 2
        while pkey in used_project_keys:
            pkey = f"{base}-{n}"
            n += 1
        used_project_keys.add(pkey)

        envs_raw = project.get("environments") or []
        if not isinstance(envs_raw, list):
            die(f"project {pid}: environments must be a list")

        environments: dict[str, Any] = {}
        used_env_keys: set[str] = set()
        for env in sorted(envs_raw, key=lambda e: str((e or {}).get("name") or "").lower()):
            if not isinstance(env, dict):
                continue
            eid = env.get("id")
            ename = env.get("name")
            if not eid or not ename:
                die(f"environment missing id/name under project {pid}")
            ekey = slugify(str(ename), fallback=slugify(str(eid), "environment"))
            ebase = ekey
            m = 2
            while ekey in used_env_keys:
                ekey = f"{ebase}-{m}"
                m += 1
            used_env_keys.add(ekey)

            env_entry: dict[str, Any] = {
                "id": str(eid),
                "name": str(ename),
            }
            apps = resource_map(env.get("applications"))
            services = resource_map(env.get("services"))
            databases = resource_map(env.get("databases"))
            if apps:
                env_entry["applications"] = apps
            if services:
                env_entry["services"] = services
            if databases:
                env_entry["databases"] = databases
            environments[ekey] = env_entry

        projects_out[pkey] = {
            "id": str(pid),
            "name": str(pname),
            "environments": environments,
        }

    inventory: dict[str, Any] = {
        "version": 1,
        "source": {"type": "coolify", "mcp_server": "coolify-readonly"},
        "generated_at": generated_at,
        "projects": projects_out,
    }
    # Preserve complete top-level collections when present in raw.
    for key in ("servers", "domains", "overview", "resources", "extra"):
        if key in raw and raw[key] is not None:
            inventory[key] = raw[key]
    # Any other top-level keys beyond the normalized project tree.
    reserved = {"projects", "servers", "domains", "overview", "resources", "extra"}
    for key, value in raw.items():
        if key in reserved or value is None:
            continue
        inventory.setdefault(key, value)
    return drop_nulls(inventory)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def archive_previous(path: Path, history_dir: Path, retain: int = 20) -> None:
    if not path.exists():
        return
    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = history_dir / f"{path.stem}-{stamp}{path.suffix}"
    shutil.copy2(path, dest)
    files = sorted(history_dir.glob(f"{path.stem}-*{path.suffix}"))
    for old in files[:-retain]:
        old.unlink(missing_ok=True)


def write_yaml(data: dict[str, Any], path: Path) -> None:
    try:
        import yaml
    except ImportError:
        die("PyYAML is required for YAML output.\nInstall with: pip install pyyaml")
    content = yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
    atomic_write_text(path, content)


def write_json(data: dict[str, Any], path: Path) -> None:
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    atomic_write_text(path, content)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True, help="Normalized raw latest.json")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for inventory.yaml / inventory.json",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Single output file (use with --format yaml|json)",
    )
    p.add_argument(
        "--format",
        choices=("yaml", "json", "both"),
        default="both",
    )
    p.add_argument(
        "--history-dir",
        type=Path,
        default=None,
        help="Archive previous inventories here (default: <output-dir>/history)",
    )
    p.add_argument("--no-history", action="store_true")
    p.add_argument("--retain", type=int, default=20)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    inventory = build_inventory(require_raw(raw), utc_now())

    outputs: list[tuple[str, Path]] = []
    if args.output and args.format == "both":
        die("--output requires --format yaml or json (not both)")
    if args.output:
        outputs.append((args.format, args.output))
    else:
        out_dir = args.output_dir or Path("/knowledge/inventory/coolify")
        if args.format in ("yaml", "both"):
            outputs.append(("yaml", out_dir / "inventory.yaml"))
        if args.format in ("json", "both"):
            outputs.append(("json", out_dir / "inventory.json"))

    for fmt, path in outputs:
        history_dir = args.history_dir
        if history_dir is None and not args.no_history:
            history_dir = path.parent / "history"
        if history_dir and not args.no_history:
            archive_previous(path, history_dir, retain=args.retain)
        if fmt == "yaml":
            write_yaml(inventory, path)
        else:
            write_json(inventory, path)
        print(f"Wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
