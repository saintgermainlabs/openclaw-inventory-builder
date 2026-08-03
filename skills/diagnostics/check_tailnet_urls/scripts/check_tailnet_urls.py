#!/usr/bin/env python3
"""Thin wrapper around diagnostics.cli for the check_tailnet_urls skill."""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
# skills/diagnostics/check_tailnet_urls/scripts -> repo root is parents[4]
_CANDIDATE_SRC = [
    _HERE.parents[4] / "src",  # repo checkout
    Path("/data/apps/openclaw/src"),  # optional host staging of package src
    _HERE.parents[1] / "vendor",  # skill-local vendor/ (diagnostics package root)
]
for src in _CANDIDATE_SRC:
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

from diagnostics.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
