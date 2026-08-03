"""Tests for service diagnosis helpers."""

from __future__ import annotations

from diagnostics.service_diagnose import (
    Finding,
    check_dns,
    format_diagnosis,
    normalize_target,
)


def test_normalize_target() -> None:
    url, host = normalize_target("vikunja.tiger-bushmaster.ts.net")
    assert host == "vikunja.tiger-bushmaster.ts.net"
    assert url.startswith("https://")


def test_format_diagnosis_includes_remediation() -> None:
    from diagnostics.service_diagnose import ServiceDiagnosis

    diag = ServiceDiagnosis(
        input="https://vikunja.example.ts.net",
        hostname="vikunja.example.ts.net",
        url="https://vikunja.example.ts.net/",
        findings=[
            Finding(
                "error",
                "dns_fail",
                "DNS failed",
                remediation="Refresh TS_AUTHKEY",
            )
        ],
    )
    text = format_diagnosis(diag)
    assert "ERROR" in text
    assert "Refresh TS_AUTHKEY" in text
    assert "FAILED" in text


def test_check_dns_localhost() -> None:
    f = check_dns("localhost")
    assert f.severity == "ok"
