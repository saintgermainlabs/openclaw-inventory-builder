"""CLI: check_tailnet_urls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .check_urls import run_inventory_check
from .report import format_reachability_report

DEFAULT_INVENTORY = Path("/data/apps/inventory/app-dashboard.yaml")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Check reachability of UI URLs from app-dashboard (or services) inventory."
        )
    )
    p.add_argument(
        "--inventory",
        type=Path,
        default=DEFAULT_INVENTORY,
        help=f"Inventory YAML path (default: {DEFAULT_INVENTORY})",
    )
    p.add_argument(
        "--format",
        choices=("auto", "app-dashboard", "services"),
        default="auto",
        help="Inventory shape hint (default: auto-detect)",
    )
    p.add_argument("--timeout", type=float, default=5.0, help="Per-URL timeout seconds")
    p.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS certificate verification",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text report",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.inventory.exists():
        print(f"Inventory not found: {args.inventory}", file=sys.stderr)
        return 2
    hint = None if args.format == "auto" else args.format
    results = run_inventory_check(
        args.inventory,
        timeout=args.timeout,
        verify_tls=not args.insecure,
        format_hint=hint,
    )
    if args.json:
        payload = {
            "inventory": str(args.inventory),
            "checked": len(results),
            "reachable": sum(1 for r in results if r.reachable),
            "unreachable": sum(1 for r in results if not r.reachable),
            "results": [
                {
                    "id": r.target.id,
                    "name": r.target.name,
                    "category": r.target.category,
                    "url": r.target.url,
                    "reachable": r.reachable,
                    "status_code": r.probe.status_code,
                    "error": r.probe.error,
                }
                for r in results
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_reachability_report(results), end="")
    # Exit 1 if any unreachable (useful for automation); 0 if all ok or empty
    if any(not r.reachable for r in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
