#!/usr/bin/env python3
"""Build Tailscale device inventory YAML/JSON from normalized raw JSON.

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
OPTIONAL_DEVICE_FIELDS = (
    "name",
    "online",
    "addresses",
    "tags",
    "os",
    "client_version",
    "node_id",
    "last_seen",
    "authorized",
    "user",
)


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(value: str, fallback: str = "device") -> str:
    s = SLUG_RE.sub("-", (value or "").strip().lower()).strip("-")
    return s or fallback


def drop_nulls(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: drop_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [drop_nulls(v) for v in obj if v is not None]
    return obj


def require_devices(data: Any) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not isinstance(data, dict):
        die("raw input must be a JSON object")
    devices = data.get("devices")
    if devices is None:
        die("raw input missing 'devices'")
    if not isinstance(devices, list):
        die("'devices' must be a list")
    tailnet = data.get("tailnet")
    if tailnet is not None and not isinstance(tailnet, dict):
        die("'tailnet' must be an object when present")
    return tailnet, devices


def build_inventory(
    devices: list[dict[str, Any]],
    tailnet: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    out_devices: dict[str, Any] = {}
    used: set[str] = set()

    sorted_devices = sorted(
        devices,
        key=lambda d: str(d.get("hostname") or d.get("name") or d.get("id") or "").lower(),
    )

    for device in sorted_devices:
        if not isinstance(device, dict):
            continue
        did = device.get("id")
        hostname = device.get("hostname")
        if not did or not hostname:
            die(f"device missing id/hostname: {device!r}")
        key = slugify(str(hostname), fallback=slugify(str(did), "device"))
        base = key
        n = 2
        while key in used:
            key = f"{base}-{n}"
            n += 1
        used.add(key)

        entry: dict[str, Any] = {"id": str(did), "hostname": str(hostname)}
        for field in OPTIONAL_DEVICE_FIELDS:
            if field == "hostname":
                continue
            if field in device and device[field] is not None:
                entry[field] = device[field]
        for k, v in device.items():
            if k in entry or k in {"id", "hostname"} or v is None:
                continue
            entry[k] = v
        out_devices[key] = entry

    inventory: dict[str, Any] = {
        "version": 1,
        "source": {"type": "tailscale", "mcp_server": "tailscale-readonly"},
        "generated_at": generated_at,
        "devices": out_devices,
    }
    if tailnet:
        cleaned = drop_nulls(dict(tailnet))
        if cleaned:
            inventory["tailnet"] = cleaned
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
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--format", choices=("yaml", "json", "both"), default="both")
    p.add_argument("--history-dir", type=Path, default=None)
    p.add_argument("--no-history", action="store_true")
    p.add_argument("--retain", type=int, default=20)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    tailnet, devices = require_devices(raw)
    inventory = build_inventory(devices, tailnet, utc_now())

    outputs: list[tuple[str, Path]] = []
    if args.output and args.format == "both":
        die("--output requires --format yaml or json (not both)")
    if args.output:
        outputs.append((args.format, args.output))
    else:
        out_dir = args.output_dir or Path("/knowledge/inventory/tailscale")
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
