"""Deep diagnosis of a single Tailnet UI hostname/URL."""

from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .http_check import ProbeResult, probe_url


@dataclass
class Finding:
    severity: str  # ok | warn | error | info
    code: str
    message: str
    evidence: str | None = None
    remediation: str | None = None


@dataclass
class ServiceDiagnosis:
    input: str
    hostname: str | None
    url: str | None
    findings: list[Finding] = field(default_factory=list)
    probe: ProbeResult | None = None
    docker: dict[str, Any] = field(default_factory=dict)
    tailscale: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)


def _run(cmd: list[str], timeout: float = 15.0) -> tuple[int, str, str]:
    try:
        cp = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return cp.returncode, cp.stdout or "", cp.stderr or ""
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def normalize_target(raw: str) -> tuple[str, str]:
    """Return (url, hostname)."""
    s = raw.strip()
    if "://" not in s:
        s = f"https://{s}"
    parsed = urlparse(s)
    host = parsed.hostname or ""
    url = f"{parsed.scheme}://{host}{parsed.path or '/'}"
    if parsed.path in ("", "/"):
        url = f"{parsed.scheme}://{host}/"
    return url, host


def check_dns(hostname: str) -> Finding:
    try:
        infos = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        addrs = sorted({i[4][0] for i in infos})
        return Finding(
            "ok",
            "dns_ok",
            f"DNS resolved {hostname}",
            evidence=", ".join(addrs),
        )
    except socket.gaierror as exc:
        return Finding(
            "error",
            "dns_fail",
            f"DNS failed for {hostname}",
            evidence=str(exc),
            remediation=(
                "MagicDNS name missing usually means the Tailscale sidecar is "
                "Logged out / NeedsLogin, wrong TS_HOSTNAME, or the node was never "
                "created. Refresh TS_AUTHKEY in Coolify and recreate the sidecar; "
                "confirm HTTPS certs + MagicDNS are enabled on the tailnet."
            ),
        )


def check_http(url: str, *, timeout: float = 5.0) -> tuple[ProbeResult, Finding]:
    probe = probe_url(url, timeout=timeout)
    if probe.reachable:
        return probe, Finding(
            "ok",
            "http_ok",
            f"HTTP reachable ({probe.status_code})",
            evidence=url,
        )
    return probe, Finding(
        "error",
        "http_fail",
        "HTTP unreachable",
        evidence=probe.error or f"status={probe.status_code}",
        remediation=(
            "If DNS works but HTTP fails: check Tailscale Serve proxies to the "
            "app port (not missing Serve config), app container is running, and "
            "something listens on 127.0.0.1:<port> inside the sidecar netns."
        ),
    )


def docker_available() -> bool:
    return shutil.which("docker") is not None


def find_containers_for_hostname(hostname: str) -> dict[str, Any]:
    """Best-effort match Coolify/Tailscale containers for a short hostname."""
    short = hostname.split(".")[0]
    info: dict[str, Any] = {"short_name": short, "containers": []}
    if not docker_available():
        info["error"] = "docker CLI not available in this environment"
        return info
    code, out, err = _run(
        [
            "docker",
            "ps",
            "-a",
            "--format",
            "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}",
        ]
    )
    if code != 0:
        info["error"] = err.strip() or "docker ps failed"
        return info
    matched = []
    for line in out.splitlines():
        if short.lower() in line.lower():
            parts = line.split("\t")
            matched.append(
                {
                    "id": parts[0] if parts else "",
                    "name": parts[1] if len(parts) > 1 else line,
                    "status": parts[2] if len(parts) > 2 else "",
                    "image": parts[3] if len(parts) > 3 else "",
                }
            )
    info["containers"] = matched
    if not matched:
        # also search compose project labels loosely via docker ps names containing resource
        info["note"] = "No container names matched hostname short name"
    return info


