#!/usr/bin/env python3
"""Validate app-dashboard inventory YAML (flat apps: template)."""

from __future__ import annotations

import argparse
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
    import json

    return json.loads(text)


REQUIRED_APP_FIELDS = (
    "hostname",
    "dns_name",
    "online",
    "tailscale-tags",
    "coolify_id",
    "status",
    "tags",
    "labels",
    "name",
    "project",
    "resource_type",
)


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["document must be a mapping/object"]

    version = data.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append("version must be an integer >= 1")

    generated = data.get("generated")
    if not isinstance(generated, dict):
        errors.append("generated must be an object")
    else:
        if not generated.get("at"):
            errors.append("generated.at is required")
        sources = generated.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append("generated.sources must be a non-empty list")
        else:
            for s in sources:
                if s not in {"coolify", "tailscale"}:
                    errors.append(f"generated.sources contains unexpected value: {s!r}")

    apps = data.get("apps")
    if not isinstance(apps, dict):
        errors.append("apps must be an object/map")
        return errors

    secret_keys = {
        "token",
        "password",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "private_key",
    }
    seen_ids: set[str] = set()

    for app_key, app in apps.items():
        aw = f"apps.{app_key}"
        if not isinstance(app, dict):
            errors.append(f"{aw}: must be an object")
            continue
        for req in REQUIRED_APP_FIELDS:
            if req not in app:
                errors.append(f"{aw}: missing {req}")

        cid = app.get("coolify_id")
        if cid:
            if cid in seen_ids:
                errors.append(f"duplicate coolify_id {cid!r} at {aw}")
            seen_ids.add(str(cid))

        if "online" in app and app["online"] is not None and not isinstance(app["online"], bool):
            errors.append(f"{aw}: online must be a boolean or null")

        for list_field in ("tags", "tailscale-tags"):
            val = app.get(list_field)
            if val is None:
                continue
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                errors.append(f"{aw}.{list_field}: must be a list of strings")

        labels = app.get("labels")
        if labels is not None and not isinstance(labels, dict):
            errors.append(f"{aw}.labels: must be an object")

        if not app.get("coolify_id"):
            errors.append(f"{aw}: coolify_id is required")
        if not app.get("name"):
            errors.append(f"{aw}: name is required")
        if not app.get("resource_type"):
            errors.append(f"{aw}: resource_type is required")

        stack = [app]
        while stack:
            obj = stack.pop()
            if not isinstance(obj, dict):
                continue
            for k, v in obj.items():
                kl = str(k).lower()
                if kl in secret_keys or any(
                    s in kl for s in ("password", "token", "secret", "api_key")
                ):
                    errors.append(f"{aw}: forbidden secret-like field {k!r}")
                if isinstance(v, dict):
                    stack.append(v)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("/data/apps/inventory/app-dashboard.yaml"),
    )
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
