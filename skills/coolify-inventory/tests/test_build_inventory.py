#!/usr/bin/env python3
"""Fixture tests for coolify-inventory builders."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_inventory.py"
VALIDATE = ROOT / "scripts" / "validate_inventory.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def test_empty_projects(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"projects": []}), encoding="utf-8")
    out = tmp_path / "out"
    cp = run(
        [
            sys.executable,
            str(BUILD),
            "--input",
            str(raw),
            "--output-dir",
            str(out),
            "--format",
            "both",
            "--no-history",
        ]
    )
    assert cp.returncode == 0, cp.stderr
    data = json.loads((out / "inventory.json").read_text())
    assert data["projects"] == {}
    assert run([sys.executable, str(VALIDATE), str(out / "inventory.json")]).returncode == 0


def test_full_fixture(tmp_path: Path) -> None:
    raw = ROOT / "examples" / "raw.fixture.json"
    out = tmp_path / "out"
    cp = run(
        [
            sys.executable,
            str(BUILD),
            "--input",
            str(raw),
            "--output-dir",
            str(out),
            "--format",
            "both",
            "--no-history",
        ]
    )
    assert cp.returncode == 0, cp.stderr
    data = json.loads((out / "inventory.json").read_text())
    assert "demo-project" in data["projects"]
    env = data["projects"]["demo-project"]["environments"]["production"]
    assert "wordpress" in env["applications"]
    assert "redis" in env["services"]
    assert "postgresql" in env["databases"]
    assert run([sys.executable, str(VALIDATE), str(out / "inventory.yaml")]).returncode == 0
    assert run([sys.executable, str(VALIDATE), str(out / "inventory.json")]).returncode == 0


def test_malformed_missing_projects(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    raw.write_text("{}", encoding="utf-8")
    cp = run(
        [
            sys.executable,
            str(BUILD),
            "--input",
            str(raw),
            "--output-dir",
            str(tmp_path / "out"),
            "--format",
            "json",
            "--no-history",
        ]
    )
    assert cp.returncode != 0


def test_duplicate_ids_fail_validation(tmp_path: Path) -> None:
    bad = {
        "version": 1,
        "generated_at": "t",
        "source": {"type": "coolify", "mcp_server": "coolify-readonly"},
        "projects": {
            "a": {
                "id": "same",
                "name": "A",
                "environments": {
                    "e": {"id": "same", "name": "e"}
                },
            }
        },
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    assert run([sys.executable, str(VALIDATE), str(path)]).returncode != 0


def test_atomic_and_history(tmp_path: Path) -> None:
    raw = ROOT / "examples" / "raw.fixture.json"
    out = tmp_path / "out"
    out.mkdir()
    first = out / "inventory.json"
    first.write_text('{"version":1}\n', encoding="utf-8")
    cp = run(
        [
            sys.executable,
            str(BUILD),
            "--input",
            str(raw),
            "--output-dir",
            str(out),
            "--format",
            "json",
            "--history-dir",
            str(out / "history"),
            "--retain",
            "20",
        ]
    )
    assert cp.returncode == 0, cp.stderr
    assert first.exists()
    assert list((out / "history").glob("inventory-*.json"))


def test_stable_sorting(tmp_path: Path) -> None:
    raw = {
        "projects": [
            {
                "id": "p2",
                "name": "Zed",
                "environments": [
                    {
                        "id": "e1",
                        "name": "b-env",
                        "applications": [
                            {"id": "a2", "name": "Bravo"},
                            {"id": "a1", "name": "Alpha"},
                        ],
                        "services": [],
                        "databases": [],
                    },
                    {
                        "id": "e0",
                        "name": "a-env",
                        "applications": [],
                        "services": [],
                        "databases": [],
                    },
                ],
            },
            {"id": "p1", "name": "Alpha", "environments": []},
        ]
    }
    path = tmp_path / "raw.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    out = tmp_path / "out"
    run(
        [
            sys.executable,
            str(BUILD),
            "--input",
            str(path),
            "--output-dir",
            str(out),
            "--format",
            "json",
            "--no-history",
        ]
    )
    data = json.loads((out / "inventory.json").read_text())
    assert list(data["projects"]) == ["alpha", "zed"]
    assert list(data["projects"]["zed"]["environments"]) == ["a-env", "b-env"]
    apps = data["projects"]["zed"]["environments"]["b-env"]["applications"]
    assert list(apps) == ["alpha", "bravo"]


if __name__ == "__main__":
    import tempfile

    failures = 0
    for name, fn in list(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        with tempfile.TemporaryDirectory() as td:
            try:
                fn(Path(td))
                print(f"PASS {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {exc}")
    raise SystemExit(failures)
