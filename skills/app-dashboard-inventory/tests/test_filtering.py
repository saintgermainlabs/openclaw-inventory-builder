#!/usr/bin/env python3
"""Filtering tests for app-dashboard-inventory."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from filter import (  # noqa: E402
    extract_category,
    filter_dashboard_resources,
    filter_excluded_resources,
)
from models import CoolifyAdapter  # noqa: E402


def load_coolify() -> list:
    data = json.loads((ROOT / "tests" / "fixtures" / "coolify_resources.json").read_text())
    return CoolifyAdapter().collect_resources(data)


def test_dashboard_tag_included() -> None:
    resources = load_coolify()
    tagged = filter_dashboard_resources(resources)
    names = {r.name for r in tagged}
    assert "Uptime Kuma" in names
    assert "Open WebUI" in names


def test_missing_dashboard_excluded() -> None:
    resources = load_coolify()
    tagged = filter_dashboard_resources(resources)
    names = {r.name for r in tagged}
    assert "PostgreSQL" not in names


def test_sidecar_excluded() -> None:
    resources = load_coolify()
    tagged = filter_dashboard_resources(resources)
    kept, excluded = filter_excluded_resources(
        tagged,
        {
            "resource_name_suffixes": ["-tailscale"],
            "components": ["tailscale-sidecar"],
        },
    )
    names = {r.name for r in kept}
    excl = {r.name for r in excluded}
    assert "uptime-kuma-tailscale" not in names
    # sidecar without dashboard tag never enters tagged; suffix one with dashboard is excluded
    assert "sidecar-by-suffix-tailscale" in excl
    assert "sidecar-by-suffix-tailscale" not in names


def test_database_excluded_by_default() -> None:
    resources = load_coolify()
    tagged = filter_dashboard_resources(resources)
    assert all(r.name != "PostgreSQL" for r in tagged)


def test_category_parsed() -> None:
    resources = load_coolify()
    uptime = next(r for r in resources if r.name == "Uptime Kuma")
    assert extract_category(uptime) == "monitoring"


def test_missing_category_defaults_other() -> None:
    resources = load_coolify()
    mystery = next(r for r in resources if r.name == "Mystery App")
    assert extract_category(mystery) == "other"


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {name}: {exc}")
    raise SystemExit(failures)
