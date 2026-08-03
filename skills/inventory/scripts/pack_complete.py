#!/usr/bin/env python3
"""Package complete MCP dumps + normalized latest.json into complete.json.

Does not make network calls. Does not invent data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def collect_mcp(mcp_dir: Path) -> dict[str, Any]:
    if not mcp_dir.is_dir():
        die(f"mcp dir not found: {mcp_dir}")
    captures: dict[str, Any] = {}
    for path in sorted(mcp_dir.glob("*.json")):
        captures[path.stem] = load_json(path)
    return captures


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", choices=("coolify", "tailscale"), required=True)
    p.add_argument("--mcp-dir", type=Path, required=True)
    p.add_argument("--normalized", type=Path, required=True, help="raw/latest.json")
    p.add_argument("--output", type=Path, required=True, help="raw/complete.json")
    args = p.parse_args()

    if not args.normalized.is_file():
        die(f"normalized input missing: {args.normalized}")

    mcp_server = (
        "coolify-readonly" if args.source == "coolify" else "tailscale-readonly"
    )
    payload = {
        "version": 1,
        "source": {"type": args.source, "mcp_server": mcp_server},
        "generated_at": utc_now(),
        "mcp_captures": collect_mcp(args.mcp_dir),
        "normalized": load_json(args.normalized),
    }
    atomic_write_text(
        args.output,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )
    print(f"Wrote {args.output} ({len(payload['mcp_captures'])} mcp captures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
