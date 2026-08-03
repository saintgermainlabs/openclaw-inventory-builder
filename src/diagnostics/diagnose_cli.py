#!/usr/bin/env python3
"""CLI: diagnose a single Tailnet UI hostname/URL."""

from __future__ import annotations

import argparse
import json
import sys

from .service_diagnose import (
    diagnose_service,
    diagnosis_to_dict,
    format_diagnosis,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Diagnose why a Tailnet UI URL/hostname is unreachable."
    )
    p.add_argument("target", help="URL or hostname (e.g. https://vikunja.tiger-bushmaster.ts.net)")
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--skip-docker", action="store_true")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    diag = diagnose_service(
        args.target, timeout=args.timeout, skip_docker=args.skip_docker
    )
    if args.json:
        print(json.dumps(diagnosis_to_dict(diag), indent=2))
    else:
        print(format_diagnosis(diag), end="")
    return 0 if diag.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
