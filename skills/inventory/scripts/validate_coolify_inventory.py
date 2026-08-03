#!/usr/bin/env python3
"""Validate Coolify hierarchical inventory YAML or JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

URL_SCHEMES = {"http", "https"}


def load_doc(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError:
            print(
                "PyYAML is required for YAML validation.\nInstall with: pip install pyyaml",
                file=sys.stderr,
            )
            raise SystemExit(2)
        return yaml.safe_load(text)
    return json.loads(text)


def err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def validate_url(value: str, path: str, errors: list[str]) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in URL_SCHEMES or not parsed.netloc:
        err(errors, f"{path}: invalid URL {value!r}")


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["document must be a mapping/object"]

    if data.get("version") != 1 and not isinstance(data.get("version"), int):
        err(errors, "version must be an integer")
    elif isinstance(data.get("version"), int) and data["version"] < 1:
        err(errors, "version must be >= 1")

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

    projects = data.get("projects")
    if not isinstance(projects, dict):
        err(errors, "projects must be an object/map")
        return errors

    seen_ids: set[str] = set()

    def check_id(rid: str, where: str) -> None:
        if not rid:
            err(errors, f"{where}: empty id")
            return
        if rid in seen_ids:
            err(errors, f"duplicate id {rid!r} at {where}")
        seen_ids.add(rid)

    for pkey, project in projects.items():
        where = f"projects.{pkey}"
        if not isinstance(project, dict):
            err(errors, f"{where}: must be an object")
            continue
        if not project.get("name"):
            err(errors, f"{where}: name is required")
        pid = str(project.get("id") or "")
        check_id(pid, where)
        envs = project.get("environments")
        if not isinstance(envs, dict):
            err(errors, f"{where}: environments must be an object/map")
            continue
        for ekey, env in envs.items():
            ewhere = f"{where}.environments.{ekey}"
            if not isinstance(env, dict):
                err(errors, f"{ewhere}: must be an object")
                continue
            if not env.get("name"):
                err(errors, f"{ewhere}: name is required")
            check_id(str(env.get("id") or ""), ewhere)
            for collection in ("applications", "services", "databases"):
                block = env.get(collection)
                if block is None:
                    continue
                if not isinstance(block, dict):
                    err(errors, f"{ewhere}.{collection}: must be an object/map")
                    continue
                for rkey, res in block.items():
                    rwhere = f"{ewhere}.{collection}.{rkey}"
                    if not isinstance(res, dict):
                        err(errors, f"{rwhere}: must be an object")
                        continue
                    if not res.get("name"):
                        err(errors, f"{rwhere}: name is required")
                    check_id(str(res.get("id") or ""), rwhere)
                    domains = res.get("domains")
                    if domains is None:
                        continue
                    if not isinstance(domains, list):
                        err(errors, f"{rwhere}.domains: must be a list")
                        continue
                    for i, d in enumerate(domains):
                        if not isinstance(d, str):
                            err(errors, f"{rwhere}.domains[{i}]: must be a string")
                        else:
                            validate_url(d, f"{rwhere}.domains[{i}]", errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if not args.path.exists():
        print(f"File not found: {args.path}", file=sys.stderr)
        return 1
    try:
        data = load_doc(args.path)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to parse {args.path}: {exc}", file=sys.stderr)
        return 1
    errors = validate(data)
    if errors:
        print(f"Validation failed ({len(errors)}):", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
