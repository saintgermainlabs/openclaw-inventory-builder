#!/usr/bin/env python3
"""Validate Tailscale inventory YAML or JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


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


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["document must be a mapping/object"]

    version = data.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append("version must be an integer >= 1")
    if not data.get("generated_at"):
        errors.append("generated_at is required")

    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")
    else:
        if source.get("type") != "tailscale":
            errors.append("source.type must be 'tailscale'")
        if not source.get("mcp_server"):
            errors.append("source.mcp_server is required")

    if "tailnet" in data and data["tailnet"] is not None and not isinstance(data["tailnet"], dict):
        errors.append("tailnet must be an object when present")

    devices = data.get("devices")
    if not isinstance(devices, dict):
        errors.append("devices must be an object/map")
        return errors

    seen: set[str] = set()
    for key, device in devices.items():
        where = f"devices.{key}"
        if not isinstance(device, dict):
            errors.append(f"{where}: must be an object")
            continue
        did = str(device.get("id") or "")
        hostname = device.get("hostname")
        if not did:
            errors.append(f"{where}: id is required")
        if not hostname:
            errors.append(f"{where}: hostname is required")
        if did:
            if did in seen:
                errors.append(f"duplicate id {did!r} at {where}")
            seen.add(did)
        if "online" in device and device["online"] is not None and not isinstance(device["online"], bool):
            errors.append(f"{where}: online must be a boolean")
        for list_field in ("addresses", "tags"):
            val = device.get(list_field)
            if val is None:
                continue
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                errors.append(f"{where}.{list_field}: must be a list of strings")
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
