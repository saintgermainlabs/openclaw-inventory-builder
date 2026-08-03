"""Inventory helpers: validate, merge overrides, diff, atomic write."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SERVICE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def dump_yaml(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, default_flow_style=False)


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def apply_overrides(services: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    """Merge overrides into services map. Overrides win for nested dashboard keys."""
    if not overrides:
        return services
    out = {k: dict(v) if isinstance(v, dict) else v for k, v in services.items()}
    for sid, ov in overrides.items():
        if not isinstance(ov, dict):
            continue
        if sid not in out:
            continue
        current = dict(out[sid])
        for key, val in ov.items():
            if key == "dashboard" and isinstance(val, dict):
                dash = dict(current.get("dashboard") or {})
                dash.update(val)
                current["dashboard"] = dash
            elif key == "sources" and isinstance(val, dict):
                sources = dict(current.get("sources") or {})
                for sk, sv in val.items():
                    if isinstance(sv, dict):
                        nested = dict(sources.get(sk) or {})
                        nested.update(sv)
                        sources[sk] = nested
                    else:
                        sources[sk] = sv
                current["sources"] = sources
            else:
                current[key] = val
        out[sid] = current
    return out


def inventory_diff(before: dict[str, Any] | None, after: dict[str, Any]) -> dict[str, Any]:
    before_services = (before or {}).get("services") or {}
    after_services = after.get("services") or {}
    before_ids = set(before_services)
    after_ids = set(after_services)
    added = sorted(after_ids - before_ids)
    removed = sorted(before_ids - after_ids)
    changed: list[str] = []
    for sid in sorted(before_ids & after_ids):
        b = before_services[sid]
        a = after_services[sid]
        notes: list[str] = []
        bs = (b.get("status") or {})
        as_ = (a.get("status") or {})
        if bs.get("application") != as_.get("application"):
            notes.append(
                f"application {bs.get('application')} -> {as_.get('application')}"
            )
        if bs.get("tailnet") != as_.get("tailnet"):
            notes.append(f"tailnet {bs.get('tailnet')} -> {as_.get('tailnet')}")
        bu = ((b.get("network") or {}).get("private_url"))
        au = ((a.get("network") or {}).get("private_url"))
        if bu != au:
            notes.append(f"url {bu} -> {au}")
        if notes:
            changed.append(f"{sid}: " + "; ".join(notes))
    unmatched = after.get("unmatched") or {}
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unmatched_coolify": unmatched.get("coolify") or [],
        "unmatched_tailscale": unmatched.get("tailscale") or [],
    }


def format_diff_summary(diff: dict[str, Any]) -> str:
    lines = ["Inventory refreshed.", ""]
    if diff["added"]:
        lines.append("Added:")
        lines.extend(f"- {x}" for x in diff["added"])
        lines.append("")
    if diff["removed"]:
        lines.append("Removed:")
        lines.extend(f"- {x}" for x in diff["removed"])
        lines.append("")
    if diff["changed"]:
        lines.append("Changed:")
        lines.extend(f"- {x}" for x in diff["changed"])
        lines.append("")
    unmatched = []
    for item in diff.get("unmatched_coolify") or []:
        if isinstance(item, dict):
            unmatched.append(item.get("name") or item.get("id") or str(item))
        else:
            unmatched.append(str(item))
    for item in diff.get("unmatched_tailscale") or []:
        if isinstance(item, dict):
            unmatched.append(item.get("hostname") or item.get("name") or str(item))
        else:
            unmatched.append(str(item))
    if unmatched:
        lines.append("Unmatched:")
        lines.extend(f"- {x}" for x in unmatched)
        lines.append("")
    lines.append("No infrastructure modifications were performed.")
    return "\n".join(lines)


def validate_services_dict(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Lightweight validation (jsonschema if installed, else structural checks)."""
    errors: list[str] = []
    try:
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema)
        errors.extend(e.message for e in sorted(validator.iter_errors(data), key=lambda e: e.path))
    except ImportError:
        if data.get("version") is None:
            errors.append("missing version")
        if not data.get("generated_at"):
            errors.append("missing generated_at")
        services = data.get("services")
        if not isinstance(services, dict):
            errors.append("services must be a mapping")
        else:
            seen: set[str] = set()
            for sid, svc in services.items():
                if sid in seen:
                    errors.append(f"duplicate service id {sid}")
                seen.add(sid)
                if not SERVICE_ID_RE.match(sid):
                    errors.append(f"invalid service id {sid}")
                if not isinstance(svc, dict) or not svc.get("name"):
                    errors.append(f"service {sid} missing name")
                url = ((svc or {}).get("network") or {}).get("private_url")
                if url and not str(url).startswith(("http://", "https://")):
                    errors.append(f"service {sid} invalid private_url")
                corr = (svc or {}).get("correlation") or {}
                status = corr.get("status")
                if status and status not in {"confirmed", "probable", "unmatched", "conflict"}:
                    errors.append(f"service {sid} invalid correlation.status")
    return errors


def load_schema(schema_path: Path) -> dict[str, Any]:
    with schema_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def atomic_write_yaml(data: Any, final_path: Path) -> None:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = final_path.with_suffix(final_path.suffix + ".tmp")
    dump_yaml(data, tmp)
    tmp.replace(final_path)


def write_history(previous: Path, history_dir: Path, retain: int = 20) -> Path | None:
    if not previous.exists():
        return None
    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = history_dir / f"services-{stamp}.yaml"
    shutil.copy2(previous, dest)
    files = sorted(history_dir.glob("services-*.yaml"))
    for old in files[:-retain]:
        old.unlink(missing_ok=True)
    return dest


def correlate_by_hostname(
    coolify_resources: list[dict[str, Any]],
    tailscale_devices: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Exact hostname/name matches → confirmed services; return unmatched lists."""
    devices_by_host = {
        d["hostname"]: d for d in tailscale_devices if d.get("hostname")
    }
    used_hosts: set[str] = set()
    services: dict[str, Any] = {}
    unmatched_coolify: list[dict[str, Any]] = []

    for res in coolify_resources:
        name = res.get("name") or ""
        sid = normalize_name(name) or normalize_name(res.get("id") or "unknown")
        device = devices_by_host.get(name)
        entry: dict[str, Any] = {
            "name": name or sid,
            "sources": {
                "coolify": {
                    "resource_id": str(res.get("id") or ""),
                    "resource_type": res.get("resource_type") or "service",
                }
            },
            "status": {
                "application": res.get("status") or "unknown",
                "tailnet": "unknown",
            },
        }
        if device:
            used_hosts.add(name)
            entry["sources"]["tailscale"] = {"hostname": device["hostname"]}
            entry["status"]["tailnet"] = "online" if device.get("online") else "offline"
            dns = device.get("dns_name")
            if dns:
                host = dns.rstrip(".")
                entry["network"] = {"private_url": f"https://{host}"}
            entry["correlation"] = {
                "status": "confirmed",
                "confidence": 1.0,
                "evidence": ["exact Tailscale hostname == Coolify service name"],
            }
        else:
            entry["correlation"] = {
                "status": "unmatched",
                "confidence": 0.0,
                "evidence": ["no Tailscale hostname match"],
            }
            unmatched_coolify.append(res)
        # avoid colliding ids
        base = sid
        n = 2
        while sid in services:
            sid = f"{base}-{n}"
            n += 1
        services[sid] = entry

    unmatched_tailscale = [
        d for host, d in devices_by_host.items() if host not in used_hosts
    ]
    return services, unmatched_coolify, unmatched_tailscale
