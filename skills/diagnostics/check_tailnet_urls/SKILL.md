---
name: check-tailnet-urls
description: Check reachability of Tailnet UI URLs from app-dashboard inventory and report which are reachable vs unreachable.
metadata:
  openclaw:
    emoji: "🩺"
---

# Check Tailnet UI URLs

**Read-only diagnostics.** Load UI-enabled applications from the app dashboard inventory, probe each `ui.url` over HTTPS, and report reachability.

Does **not** call Coolify/Tailscale MCP write tools. Does **not** modify infrastructure.

## When to use

- `/check-tailnet-urls`
- Natural language: “Check Tailnet URLs”, “Which dashboard apps are down?”, “Probe app-dashboard URLs”

## When not to use

- Refreshing inventories → `app-dashboard-inventory` / `coolify-inventory` / `tailscale-inventory`
- Fixing broken auth/SSO → ops/runbooks (e.g. SilverBullet Authentik)
- Mutating Coolify or Tailscale

## Prerequisites

- Inventory file present (default): `/data/apps/inventory/app-dashboard.yaml`
  - Refresh first with **app-dashboard-inventory** if missing or stale
- Host/runtime must be able to reach MagicDNS names (on the Tailnet)

## Paths

```text
Skill source (dev):  /data/apps/openclaw/skills/diagnostics/check_tailnet_urls/
Skill runtime:       /data/workspace/skills/diagnostics/check_tailnet_urls/
Package module:      diagnostics (src/diagnostics in openclaw_coolify_tailnet_inventory)
Inventory default:   /data/apps/inventory/app-dashboard.yaml
```

## Workflow

1. Ensure inventory exists (offer to refresh `app-dashboard-inventory` if missing).
2. Run the checker from this skill directory (or installed package):

```bash
python3 scripts/check_tailnet_urls.py
# or with options:
python3 scripts/check_tailnet_urls.py \
  --inventory /data/apps/inventory/app-dashboard.yaml \
  --timeout 5
```

3. Report the text summary to the user. Include both reachable and unreachable lists.
4. Do not invent URLs. Only probe `ui.enabled: true` entries with a non-null `ui.url`.

## Reachability rules

Treat as **reachable** when the TCP/TLS handshake succeeds and the HTTP status is:

- `2xx` or `3xx` (including oauth2-proxy → Authentik redirects)
- `401` or `403` (auth wall = service answered)

Treat as **unreachable** on connection errors, timeouts, DNS failures, or other hard failures.

## Example reply

```text
Tailnet UI URL check

Checked: 4
Reachable: 3
Unreachable: 1

Reachable:
- Uptime Kuma [monitoring]: https://uptime-kuma.tiger-bushmaster.ts.net HTTP 302
- Open WebUI [ai]: https://open-webui.tiger-bushmaster.ts.net HTTP 200

Unreachable:
- code-server [development]: https://code-server.tiger-bushmaster.ts.net (TimeoutError: ...)
```

## Related

- Module: `diagnostics.check_urls` / `python -m diagnostics.cli`
- Inventory: `app-dashboard-inventory`
- Deploy: copy this skill under `/data/apps/openclaw/skills/diagnostics/check_tailnet_urls/` then `deploy-skill.sh` if your helper supports nested paths — otherwise `docker cp` the `diagnostics` tree into `/data/workspace/skills/diagnostics/`
