#!/usr/bin/env python3
"""Dump normalized Coolify or Tailscale input without building inventory.

Usage:
  python scripts/inspect_sources.py coolify --input path/to/coolify.json
  python scripts/inspect_sources.py tailscale --input path/to/tailscale.json

Never prints secrets or tokens.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from filter import extract_category, filter_dashboard_resources, filter_excluded_resources  # noqa: E402
from models import CoolifyAdapter, TailscaleAdapter  # noqa: E402
from normalize import normalize_name  # noqa: E402


SECRET_KEYS = {
    "token",
    "password",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "private_key",
}


def scrub(obj: object) -> object:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in SECRET_KEYS or any(
                s in kl for s in ("password", "token", "secret", "api_key")
            ):
                out[k] = "<redacted>"
            else:
                out[k] = scrub(v)
        return out
    if isinstance(obj, list):
        return [scrub(x) for x in obj]
    return obj


def inspect_coolify(data: object) -> None:
    resources = CoolifyAdapter().collect_resources(data)
    print(f"Coolify resources: {len(resources)}")
    tagged = filter_dashboard_resources(resources)
    print(f"With dashboard tag: {len(tagged)}")
    kept, excluded = filter_excluded_resources(
        tagged,
        {
            "resource_name_suffixes": ["-tailscale"],
            "components": ["tailscale-sidecar"],
        },
    )
    print(f"After exclusions: {len(kept)} (excluded {len(excluded)})")
    for r in kept:
        cat = extract_category(r)
        print(
            f"- {r.name!r} id={r.id} type={r.resource_type} "
            f"norm={normalize_name(r.name)} category={cat} tags={r.tags}"
        )
    if excluded:
        print("Excluded:")
        for r in excluded:
            print(f"- {r.name!r} labels={r.labels}")


def inspect_tailscale(data: object) -> None:
    devices = TailscaleAdapter().collect_resources(data)
    print(f"Tailscale devices: {len(devices)}")
    for d in devices:
        print(
            f"- hostname={d.hostname!r} dns={d.dns_name!r} "
            f"online={d.online} norm={normalize_name(d.hostname)}"
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", choices=("coolify", "tailscale"))
    p.add_argument("--input", type=Path, required=True)
    args = p.parse_args()
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    raw = scrub(raw)
    if args.source == "coolify":
        inspect_coolify(raw)
    else:
        inspect_tailscale(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
