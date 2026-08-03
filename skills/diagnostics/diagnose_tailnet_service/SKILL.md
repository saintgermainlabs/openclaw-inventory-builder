---
name: diagnose-tailnet-service
description: Deep-diagnose a single Tailnet UI hostname (DNS, HTTP, Docker containers, Tailscale login/Serve, localhost ports) and report findings with remediations.
---

# Diagnose Tailnet service

**Read-only by default.** Investigate why a MagicDNS UI URL fails (e.g. `https://vikunja.tiger-bushmaster.ts.net`).

Use this when `check-tailnet-urls` marks a URL unreachable, or a user reports one broken hostname.

## When to use

- `/diagnose-tailnet-service <hostname-or-url>`
- “Why doesn’t https://vikunja.tiger-bushmaster.ts.net work?”
- After inventory URL checks fail for one app

## When not to use

- Bulk URL checks → `check-tailnet-urls`
- Coolify/Tailscale **mutations** (redeploy, rotate keys) unless the user explicitly asks you to apply a fix
- Inventing Serve ports or auth keys

## Workflow

1. Identify the target URL/hostname.
2. Prefer running on the **Docker/Tailscale host** (or OpenClaw host with docker.sock + Tailnet access):

```bash
python3 scripts/diagnose_tailnet_service.py https://vikunja.tiger-bushmaster.ts.net
python3 scripts/diagnose_tailnet_service.py vikunja.tiger-bushmaster.ts.net --json
```

3. Walk findings in order: DNS → HTTP → containers → Tailscale BackendState → Serve → localhost ports.
4. Report the summary verbatim; include remediations from findings.
5. Only apply fixes if the user asks (volume permissions, recreate sidecar, paste Serve compose, refresh `TS_AUTHKEY` in Coolify).

## Checklist encoded in the tool

| Check | Failure meaning |
|-------|-----------------|
| DNS | Sidecar Logged out / wrong hostname / never joined |
| HTTP | Serve missing, app down, wrong proxy port |
| Containers | App not deployed / restarting / name mismatch |
| Tailscale `BackendState` | NeedsLogin → refresh auth key + state volume |
| Serve status | “No serve config” → add `TS_SERVE_CONFIG` → app port |
| Localhost ports | App crash (perms/DB) or wrong port |

## Vikunja case study (2026-08-03)

`https://vikunja.tiger-bushmaster.ts.net` failed because **all** of:

1. **DNS fail** — Tailscale sidecar `BackendState=NeedsLogin` / Logged out (`Persist` empty).
2. **App container missing/restarting** — `vikunja` not Up; logs: `mkdir /app/vikunja/files: permission denied` (uid 1000).
3. **No Serve config** — compose had no `TS_SERVE_CONFIG` proxy to `http://127.0.0.1:3456`.
4. **Public Coolify URL still in env** — `VIKUNJA_SERVICE_PUBLICURL` pointed at sslip.io, not MagicDNS.

Remediation path: fix volume ownership → keep app healthy on `:3456` → refresh `TS_AUTHKEY` / recreate sidecar → add Serve JSON for `:3456` → set public URL to `https://vikunja.tiger-bushmaster.ts.net`.

## Safety

- Do not print `TS_AUTHKEY`, DB passwords, JWT secrets.
- Prefer read-only `docker logs` / `tailscale status` / HTTP probes.
- Mark destructive steps clearly if user requests repair.

## Related

- Module: `diagnostics.service_diagnose` / `python -m diagnostics.diagnose_cli`
- Sibling: `check-tailnet-urls`
- Pattern docs: `tailscale-sidecars-coolify` README
