#!/usr/bin/env python3
"""End-to-end inventory builder tests (flat apps: template)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
BUILD = SCRIPTS / "build_inventory.py"
VALIDATE = SCRIPTS / "validate_inventory.py"
sys.path.insert(0, str(SCRIPTS))

from validate_inventory import validate  # noqa: E402


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def test_full_build(tmp_path: Path) -> None:
    out = tmp_path / "app-dashboard.yaml"
    cp = run(
        [
            sys.executable,
            str(BUILD),
            "--coolify-input",
            str(ROOT / "tests" / "fixtures" / "coolify_resources.json"),
            "--tailscale-input",
            str(ROOT / "tests" / "fixtures" / "tailscale_resources.json"),
            "--defaults",
            str(ROOT / "config" / "defaults.yaml"),
            "--apps",
            str(ROOT / "config" / "apps.yaml"),
            "--output",
            str(out),
        ]
    )
    assert cp.returncode == 0, cp.stderr
    assert out.exists()

    import yaml

    data = yaml.safe_load(out.read_text())
    assert validate(data) == [], validate(data)
    assert "apps" in data
    assert "categories" not in data

    apps = data["apps"]
    names = {a["name"] for a in apps.values()}
    assert "Uptime Kuma" in names
    assert "PostgreSQL" not in names
    assert "dom-laptop" not in names
    assert all("uptime-kuma-tailscale" not in n for n in names)

    uk = apps.get("uptime-kuma") or next(
        a for a in apps.values() if a["name"] == "Uptime Kuma"
    )
    assert uk["dns_name"] == "uptime-kuma.tiger-bushmaster.ts.net"
    assert uk["online"] is True
    assert uk["coolify_id"] == "1"
    assert "dashboard" in uk["tags"]
    assert isinstance(uk["tailscale-tags"], list)
    assert isinstance(uk["labels"], dict)

    # Unmatched app still present with null Tailscale fields
    cs = next(a for a in apps.values() if a["name"] == "code-server")
    assert cs["hostname"] is None
    assert cs["dns_name"] is None
    assert cs["online"] is None

    blob = out.read_text()
    assert "dom-laptop" not in blob
    assert run([sys.executable, str(VALIDATE), str(out)]).returncode == 0


def test_example_validates() -> None:
    example = ROOT / "examples" / "inventory.example.yaml"
    assert run([sys.executable, str(VALIDATE), str(example)]).returncode == 0


def test_deterministic_ordering(tmp_path: Path) -> None:
    outs = []
    for i in range(2):
        out = tmp_path / f"inv-{i}.yaml"
        run(
            [
                sys.executable,
                str(BUILD),
                "--coolify-input",
                str(ROOT / "tests" / "fixtures" / "coolify_resources.json"),
                "--tailscale-input",
                str(ROOT / "tests" / "fixtures" / "tailscale_resources.json"),
                "--defaults",
                str(ROOT / "config" / "defaults.yaml"),
                "--apps",
                str(ROOT / "config" / "apps.yaml"),
                "--output",
                str(out),
            ]
        )
        import yaml

        data = yaml.safe_load(out.read_text())
        data["generated"]["at"] = "FIXED"
        outs.append(json.dumps(data, sort_keys=True))
    assert outs[0] == outs[1]


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            if "tmp_path" in fn.__code__.co_varnames:
                with tempfile.TemporaryDirectory() as td:
                    fn(Path(td))
            else:
                fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {name}: {exc}")
    raise SystemExit(failures)