def inspect_tailscale_sidecar(container_name: str) -> dict[str, Any]:
    """Run status/serve checks inside a suspected Tailscale sidecar container."""
    result: dict[str, Any] = {"container": container_name}
    if not docker_available():
        result["error"] = "docker not available"
        return result

    def dexec(*args: str) -> tuple[int, str, str]:
        return _run(["docker", "exec", container_name, *args])

    # Prefer explicit socket used by official image
    for sock_args in (
        ["tailscale", "--socket=/tmp/tailscaled.sock", "status", "--json"],
        ["tailscale", "status", "--json"],
    ):
        code, out, err = dexec(*sock_args)
        if code == 0 and out.strip():
            try:
                result["status"] = json.loads(out)
            except json.JSONDecodeError:
                result["status_raw"] = out[:2000]
            break
        result["status_error"] = err.strip() or out.strip()

    for sock_args in (
        ["tailscale", "--socket=/tmp/tailscaled.sock", "serve", "status"],
        ["tailscale", "serve", "status"],
    ):
        code, out, err = dexec(*sock_args)
        text = (out or err).strip()
        if text:
            result["serve_status"] = text
            break

    # Common app ports for quick listen check
    listening: list[str] = []
    for port in (80, 3000, 3001, 3456, 4180, 8080, 9000):
        code, out, err = dexec(
            "sh",
            "-c",
            f"wget -q -O /dev/null --timeout=1 http://127.0.0.1:{port}/ && echo OK || true",
        )
        if "OK" in (out + err):
            listening.append(str(port))
    result["localhost_http_ports"] = listening
    return result


