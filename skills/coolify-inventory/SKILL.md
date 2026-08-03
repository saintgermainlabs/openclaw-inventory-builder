---
name: coolify-inventory
description: Deprecated alias. Use inventory_coolify_apps for a flat Coolify apps+services YAML under /knowledge/inventory/coolify/apps.yaml.
metadata:
  openclaw:
    requires:
      env:
        - COOLIFY_MCP_TOKEN
---

# Coolify inventory (deprecated)

**Deprecated.** Use **`inventory_coolify_apps`** instead:

- `/inventory_coolify_apps` — flat apps + services → `/knowledge/inventory/coolify/apps.yaml`

Follow [`../inventory_coolify_apps/SKILL.md`](../inventory_coolify_apps/SKILL.md). Keep using MCP server **`coolify-readonly`** only.
