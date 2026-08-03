from __future__ import annotations

import json
from pathlib import Path

import yaml

from inventory_lib import (
    apply_overrides,
    atomic_write_yaml,
    correlate_by_hostname,
    format_diff_summary,
    inventory_diff,
    load_schema,
    normalize_name,
    validate_services_dict,
    write_history,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "skills/infrastructure-inventory/schemas/inventory.schema.json"
EXAMPLE = ROOT / "examples/inventory/services.example.yaml"


def test_example_services_validate():
    data = yaml.safe_load(EXAMPLE.read_text())
    schema = load_schema(SCHEMA)
    assert validate_services_dict(data, schema) == []


def test_invalid_missing_name_fails():
    schema = load_schema(SCHEMA)
    bad = {
        "version": 1,
        "generated_at": "2026-08-02T00:00:00Z",
        "services": {"bad": {}},
    }
    errors = validate_services_dict(bad, schema)
    assert errors


def test_overrides_survive_merge():
    services = {
        "uptime-kuma": {
            "name": "Uptime Kuma",
            "dashboard": {"enabled": True, "category": "Other"},
        }
    }
    overrides = {
        "uptime-kuma": {
            "dashboard": {"name": "Uptime", "category": "Monitoring", "order": 10}
        }
    }
    merged = apply_overrides(services, overrides)
    assert merged["uptime-kuma"]["dashboard"]["name"] == "Uptime"
    assert merged["uptime-kuma"]["dashboard"]["category"] == "Monitoring"
    assert merged["uptime-kuma"]["dashboard"]["enabled"] is True
    assert merged["uptime-kuma"]["dashboard"]["order"] == 10


def test_diff_detects_add_and_status_change():
    before = {
        "services": {
            "uptime-kuma": {
                "name": "Uptime Kuma",
                "status": {"application": "running", "tailnet": "offline"},
            }
        }
    }
    after = {
        "services": {
            "uptime-kuma": {
                "name": "Uptime Kuma",
                "status": {"application": "running", "tailnet": "online"},
            },
            "vikunja": {"name": "Vikunja"},
        },
        "unmatched": {"coolify": [{"name": "postgres-production"}], "tailscale": []},
    }
    diff = inventory_diff(before, after)
    assert diff["added"] == ["vikunja"]
    assert any("tailnet offline -> online" in c for c in diff["changed"])
    summary = format_diff_summary(diff)
    assert "vikunja" in summary
    assert "No infrastructure modifications were performed." in summary


def test_atomic_write_and_history(tmp_path: Path):
    dest = tmp_path / "services.yaml"
    history = tmp_path / "history"
    first = {"version": 1, "generated_at": "t1", "services": {"a": {"name": "A"}}}
    second = {"version": 1, "generated_at": "t2", "services": {"a": {"name": "A"}, "b": {"name": "B"}}}
    atomic_write_yaml(first, dest)
    write_history(dest, history, retain=5)
    atomic_write_yaml(second, dest)
    assert dest.exists()
    assert list(history.glob("services-*.yaml"))


def test_correlate_exact_hostname():
    coolify = [
        {"id": "abc", "name": "uptime-kuma", "status": "running", "resource_type": "service"},
        {"id": "db1", "name": "postgres-production", "status": "running", "resource_type": "database"},
    ]
    tailscale = [
        {
            "hostname": "uptime-kuma",
            "dns_name": "uptime-kuma.tiger-bushmaster.ts.net.",
            "online": True,
        }
    ]
    services, unmatched_c, unmatched_t = correlate_by_hostname(coolify, tailscale)
    assert "uptimekuma" in services or "uptime-kuma" in [
        normalize_name(k) for k in services
    ]
    matched = next(s for s in services.values() if s["name"] == "uptime-kuma")
    assert matched["correlation"]["status"] == "confirmed"
    assert any(u["name"] == "postgres-production" for u in unmatched_c)
    assert unmatched_t == []


def test_schema_file_is_json():
    raw = json.loads(SCHEMA.read_text())
    assert raw["required"] == ["version", "generated_at", "services"]


def test_repo_has_no_literal_bearer_secrets():
    """Committed files must not contain real-looking bearer tokens."""
    import re

    patterns = (
        re.compile(r"tskey-[a-z]+-[A-Za-z0-9]+"),
        re.compile(r"eyJhbGci[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
        re.compile(r"Bearer\s+sk-[A-Za-z0-9]+"),
    )
    skip_parts = {".git", ".venv", "__pycache__", "node_modules"}
    for path in ROOT.rglob("*"):
        if path.is_dir() or skip_parts.intersection(path.parts):
            continue
        if path.suffix in {".png", ".pyc"}:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(errors="ignore")
        for pattern in patterns:
            assert not pattern.search(text), f"{path} matches {pattern.pattern}"


def test_forbidden_ops_are_documented_in_skill():
    skill = (ROOT / "skills/infrastructure-inventory/SKILL.md").read_text()
    assert "This is a read-only infrastructure discovery skill." in skill
    for word in ("deploy", "restart", "delete", "modify Tailscale ACLs"):
        assert word in skill
