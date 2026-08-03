"""Orchestrate UI URL reachability checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .http_check import ProbeFn, ProbeResult, probe_url
from .loaders import Target, collect_ui_targets


@dataclass(frozen=True)
class CheckResult:
    target: Target
    probe: ProbeResult

    @property
    def reachable(self) -> bool:
        return self.probe.reachable


def check_targets(
    targets: list[Target],
    *,
    timeout: float = 5.0,
    verify_tls: bool = True,
    probe: ProbeFn | None = None,
) -> list[CheckResult]:
    """Probe each target; return results in stable id order."""
    fn = probe or probe_url
    ordered = sorted(targets, key=lambda t: (t.category or "", t.name.lower(), t.id))
    results: list[CheckResult] = []
    for t in ordered:
        pr = fn(t.url, timeout=timeout, verify_tls=verify_tls)
        results.append(CheckResult(target=t, probe=pr))
    return results


def run_inventory_check(
    inventory_path: Path,
    *,
    timeout: float = 5.0,
    verify_tls: bool = True,
    format_hint: str | None = None,
    probe: ProbeFn | None = None,
) -> list[CheckResult]:
    targets = collect_ui_targets(inventory_path, format_hint=format_hint)
    return check_targets(
        targets, timeout=timeout, verify_tls=verify_tls, probe=probe
    )
