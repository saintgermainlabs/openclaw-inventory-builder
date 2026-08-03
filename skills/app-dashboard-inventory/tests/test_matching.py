#!/usr/bin/env python3
"""Matching tests for app-dashboard-inventory."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from match import match_tailscale_resource  # noqa: E402
from models import CoolifyAdapter, CoolifyResource, TailscaleAdapter  # noqa: E402
from normalize import normalize_name  # noqa: E402


def devices():
    data = json.loads((ROOT / "tests" / "fixtures" / "tailscale_resources.json").read_text())
    return TailscaleAdapter().collect_resources(data)


def test_normalize_examples() -> None:
    assert normalize_name("Uptime Kuma") == "uptime-kuma"
    assert normalize_name("Open WebUI") == "open-webui"
    assert normalize_name("Silver Bullet") == "silver-bullet"
    assert normalize_name("VaultWarden") == "vaultwarden"


def test_exact_hostname() -> None:
    coolify = CoolifyResource(
        id="1", name="Uptime Kuma", resource_type="application", tags=["dashboard"]
    )
    result = match_tailscale_resource(coolify, devices())
    assert result.resource is not None
    assert result.resource.hostname == "uptime-kuma"
    assert result.method == "hostname"
    assert not result.ambiguous


def test_alias_mapping() -> None:
    coolify = CoolifyResource(
        id="4", name="Open WebUI", resource_type="application", tags=["dashboard"]
    )
    apps = {
        "open-webui": {
            "aliases": ["ollama-webui"],
            "label": "Open WebUI",
        }
    }
    # Name already normalizes to open-webui; alias path via apps meta
    result = match_tailscale_resource(coolify, devices(), apps_cfg=apps)
    assert result.resource is not None
    assert result.resource.hostname == "open-webui"


def test_alias_from_alternate_coolify_name() -> None:
    coolify = CoolifyResource(
        id="9", name="ollama-webui", resource_type="application", tags=["dashboard"]
    )
    apps = {"open-webui": {"aliases": ["ollama-webui"]}}
    result = match_tailscale_resource(coolify, devices(), apps_cfg=apps)
    assert result.resource is not None
    assert result.resource.hostname == "open-webui"
    assert result.method == "alias"


def test_missing_match() -> None:
    coolify = CoolifyResource(
        id="5", name="code-server", resource_type="application", tags=["dashboard"]
    )
    result = match_tailscale_resource(coolify, devices())
    assert result.resource is None
    assert not result.ambiguous


def test_ambiguous_match() -> None:
    coolify = CoolifyResource(
        id="x", name="dup-a", resource_type="application", tags=["dashboard"]
    )
    result = match_tailscale_resource(coolify, devices())
    assert result.ambiguous
    assert result.resource is None
    assert result.candidates and len(result.candidates) == 2


def test_laptop_never_matched_as_app() -> None:
    # Matching is Coolify-driven; laptop only appears if Coolify asks for it
    coolify = CoolifyResource(
        id="1", name="Uptime Kuma", resource_type="application", tags=["dashboard"]
    )
    result = match_tailscale_resource(coolify, devices())
    assert result.resource and result.resource.hostname != "dom-laptop"


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
