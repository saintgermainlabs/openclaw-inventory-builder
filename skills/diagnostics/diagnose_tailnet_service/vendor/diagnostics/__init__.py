"""Diagnostics helpers for Coolify/Tailscale inventory health checks.

Read-only: probes HTTP reachability and reports status. Does not mutate
infrastructure or call Coolify/Tailscale write APIs.
"""

from .check_urls import CheckResult, check_targets, run_inventory_check
from .loaders import Target, collect_ui_targets
from .report import format_reachability_report
from .service_diagnose import ServiceDiagnosis, diagnose_service, format_diagnosis

__all__ = [
    "CheckResult",
    "ServiceDiagnosis",
    "Target",
    "check_targets",
    "collect_ui_targets",
    "diagnose_service",
    "format_diagnosis",
    "format_reachability_report",
    "run_inventory_check",
]
