---
name: inventory_coolify_apps
description: Read-only Coolify apps+services inventory. Calls list_applications and list_services, writes a flat YAML list under /knowledge/inventory/coolify/apps.yaml.
metadata:
  openclaw:
    requires:
      env:
        - COOLIFY_MCP_TOKEN
---

# Inventory Coolify apps (includes services)

**Read-only.** Build a **flat YAML list** of Coolify applications and services. Two MCP calls only.

Use MCP server **`coolify-readonly`** only. Never call Coolify HTTP APIs. Never mutate. Never print tokens/secrets.

## When to use

- `/inventory_coolify_apps`
- “List Coolify apps”, “Refresh Coolify apps inventory”

## When not to use

- Per-app detail / diagnose → later enrichment
- Tailscale nodes → `inventory_tailnet_nodes`
- Any Coolify write → refuse

## MCP calls (only these)

1. `list_applications`
2. `list_services`

## Output

Path: `/knowledge/inventory/coolify/apps.yaml`

Flat list. Applications and services in one list. Each item:

| Field | Notes |
|-------|--------|
| `id` | Resource id/uuid |
| `name` | Display name |
| `project` | Project name or id if present, else `""` |
| `tags` | List of strings; use `[]` if none |
| `kind` | `application` or `service` |

Example:

```yaml
generated_at: "2026-08-03T00:00:00Z"
source: coolify-readonly
tools:
  - list_applications
  - list_services
apps:
  - id: app-wp
    name: WordPress
    project: demo
    tags:
      - dashboard
    kind: application
  - id: svc-redis
    name: Redis
    project: demo
    tags: []
    kind: service
```

Also save raw MCP responses (optional but preferred):

- `/knowledge/inventory/coolify/raw/mcp/list_applications.json`
- `/knowledge/inventory/coolify/raw/mcp/list_services.json`

## Procedure

1. `mkdir -p /knowledge/inventory/coolify/raw/mcp`
2. Call `list_applications` and `list_services` on `coolify-readonly`.
3. Write raw JSON if possible.
4. Write `/knowledge/inventory/coolify/apps.yaml` as above. Never invent ids/names. Missing project → `""`. Missing tags → `[]`.
5. Reply with counts only: `applications: N, services: M, path: …`. No secrets.

## Safety

Follow `coolify-readonly`. Skip deploy/restart/delete/create/env/secret tools.

## Next skill (later)

`inventory_coolify_insert_ids` will read this YAML and fill basic identifying details per id (one at a time).
