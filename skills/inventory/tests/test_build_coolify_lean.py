#!/usr/bin/env python3
"""Offline tests for lean Coolify inventory builder + enricher."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_coolify_lean.py"
VALIDATE = ROOT / "scripts" / "validate_coolify_lean.py"
ENRICH = ROOT / "scripts" / "enrich_coolify_resource.py"
EXAMPLES = ROOT / "examples" / "coolify"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def test_build_from_fixtures() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "inventory.yaml"
        also = Path(td) / "inventory.json"
        cp = run(
            [
                sys.executable,
                str(BUILD),
                "--applications",
                str(EXAMPLES / "list_applications.fixture.json"),
                "--services",
                str(EXAMPLES / "list_services.fixture.json"),
                "--output",
                str(out),
                "--also-json",
                str(also),
            ]
        )
        assert cp.returncode == 0, cp.stderr + cp.stdout
        data = json.loads(also.read_text())
        assert data["version"] == 1
        assert data["source"]["tools"] == ["list_applications", "list_services"]
        assert len(data["apps"]) == 3
        assert len(data["services"]) == 2

        by_id = {a["id"]: a for a in data["apps"]}
        assert by_id["app-wp"]["project"] == "demo-project"
        assert by_id["app-wp"]["tags"] == ["dashboard"]
        assert by_id["app-api"]["id"] == "app-api"
        assert by_id["app-api"]["project"] == "backend"
        assert by_id["app-api"]["tags"] == ["api"]
        assert by_id["app-empty"]["project"] == ""
        assert by_id["app-empty"]["tags"] == []

        cpv = run([sys.executable, str(VALIDATE), str(also)])
        assert cpv.returncode == 0, cpv.stderr


def test_enrich_updates_one_app() -> None:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        inv_json = td_path / "inventory.json"
        inv_yaml = td_path / "inventory.yaml"
        cp = run(
            [
                sys.executable,
                str(BUILD),
                "--applications",
                str(EXAMPLES / "list_applications.fixture.json"),
                "--services",
                str(EXAMPLES / "list_services.fixture.json"),
                "--output",
                str(inv_yaml),
                "--also-json",
                str(inv_json),
            ]
        )
        assert cp.returncode == 0, cp.stderr

        detail = td_path / "detail.json"
        detail.write_text(
            json.dumps(
                {
                    "id": "app-empty",
                    "name": "Empty Fields",
                    "project": "filled-project",
                    "tags": ["enriched"],
                }
            ),
            encoding="utf-8",
        )
        cpe = run(
            [
                sys.executable,
                str(ENRICH),
                "--kind",
                "app",
                "--id",
                "app-empty",
                "--detail-json",
                str(detail),
                "--inventory",
                str(inv_json),
                "--also-json",
                str(inv_json),
            ]
        )
        assert cpe.returncode == 0, cpe.stderr + cpe.stdout
        data = json.loads(inv_json.read_text())
        row = next(a for a in data["apps"] if a["id"] == "app-empty")
        assert row["project"] == "filled-project"
        assert row["tags"] == ["enriched"]
        # other apps untouched
        assert next(a for a in data["apps"] if a["id"] == "app-wp")["name"] == "WordPress"


def test_validate_rejects_missing_apps() -> None:
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.json"
        bad.write_text(
            json.dumps(
                {
                    "version": 1,
                    "generated_at": "t",
                    "source": {
                        "type": "coolify",
                        "mcp_server": "coolify-readonly",
                        "tools": ["list_applications"],
                    },
                    "services": [],
                }
            ),
            encoding="utf-8",
        )
        cp = run([sys.executable, str(VALIDATE), str(bad)])
        assert cp.returncode != 0


def main() -> int:
    test_build_from_fixtures()
    test_enrich_updates_one_app()
    test_validate_rejects_missing_apps()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
