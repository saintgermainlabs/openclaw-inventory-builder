"""Tests for diagnostics URL reachability."""

from __future__ import annotations

from pathlib import Path

import yaml

from diagnostics.check_urls import check_targets, run_inventory_check
from diagnostics.http_check import ProbeResult
from diagnostics.loaders import Target, collect_ui_targets
from diagnostics.report import format_reachability_report

FIXTURE_DASHBOARD = """
version: 1
generated:
  at: "2026-08-03T00:00:00Z"
  sources: [coolify, tailscale]
categories:
  monitoring:
    label: Monitoring
    order: 40
    applications:
      uptime-kuma:
        id: uptime-kuma
        name: Uptime Kuma
        category: monitoring
        status: {application: running, tailscale: online}
        ui:
          enabled: true
          url: https://uptime-kuma.example.ts.net
          source: tailscale
        coolify: {uuid: "1", resource_type: application}
        tailscale: {hostname: uptime-kuma, dns_name: uptime-kuma.example.ts.net}
      offline-app:
        id: offline-app
        name: Offline App
        category: monitoring
        status: {application: running, tailscale: offline}
        ui:
          enabled: true
          url: https://offline.example.ts.net
          source: tailscale
        coolify: {uuid: "2", resource_type: application}
        tailscale: {hostname: offline, dns_name: offline.example.ts.net}
      no-ui:
        id: no-ui
        name: No UI
        category: monitoring
        status: {application: running, tailscale: unknown}
        ui:
          enabled: false
          url: null
          source: null
        coolify: {uuid: "3", resource_type: application}
        tailscale: {hostname: null, dns_name: null}
"""


def test_collect_skips_disabled_ui(tmp_path: Path) -> None:
    path = tmp_path / "app-dashboard.yaml"
    path.write_text(FIXTURE_DASHBOARD, encoding="utf-8")
    targets = collect_ui_targets(path)
    ids = {t.id for t in targets}
    assert ids == {"uptime-kuma", "offline-app"}
    assert "no-ui" not in ids


def test_check_and_report(tmp_path: Path) -> None:
    path = tmp_path / "app-dashboard.yaml"
    path.write_text(FIXTURE_DASHBOARD, encoding="utf-8")

    def fake_probe(url: str, **_kwargs):  # noqa: ANN003
        if "uptime-kuma" in url:
            return ProbeResult(True, 302, None, url)
        return ProbeResult(False, None, "URLError: timed out", None)

    results = run_inventory_check(path, probe=fake_probe)
    assert len(results) == 2
    by_id = {r.target.id: r for r in results}
    assert by_id["uptime-kuma"].reachable is True
    assert by_id["offline-app"].reachable is False

    text = format_reachability_report(results)
    assert "Reachable: 1" in text
    assert "Unreachable: 1" in text
    assert "Uptime Kuma" in text
    assert "Offline App" in text


def test_auth_statuses_count_reachable() -> None:
    targets = [
        Target(id="a", name="A", url="https://a.example", category="other"),
        Target(id="b", name="B", url="https://b.example", category="other"),
    ]

    def fake_probe(url: str, **_kwargs):  # noqa: ANN003
        if url.endswith("a.example"):
            return ProbeResult(True, 401, None, url)
        return ProbeResult(True, 403, None, url)

    results = check_targets(targets, probe=fake_probe)
    assert all(r.reachable for r in results)


def test_services_yaml_loader(tmp_path: Path) -> None:
    data = {
        "version": 1,
        "services": {
            "uptime-kuma": {
                "name": "Uptime Kuma",
                "dashboard": {"enabled": True, "category": "Monitoring"},
                "network": {"private_url": "https://uptime-kuma.example.ts.net"},
            },
            "hidden": {
                "name": "Hidden",
                "dashboard": {"enabled": False},
                "network": {"private_url": "https://hidden.example.ts.net"},
            },
        },
    }
    path = tmp_path / "services.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    targets = collect_ui_targets(path)
    assert len(targets) == 1
    assert targets[0].id == "uptime-kuma"
