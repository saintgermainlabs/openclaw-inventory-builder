---
name: app-dashboard-inventory
description: Build a flat apps: YAML catalogue of browser UI apps from Coolify (dashboard-tagged) enriched with Tailscale MagicDNS. Coolify is authoritative; Tailscale never seeds the app list.
metadata:
  openclaw:
    requires:
      env:
        - COOLIFY_MCP_TOKEN
        - TAILSCALE_API_KEY
---

# App dashboard inventory

**Read-only.** Coolify decides which applications exist. Tailscale only supplies private browser URLs.

**Note:** Prefer refreshing complete source dumps with the merged [`inventory`](../inventory/SKILL.md) skill (`/inventory`). This skill still may re-query MCP until extract scripts consume `/knowledge/inventory/*/raw/complete.json`.

## Hard rules

1. **Coolify is authoritative** for application membership.
2. Only Coolify resources tagged **`dashboard`** are candidates.
3. **Optional** `category:<name>` Coolify tag (kept in `tags[]`; not a separate hierarchy).
4. **Never** build the inventory by enumerating Tailscale devices (laptops, phones, desktops, servers stay out).
5. **Never** include Tailscale sidecars (`-tailscale` suffix or `app.component: tailscale-sidecar`).
6. Databases, Redis, workers, queues appear **only** if intentionally tagged `dashboard`.
7. **Never** invent hostnames/DNS. No Coolify public URLs, Tailscale IPs, or container ports as substitutes.
8. **Never** attach an ambiguous Tailscale match — warn and leave Tailscale fields null.
9. **Never** print or write tokens/secrets into the inventory.
10. Refuse all Coolify/Tailscale mutations.

## When to use

- `/app-dashboard-inventory`
- Natural language: “Refresh the app dashboard inventory”, “Generate app-dashboard.yaml”

## Paths

```text
Skill source (dev):     /data/apps/openclaw/skills/app-dashboard-inventory/
Skill runtime:          /data/workspace/skills/app-dashboard-inventory/

Output:
/data/apps/inventory/app-dashboard.yaml

Working intermediates (create as needed):
/data/apps/openclaw/skills/app-dashboard-inventory/raw/coolify.json
/data/apps/openclaw/skills/app-dashboard-inventory/raw/tailscale.json
```

## MCP servers (allowlisted tools only)

### `coolify-readonly`

Prefer read tools from the configured allowlist, for example:

- `list_applications`, `list_services`, `list_databases`
- `get_application`, `get_service`, `get_database`
- `get_infrastructure_overview`, `list_servers`, `get_domains`

**Tags:** Coolify may expose tags on detail payloads. If list endpoints omit tags, call `get_application` / `get_service` for candidates and extract `tags` (array of strings) and `labels` / Docker labels when present. Map into the normalized Coolify JSON below. **Do not invent tags.**

### `tailscale-readonly`

- `list_devices` (required)
- `get_tailnet_info` (optional metadata)

Device fields to capture when present: `id`, `hostname`, `name` (often MagicDNS FQDN), `dns_name`, `online`, `tags`.

## Workflow

1. `mkdir -p /data/apps/inventory` and skill `raw/` if missing.
2. Using **only** `coolify-readonly`, discover applications/services (and databases only if needed for completeness). Flatten into:

```json
{
  "resources": [
    {
      "id": "coolify-uuid",
      "name": "Uptime Kuma",
      "project": "infrastructure",
      "environment": "production",
      "resource_type": "application",
      "status": "running",
      "tags": ["dashboard", "category:monitoring"],
      "labels": {}
    }
  ]
}
```

   Write to `raw/coolify.json`. Include **all** discovered resources with real tags; Python filters to `dashboard`.
3. Using **only** `tailscale-readonly` `list_devices`, write:

```json
{
  "devices": [
    {
      "id": "…",
      "hostname": "uptime-kuma",
      "name": "uptime-kuma.tiger-bushmaster.ts.net",
      "dns_name": "uptime-kuma.tiger-bushmaster.ts.net",
      "online": true,
      "tags": []
    }
  ]
}
```

   Write to `raw/tailscale.json`. Do **not** filter devices in this file; the matcher ignores non-matching hosts.
4. Build + validate:

```bash
cd /data/workspace/skills/app-dashboard-inventory
python3 scripts/build_inventory.py \
  --coolify-input raw/coolify.json \
  --tailscale-input raw/tailscale.json \
  --output /data/apps/inventory/app-dashboard.yaml
python3 scripts/validate_inventory.py /data/apps/inventory/app-dashboard.yaml
```

5. Reply with a summary (counts, unmatched, ambiguous). No secrets.

```text
App dashboard inventory refreshed.

Applications: N
Matched Tailscale URLs: N
Unmatched: …
Ambiguous: …

Output: /data/apps/inventory/app-dashboard.yaml
No infrastructure modifications were performed.
```

## Canonical inventory shape

Output `/data/apps/inventory/app-dashboard.yaml` uses a flat `apps:` map. Each node:

```yaml
version: 1
generated:
  at: "…"
  sources:
    - coolify
    - tailscale

apps:
  portal:
    hostname: portal
    dns_name: portal.tiger-bushmaster.ts.net
    online: true
    tailscale-tags: ["tag:portal", "tag:ui"]
    coolify_id: p14yu0he1075q047r4dbk50a
    status: running
    tags: ["dashboard"]
    labels: {}
    name: server-portal:main-p14yu0he1075q047r4dbk50a
    project: Portal
    resource_type: application
```

- Map key is preferably the Tailscale hostname slug; otherwise a normalized Coolify name.
- Unmatched Tailscale fields (`hostname`, `dns_name`, `online`) are `null`; `tailscale-tags` is `[]`.
- Coolify remains authoritative for membership (`tags` must include `dashboard`).

## Matching (deterministic)

1. Explicit alias from `config/apps.yaml`
2. Exact normalized hostname == normalized Coolify name
3. Exact normalized service name (if present)
4. No match → null Tailscale fields (app still listed)

Ambiguous (multiple devices) → null Tailscale fields + warning.

## Config

- `config/defaults.yaml` — inclusion tag, exclusions, output path
- `config/apps.yaml` — optional aliases only (never invents apps)

## Related

- Deploy: `/data/apps/openclaw/deploy-skill.sh app-dashboard-inventory`
- Siblings: `coolify-inventory`, `tailscale-inventory`
- URL probes: `diagnostics/check_tailnet_urls` (uses `apps.*.dns_name`)
