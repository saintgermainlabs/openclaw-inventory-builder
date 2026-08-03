"""Coolify resource filtering for dashboard inventory."""

from __future__ import annotations

from typing import Any

from models import CoolifyResource
from normalize import normalize_name


def filter_dashboard_resources(
    resources: list[CoolifyResource],
    inclusion_tag: str = "dashboard",
) -> list[CoolifyResource]:
    tag = inclusion_tag.lower()
    return [r for r in resources if tag in {t.lower() for t in r.tags}]


def is_excluded(
    resource: CoolifyResource,
    *,
    name_suffixes: list[str] | None = None,
    components: list[str] | None = None,
) -> bool:
    suffixes = name_suffixes or []
    comps = {c.lower() for c in (components or [])}
    name_l = resource.name.lower()
    for suf in suffixes:
        if name_l.endswith(suf.lower()):
            return True
    component = (resource.labels.get("app.component") or "").lower()
    if component and component in comps:
        return True
    for t in resource.tags:
        if t.lower() in comps:
            return True
    return False


def filter_excluded_resources(
    resources: list[CoolifyResource],
    exclusions: dict[str, Any] | None = None,
) -> tuple[list[CoolifyResource], list[CoolifyResource]]:
    exclusions = exclusions or {}
    suffixes = list(exclusions.get("resource_name_suffixes") or [])
    components = list(exclusions.get("components") or [])
    kept: list[CoolifyResource] = []
    excluded: list[CoolifyResource] = []
    for r in resources:
        if is_excluded(r, name_suffixes=suffixes, components=components):
            excluded.append(r)
        else:
            kept.append(r)
    return kept, excluded


def extract_category(
    resource: CoolifyResource,
    *,
    category_prefix: str = "category:",
    default: str = "other",
) -> str:
    """Return category key (e.g. monitoring) from category:* tag."""
    prefix_l = category_prefix.lower()
    for tag in resource.tags:
        t = tag.strip()
        if t.lower().startswith(prefix_l):
            idx = t.find(":")
            raw = t[idx + 1 :].strip().lower() if idx >= 0 else ""
            if raw:
                return normalize_name(raw) or default
    return default
