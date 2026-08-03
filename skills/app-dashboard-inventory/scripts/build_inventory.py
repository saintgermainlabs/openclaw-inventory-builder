#!/usr/bin/env python3
"""Build app-dashboard.yaml from Coolify + Tailscale normalized JSON.

Does not make network calls. Coolify is authoritative; Tailscale enriches
hostname / dns_name / online / tailscale-tags.

Output shape (flat apps map):

```yaml
version: 1
generated: { at: …, sources: [coolify, tailscale] }
apps:
  portal:
    hostname: portal
    dns_name: portal.tiger-bushmaster.ts.net
    online: true
    tailscale-tags: ["tag:portal", "tag:ui"]
    coolify_id: …
    status: running
    tags: ["dashboard"]
    labels: {}
    name: …
    project: Portal
    resource_type: application
```
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from filter import (  # noqa: E402
    filter_dashboard_resources,
    filter_excluded_resources,
)
from match import match_tailscale_resource  # noqa: E402
from models import CoolifyAdapter, CoolifyResource, TailscaleAdapter, TailscaleResource  # noqa: E402
from normalize import normalize_name  # noqa: E402


def log(level: str, msg: str) -> None:
    print(f"[{level}] {msg}", file=sys.stderr)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> Any:
    try:
        import yaml
    except ImportError:
        print("PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
        raise SystemExit(2)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def dump_yaml(data: Any) -> str:
    try:
        import yaml
    except ImportError:
        print("PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
        raise SystemExit(2)
    return yaml.safe_dump(data, sort_keys=False, default_flow_style=False)


def load_config(
    defaults_path: Path | None = None,
    apps_path: Path | None = None,
) -> dict[str, Any]:
    defaults_path = defaults_path or (SKILL_DIR / "config" / "defaults.yaml")
    apps_path = apps_path or (SKILL_DIR / "config" / "apps.yaml")
    cfg = load_yaml(defaults_path) if defaults_path.exists() else {}
    apps_doc = load_yaml(apps_path) if apps_path.exists() else {}
    cfg["apps"] = apps_doc.get("apps") or {}
    return cfg


def resolve_app_id(resource: CoolifyResource, apps_cfg: dict[str, Any]) -> str:
    norm = normalize_name(resource.name)
    for app_id, meta in apps_cfg.items():
        if normalize_name(app_id) == norm:
            return normalize_name(app_id)
        if isinstance(meta, dict):
            for alias in meta.get("aliases") or []:
                if normalize_name(str(alias)) == norm:
                    return normalize_name(app_id)
    return norm


def dns_for_device(
    device: TailscaleResource,
    *,
    domain_suffix: str,
) -> str | None:
    if device.dns_name and "." in device.dns_name:
        return device.dns_name.rstrip(".")
    if device.hostname and domain_suffix:
        return f"{device.hostname}.{domain_suffix}"
    return device.dns_name


def build_application_record(
    resource: CoolifyResource,
    match: Any,
    *,
    app_id: str,
    domain_suffix: str,
) -> dict[str, Any]:
    """Build one flat app node matching the inventory template."""
    hostname: str | None = None
    dns_name: str | None = None
    online: bool | None = None
    ts_tags: list[str] = []

    device: TailscaleResource | None = match.resource if match else None
    if match and match.ambiguous:
        pass
    elif device:
        hostname = device.hostname
        dns_name = dns_for_device(device, domain_suffix=domain_suffix)
        online = device.online
        ts_tags = list(device.tags or [])

    # Prefer Tailscale hostname as map key when matched; else resolved app_id
    key = normalize_name(hostname) if hostname else app_id

    record: dict[str, Any] = {
        "hostname": hostname,
        "dns_name": dns_name,
        "online": online,
        "tailscale-tags": ts_tags,
        "coolify_id": resource.id,
        "status": resource.status or "unknown",
        "tags": list(resource.tags or []),
        "labels": dict(resource.labels or {}),
        "name": resource.name,
        "project": resource.project,
        "resource_type": resource.resource_type,
        "_key": key,
        "_sort_name": resource.name or key,
    }
    return record


def build_inventory(
    coolify_data: Any,
    tailscale_data: Any,
    cfg: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    coolify_cfg = cfg.get("coolify") or {}
    ts_cfg = cfg.get("tailscale") or {}
    matching = cfg.get("matching") or {}
    exclusions = cfg.get("exclusions") or {}
    apps_cfg = cfg.get("apps") or {}

    inclusion_tag = coolify_cfg.get("inclusion_tag") or "dashboard"
    domain_suffix = ts_cfg.get("domain_suffix") or "tiger-bushmaster.ts.net"
    fail_ambiguous = bool(matching.get("fail_on_ambiguous_match", False))

    all_coolify = CoolifyAdapter().collect_resources(coolify_data)
    log("INFO", f"Found {len(all_coolify)} Coolify resources")

    tagged = filter_dashboard_resources(all_coolify, inclusion_tag=inclusion_tag)
    log("INFO", f"{len(tagged)} resources contain {inclusion_tag!r} tag")

    candidates, excluded = filter_excluded_resources(tagged, exclusions)
    log("INFO", f"Excluded {len(excluded)} Tailscale sidecars / excluded resources")

    devices = TailscaleAdapter().collect_resources(tailscale_data)
    log("INFO", f"Matching {len(candidates)} dashboard applications against Tailscale")

    records: list[dict[str, Any]] = []
    matched = 0
    unmatched = 0
    ambiguous = 0

    for resource in candidates:
        app_id = resolve_app_id(resource, apps_cfg)
        result = match_tailscale_resource(resource, devices, apps_cfg=apps_cfg)
        if result.ambiguous:
            ambiguous += 1
            names = ", ".join(d.hostname for d in (result.candidates or []))
            log(
                "WARN",
                f"Ambiguous Tailscale match for {resource.name!r}: {names}",
            )
            if fail_ambiguous:
                raise SystemExit(f"Ambiguous match for {resource.name}")
            result = type(result)(None, result.method, True, result.candidates)
        elif result.resource:
            matched += 1
            dns = dns_for_device(result.resource, domain_suffix=domain_suffix)
            log("INFO", f"Matched {app_id} -> {dns}")
        else:
            unmatched += 1
            log("WARN", f"No Tailscale match found for {resource.name}")

        records.append(
            build_application_record(
                resource,
                result,
                app_id=app_id,
                domain_suffix=domain_suffix,
            )
        )

    seen_keys: set[str] = set()
    apps_out: dict[str, Any] = {}
    for rec in sorted(records, key=lambda r: str(r.get("_sort_name") or "").lower()):
        key = str(rec.get("_key") or "app")
        base = key
        n = 2
        while key in seen_keys:
            key = f"{base}-{n}"
            n += 1
        seen_keys.add(key)
        clean = {k: v for k, v in rec.items() if not k.startswith("_")}
        apps_out[key] = clean

    inventory = {
        "version": 1,
        "generated": {
            "at": generated_at or utc_now(),
            "sources": ["coolify", "tailscale"],
        },
        "apps": apps_out,
    }
    log("INFO", f"Wrote {len(apps_out)} applications to inventory")
    log(
        "INFO",
        f"Matched={matched} unmatched={unmatched} ambiguous={ambiguous}",
    )
    return inventory


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--coolify-input", type=Path, required=True)
    p.add_argument("--tailscale-input", type=Path, required=True)
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--defaults", type=Path, default=None)
    p.add_argument("--apps", type=Path, default=None)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(args.defaults, args.apps)
    coolify_data = json.loads(args.coolify_input.read_text(encoding="utf-8"))
    tailscale_data = json.loads(args.tailscale_input.read_text(encoding="utf-8"))
    inventory = build_inventory(coolify_data, tailscale_data, cfg)

    from validate_inventory import validate  # local import

    errors = validate(inventory)
    if errors:
        for e in errors:
            log("ERROR", e)
        return 1

    out_path = args.output
    if out_path is None:
        out_path = Path(
            (cfg.get("inventory") or {}).get("output")
            or "/data/apps/inventory/app-dashboard.yaml"
        )

    content = dump_yaml(inventory)
    if args.dry_run:
        print(content)
        return 0
    atomic_write_text(out_path, content)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
