#!/usr/bin/env python3
"""Wrapper for diagnose-tailnet-service skill."""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_CANDIDATE_SRC = [
    _HERE.parents[4] / "src",
    Path("/data/apps/openclaw/src"),
    _HERE.parents[1] / "vendor",
]
for src in _CANDIDATE_SRC:
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

from diagnostics.diagnose_cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
