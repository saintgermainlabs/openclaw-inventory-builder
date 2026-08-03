# app-dashboard-inventory

Generates a reusable **browser UI** catalogue from Coolify (source of truth) + Tailscale (hostname / MagicDNS / online).

Output: `/data/apps/inventory/app-dashboard.yaml`

## Inventory node template

```yaml
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

## Purpose

- Includes only Coolify resources tagged `dashboard`
- Excludes Tailscale sidecars; never lists laptops/phones/servers as apps
- Enriches with Tailscale `hostname`, `dns_name`, `online`, `tailscale-tags` when uniquely matched

## Tagging (Coolify)

```text
dashboard
category:monitoring   # optional; kept in tags[]
```

Without `dashboard`, the resource is omitted.

## Generation (OpenClaw)

Ask: **Refresh the app dashboard inventory** or `/app-dashboard-inventory`.

```bash
python3 scripts/build_inventory.py \
  --coolify-input raw/coolify.json \
  --tailscale-input raw/tailscale.json \
  --output /data/apps/inventory/app-dashboard.yaml
```

## Validation

```bash
python3 scripts/validate_inventory.py /data/apps/inventory/app-dashboard.yaml
```

## Files

| Path | Role |
|------|------|
| `config/defaults.yaml` | Inclusion tag, exclusions, output path |
| `config/apps.yaml` | Optional aliases |
| `examples/inventory.example.yaml` | Template example |
| `/data/apps/inventory/app-dashboard.yaml` | Generated inventory |

## Local tests

```bash
cd skills/app-dashboard-inventory
python3 tests/test_filtering.py
python3 tests/test_matching.py
python3 tests/test_inventory.py
```

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Coolify app missing | Missing `dashboard` tag |
| `hostname` / `dns_name` null | No Tailscale match — alias or rename |
| Ambiguous warning | Multiple Tailscale devices match |
| Sidecar appeared | `-tailscale` suffix / `tailscale-sidecar` label |

## Safety

- No direct Coolify/Tailscale HTTP from Python
- No secrets in inventory output
- MCP risk: read-only allowlists only
