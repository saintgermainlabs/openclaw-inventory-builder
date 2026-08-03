---
name: inventory_tailnet_nodes
description: Read-only Tailscale node inventory. Calls list_devices (and related read tools if needed), writes a flat YAML list under /knowledge/inventory/tailscale/nodes.yaml.
metadata:
  openclaw:
    requires:
      env:
        - TAILSCALE_API_KEY
---

# Inventory Tailnet nodes

**Read-only.** Build a **flat YAML list** of Tailscale devices/nodes.

Use MCP server **`tailscale-readonly`** only. Never call Tailscale HTTP APIs directly. Never mutate. Never print tokens/secrets.

## When to use

- `/inventory_tailnet_nodes`
- “List Tailscale nodes”, “Refresh tailnet inventory”

## When not to use

- Coolify apps → `inventory_coolify_apps`
- ACL / key / route changes → refuse

## MCP calls

Required:

1. `list_devices` (or the equivalent allowlisted device-list tool on `tailscale-readonly`)

Optional (only if needed for basic node fields, still read-only):

- `get_tailnet_info`

Do **not** dump every Tailscale tool. Keep this to a node list.

## Output

Path: `/knowledge/inventory/tailscale/nodes.yaml`

Flat list. Each item:

| Field | Notes |
|-------|--------|
| `id` | Device id if present, else `""` |
| `hostname` | Device hostname |
| `name` | Display / given name if present, else same as hostname or `""` |
| `magicdns` | MagicDNS name if present, else `""` |
| `addresses` | List of IP strings; `[]` if none |
| `online` | Boolean if known; omit if unknown |
| `tags` | List of strings; `[]` if none |

Example:

```yaml
generated_at: "2026-08-03T00:00:00Z"
source: tailscale-readonly
tools:
  - list_devices
nodes:
  - id: n123
    hostname: ubuntu-server
    name: ubuntu-server
    magicdns: ubuntu-server.tiger-bushmaster.ts.net
    addresses:
      - 100.x.y.z
    online: true
    tags:
      - tag:server
```

Also save raw MCP response (optional but preferred):

- `/knowledge/inventory/tailscale/raw/mcp/list_devices.json`

## Procedure

1. `mkdir -p /knowledge/inventory/tailscale/raw/mcp`
2. Call `list_devices` on `tailscale-readonly`.
3. Write raw JSON if possible.
4. Write `/knowledge/inventory/tailscale/nodes.yaml`. Never invent hostnames. Missing fields → `""` or `[]`.
5. Reply with counts only: `nodes: N, path: …`. No secrets.

## Safety

Read-only. Skip ACL, key, route, auth-key, or any mutate tools.

## Next skill (later)

`inventory_tailnet_insert_ids` will read this YAML and fill basic identifying details per id (one at a time).
