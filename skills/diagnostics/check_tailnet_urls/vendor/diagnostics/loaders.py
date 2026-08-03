"""Load UI targets from inventory YAML files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Target:
    """A service/application URL intended for browser UI access."""

    id: str
    name: str
    url: str
    category: str | None = None
    source: str | None = None  # inventory provenance, e.g. app-dashboard


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def targets_from_app_dashboard(data: dict[str, Any], *, source: str) -> list[Target]:
    """Extract UI URLs from app-dashboard.yaml.

    Supports:
    - flat `apps:` map (current) — URL from `https://{dns_name}`
    - legacy `categories.*.applications` with `ui.url`
    """
    targets: list[Target] = []

    apps = data.get("apps")
    if isinstance(apps, dict):
        for app_id, app in apps.items():
            if not isinstance(app, dict):
                continue
            dns = app.get("dns_name")
            if not dns:
                continue
            # Prefer dashboard-tagged apps when tags present
            tags = app.get("tags") or []
            if isinstance(tags, list) and tags and "dashboard" not in {
                str(t).lower() for t in tags
            }:
                continue
            targets.append(
                Target(
                    id=str(app_id),
                    name=str(app.get("name") or app_id),
                    url=f"https://{dns}",
                    category=None,
                    source=source,
                )
            )
        return targets

    categories = data.get("categories") or {}
    if not isinstance(categories, dict):
        return targets
    for cat_key, cat in categories.items():
        if not isinstance(cat, dict):
            continue
        nested = cat.get("applications") or {}
        if not isinstance(nested, dict):
            continue
        for app_id, app in nested.items():
            if not isinstance(app, dict):
                continue
            ui = app.get("ui") or {}
            if not isinstance(ui, dict):
                continue
            url = ui.get("url")
            if not url or not ui.get("enabled", True):
                continue
            targets.append(
                Target(
                    id=str(app.get("id") or app_id),
                    name=str(app.get("name") or app_id),
                    url=str(url),
                    category=str(app.get("category") or cat_key),
                    source=source,
                )
            )
    return targets


def targets_from_services_yaml(data: dict[str, Any], *, source: str) -> list[Target]:
    """Extract private_url entries from correlated services.yaml shape."""
    targets: list[Target] = []
    services = data.get("services") or {}
    if not isinstance(services, dict):
        return targets
    for sid, svc in services.items():
        if not isinstance(svc, dict):
            continue
        dash = svc.get("dashboard") or {}
        network = svc.get("network") or {}
        url = None
        if isinstance(network, dict):
            url = network.get("private_url") or network.get("url")
        if not url:
            continue
        if isinstance(dash, dict) and "enabled" in dash and not dash.get("enabled"):
            continue
        targets.append(
            Target(
                id=str(sid),
                name=str(svc.get("name") or sid),
                url=str(url),
                category=(
                    str(dash.get("category"))
                    if isinstance(dash, dict) and dash.get("category")
                    else None
                ),
                source=source,
            )
        )
    return targets


def collect_ui_targets(
    inventory_path: Path,
    *,
    format_hint: str | None = None,
) -> list[Target]:
    """Load UI targets from an inventory file.

    Auto-detects flat app-dashboard (`apps`), legacy categories, or services.yaml.
    """
    data = load_yaml(inventory_path)
    if not isinstance(data, dict):
        raise ValueError(f"Inventory must be a mapping: {inventory_path}")

    source = str(inventory_path)
    hint = (format_hint or "").lower()
    if hint in {"app-dashboard", "dashboard"} or "apps" in data or "categories" in data:
        return targets_from_app_dashboard(data, source=source)
    if hint in {"services", "services.yaml"} or "services" in data:
        return targets_from_services_yaml(data, source=source)
    raise ValueError(
        f"Unrecognized inventory shape in {inventory_path} "
        "(expected app-dashboard apps/categories or services map)"
    )
