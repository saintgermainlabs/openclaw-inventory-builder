"""Human-readable reachability reports."""

from __future__ import annotations

from .check_urls import CheckResult


def format_reachability_report(results: list[CheckResult]) -> str:
    reachable = [r for r in results if r.reachable]
    unreachable = [r for r in results if not r.reachable]

    lines: list[str] = [
        "Tailnet UI URL check",
        "",
        f"Checked: {len(results)}",
        f"Reachable: {len(reachable)}",
        f"Unreachable: {len(unreachable)}",
        "",
    ]

    if reachable:
        lines.append("Reachable:")
        for r in reachable:
            code = r.probe.status_code
            code_s = f" HTTP {code}" if code is not None else ""
            cat = f" [{r.target.category}]" if r.target.category else ""
            lines.append(f"- {r.target.name}{cat}: {r.target.url}{code_s}")
        lines.append("")

    if unreachable:
        lines.append("Unreachable:")
        for r in unreachable:
            detail = r.probe.error or (
                f"HTTP {r.probe.status_code}" if r.probe.status_code else "no response"
            )
            cat = f" [{r.target.category}]" if r.target.category else ""
            lines.append(f"- {r.target.name}{cat}: {r.target.url} ({detail})")
        lines.append("")

    if not results:
        lines.append("No UI-enabled URLs found in inventory.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
