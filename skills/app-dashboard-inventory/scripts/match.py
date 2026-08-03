"""Deterministic Coolify ↔ Tailscale matching (no fuzzy)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models import CoolifyResource, TailscaleResource
from normalize import normalize_name


@dataclass
class MatchResult:
    resource: TailscaleResource | None
    method: str | None  # alias | hostname | name | service_name | None
    ambiguous: bool = False
    candidates: list[TailscaleResource] | None = None


def _app_meta_map(apps_cfg: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Map normalized alias/id -> app config entry (including canonical id)."""
    apps_cfg = apps_cfg or {}
    index: dict[str, dict[str, Any]] = {}
    for app_id, meta in apps_cfg.items():
        if not isinstance(meta, dict):
            meta = {}
        entry = {"id": app_id, **meta}
        index[normalize_name(app_id)] = entry
        for alias in meta.get("aliases") or []:
            index[normalize_name(str(alias))] = entry
    return index


def build_alias_hostname_index(
    apps_cfg: dict[str, Any] | None,
    devices: list[TailscaleResource],
) -> dict[str, list[TailscaleResource]]:
    """For each app id/alias, devices whose hostname normalizes to that key."""
    by_host: dict[str, list[TailscaleResource]] = {}
    for d in devices:
        key = normalize_name(d.hostname)
        by_host.setdefault(key, []).append(d)
    return by_host


def match_tailscale_resource(
    coolify: CoolifyResource,
    devices: list[TailscaleResource],
    *,
    apps_cfg: dict[str, Any] | None = None,
) -> MatchResult:
    """Matching order: alias → exact hostname → normalized name → service name.

    If multiple devices match at the winning step, mark ambiguous and return none.
    """
    by_host: dict[str, list[TailscaleResource]] = {}
    for d in devices:
        by_host.setdefault(normalize_name(d.hostname), []).append(d)

    app_index = _app_meta_map(apps_cfg)
    app_norm = normalize_name(coolify.name)

    # 1. Explicit alias from local config
    # If coolify name (or its norm) maps to an apps.yaml entry, try that entry's
    # id and aliases against hostnames.
    meta = app_index.get(app_norm)
    if meta:
        keys = [normalize_name(meta["id"])]
        for alias in meta.get("aliases") or []:
            keys.append(normalize_name(str(alias)))
        hits: list[TailscaleResource] = []
        seen: set[int] = set()
        for key in keys:
            for d in by_host.get(key, []):
                ident = id(d)
                if ident not in seen:
                    seen.add(ident)
                    hits.append(d)
        if len(hits) == 1:
            return MatchResult(hits[0], "alias")
        if len(hits) > 1:
            return MatchResult(None, "alias", ambiguous=True, candidates=hits)

    # 2. Exact hostname match (normalized hostname == normalized app name)
    hits = by_host.get(app_norm, [])
    if len(hits) == 1:
        return MatchResult(hits[0], "hostname")
    if len(hits) > 1:
        return MatchResult(None, "hostname", ambiguous=True, candidates=hits)

    # 3. Exact normalized application name already covered by hostname step
    # (hostname index is the only Tailscale identity we match).

    # 4. Exact normalized service name match
    if coolify.service_name:
        svc = normalize_name(coolify.service_name)
        if svc != app_norm:
            hits = by_host.get(svc, [])
            if len(hits) == 1:
                return MatchResult(hits[0], "service_name")
            if len(hits) > 1:
                return MatchResult(
                    None, "service_name", ambiguous=True, candidates=hits
                )

    return MatchResult(None, None)
