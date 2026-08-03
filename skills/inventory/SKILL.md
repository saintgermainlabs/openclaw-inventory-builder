---
name: inventory
description: Deprecated merged dump skill. Prefer inventory_coolify_apps and inventory_tailnet_nodes for flat YAML lists.
metadata:
  openclaw:
    requires:
      env:
        - COOLIFY_MCP_TOKEN
        - TAILSCALE_API_KEY
---

# Inventory (deprecated merged skill)

**Deprecated** for day-to-day use. Prefer the two simple flat-list skills:

| Skill | Output |
|-------|--------|
| [`inventory_coolify_apps`](../inventory_coolify_apps/SKILL.md) | `/knowledge/inventory/coolify/apps.yaml` |
| [`inventory_tailnet_nodes`](../inventory_tailnet_nodes/SKILL.md) | `/knowledge/inventory/tailscale/nodes.yaml` |

**Planned next:** `inventory_coolify_insert_ids` and `inventory_tailnet_insert_ids` — fill basic identifying details per id from those lists.

This directory still contains older complete-dump / lean-builder scripts for reference. Do not use them unless explicitly requested.