def findings_from_tailscale(ts: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    status = ts.get("status") or {}
    backend = status.get("BackendState")
    if backend and backend != "Running":
        findings.append(
            Finding(
                "error",
                "tailscale_not_running",
                f"Tailscale BackendState={backend}",
                evidence=json.dumps(
                    {
                        "AuthURL": status.get("AuthURL"),
                        "DNSName": (status.get("Self") or {}).get("DNSName"),
                    }
                ),
                remediation=(
                    "Sidecar is not logged in. Refresh a reusable tagged TS_AUTHKEY "
                    "in Coolify, ensure TS_AUTH_ONCE=true and state volume persists, "
                    "then recreate the Tailscale container."
                ),
            )
        )
    serve = (ts.get("serve_status") or "").strip()
    if serve.lower() in {"", "no serve config"} or "no serve" in serve.lower():
        findings.append(
            Finding(
                "error",
                "serve_missing",
                "Tailscale Serve has no config",
                evidence=serve or "empty",
                remediation=(
                    "Add TS_SERVE_CONFIG pointing at a serve.json that HTTPS-proxies "
                    "to http://127.0.0.1:<app-port> (see tailscale-sidecars-coolify pattern). "
                    "Without Serve, https://<host>.ts.net will not work even if the node is online."
                ),
            )
        )
    elif serve:
        findings.append(
            Finding("ok", "serve_present", "Tailscale Serve config present", evidence=serve[:500])
        )
    ports = ts.get("localhost_http_ports") or []
    if not ports:
        findings.append(
            Finding(
                "warn",
                "app_not_listening",
                "No common app ports answered on 127.0.0.1 inside sidecar netns",
                remediation=(
                    "Confirm the application container is running with "
                    "network_mode: service:<tailscale>, check logs for crash loops "
                    "(permissions, DB DNS, missing env), and verify the Serve proxy port."
                ),
            )
        )
    else:
        findings.append(
            Finding(
                "ok",
                "app_listening",
                f"Localhost HTTP responded on port(s): {', '.join(ports)}",
            )
        )
    return findings


def findings_from_docker(docker: dict[str, Any], short: str) -> list[Finding]:
    findings: list[Finding] = []
    containers = docker.get("containers") or []
    if docker.get("error"):
        findings.append(
            Finding("warn", "docker_unavailable", docker["error"], remediation="Run diagnostics on the Docker host.")
        )
        return findings
    if not containers:
        findings.append(
            Finding(
                "warn",
                "no_matching_containers",
                f"No docker containers matched name '{short}'",
                remediation="Confirm Coolify resource is deployed and containers exist.",
            )
        )
        return findings
    running = [c for c in containers if str(c.get("status", "")).lower().startswith("up")]
    restarting = [c for c in containers if "restarting" in str(c.get("status", "")).lower()]
    findings.append(
        Finding(
            "info",
            "containers_found",
            f"Matched {len(containers)} container(s); {len(running)} up",
            evidence="; ".join(f"{c['name']} ({c['status']})" for c in containers),
        )
    )
    if restarting:
        findings.append(
            Finding(
                "error",
                "container_restarting",
                "One or more matched containers are restarting",
                evidence="; ".join(c["name"] for c in restarting),
                remediation="Inspect docker logs for the app (permissions, DB, config).",
            )
        )
    appish = [
        c
        for c in containers
        if not re.search(r"tailscale|postgres|redis|db", c.get("name", ""), re.I)
    ]
    if appish and not any(str(c.get("status", "")).lower().startswith("up") for c in appish):
        findings.append(
            Finding(
                "error",
                "app_container_down",
                "Application container is not Up",
                evidence="; ".join(f"{c['name']}:{c['status']}" for c in appish),
                remediation="Start/fix the app container; Tailscale alone is not enough.",
            )
        )
    return findings


def diagnose_service(
    target: str,
    *,
    timeout: float = 5.0,
    skip_docker: bool = False,
) -> ServiceDiagnosis:
    url, hostname = normalize_target(target)
    diag = ServiceDiagnosis(input=target, hostname=hostname, url=url)

    if not hostname:
        diag.findings.append(
            Finding("error", "bad_input", "Could not parse hostname from input")
        )
        return diag

    dns_finding = check_dns(hostname)
    diag.findings.append(dns_finding)

    if dns_finding.severity == "ok":
        probe, http_finding = check_http(url, timeout=timeout)
        diag.probe = probe
        diag.findings.append(http_finding)

    if not skip_docker and docker_available():
        docker = find_containers_for_hostname(hostname)
        diag.docker = docker
        diag.findings.extend(findings_from_docker(docker, hostname.split(".")[0]))

        # Prefer a container that looks like the Tailscale sidecar
        sidecar = None
        for c in docker.get("containers") or []:
            name = c.get("name") or ""
            if "tailscale" in name.lower():
                sidecar = name
                break
        if sidecar and str((next((c for c in docker["containers"] if c["name"] == sidecar), {})).get("status", "")).lower().startswith("up"):
            ts = inspect_tailscale_sidecar(sidecar)
            diag.tailscale = ts
            diag.findings.extend(findings_from_tailscale(ts))
        elif sidecar:
            diag.findings.append(
                Finding(
                    "error",
                    "sidecar_down",
                    f"Tailscale sidecar exists but is not Up: {sidecar}",
                    remediation="Restart the sidecar; check TS_AUTHKEY / TUN device permissions.",
                )
            )

    return diag


def format_diagnosis(diag: ServiceDiagnosis) -> str:
    lines = [
        f"Diagnosis for: {diag.input}",
        f"URL: {diag.url}",
        f"Hostname: {diag.hostname}",
        "",
        "Findings:",
    ]
    for f in diag.findings:
        mark = {
            "ok": "OK",
            "warn": "WARN",
            "error": "ERROR",
            "info": "INFO",
        }.get(f.severity, f.severity.upper())
        lines.append(f"- [{mark}] {f.code}: {f.message}")
        if f.evidence:
            lines.append(f"    evidence: {f.evidence}")
        if f.remediation:
            lines.append(f"    fix: {f.remediation}")
    lines.append("")
    lines.append("Overall: " + ("OK" if diag.ok else "FAILED"))
    lines.append("")
    return "\n".join(lines)


def diagnosis_to_dict(diag: ServiceDiagnosis) -> dict[str, Any]:
    return {
        "input": diag.input,
        "url": diag.url,
        "hostname": diag.hostname,
        "ok": diag.ok,
        "probe": asdict(diag.probe) if diag.probe else None,
        "findings": [asdict(f) for f in diag.findings],
        "docker": diag.docker,
        "tailscale": {
            k: v
            for k, v in diag.tailscale.items()
            if k != "status"  # may be large; include summary fields only
        }
        | (
            {
                "BackendState": (diag.tailscale.get("status") or {}).get("BackendState"),
                "AuthURL": (diag.tailscale.get("status") or {}).get("AuthURL"),
                "DNSName": ((diag.tailscale.get("status") or {}).get("Self") or {}).get(
                    "DNSName"
                ),
            }
            if diag.tailscale.get("status")
            else {}
        ),
    }
