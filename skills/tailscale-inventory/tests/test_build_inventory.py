#!/usr/bin/env python3
"""Fixture tests for tailscale-inventory builders."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_inventory.py"
VALIDATE = ROOT / "scripts" / "validate_inventory.py"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def test_empty_devices(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"devices": []}), encoding="utf-8")
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
    assert data["devices"] == {}
    assert run([sys.executable, str(VALIDATE), str(out / "inventory.json")]).returncode == 0


def test_full_fixture(tmp_path: Path) -> None:
    out = tmp_path / "out"
    cp = run(
        [
            sys.executable,
            str(BUILD),
            "--input",
            str(ROOT / "examples" / "raw.fixture.json"),
            "--output-dir",
            str(out),
            "--format",
            "both",
            "--no-history",
        ]
    )
    assert cp.returncode == 0, cp.stderr
    data = json.loads((out / "inventory.json").read_text())
    assert "uptime-kuma" in data["devices"]
    assert data["devices"]["uptime-kuma"]["online"] is True
    assert data["tailnet"]["dns_suffix"] == "tiger-bushmaster.ts.net"
    assert run([sys.executable, str(VALIDATE), str(out / "inventory.yaml")]).returncode == 0


def test_malformed(tmp_path: Path) -> None:
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


def test_duplicate_ids(tmp_path: Path) -> None:
    bad = {
        "version": 1,
        "generated_at": "t",
        "source": {"type": "tailscale", "mcp_server": "tailscale-readonly"},
        "devices": {
            "a": {"id": "same", "hostname": "a"},
            "b": {"id": "same", "hostname": "b"},
        },
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    assert run([sys.executable, str(VALIDATE), str(path)]).returncode != 0


def test_stable_sorting(tmp_path: Path) -> None:
    raw = {
        "devices": [
            {"id": "2", "hostname": "zeta"},
            {"id": "1", "hostname": "alpha"},
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
    assert list(data["devices"]) == ["alpha", "zeta"]


if __name__ == "__main__":
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
