---
name: tailscale-inventory
description: Deprecated alias. Use inventory_tailnet_nodes for a flat Tailscale nodes YAML under /knowledge/inventory/tailscale/nodes.yaml.
metadata:
  openclaw:
    requires:
      env:
        - TAILSCALE_API_KEY
---

# Tailscale inventory (deprecated)

**Deprecated.** Use **`inventory_tailnet_nodes`** instead:

- `/inventory_tailnet_nodes` — flat nodes → `/knowledge/inventory/tailscale/nodes.yaml`

Follow [`../inventory_tailnet_nodes/SKILL.md`](../inventory_tailnet_nodes/SKILL.md). Keep using MCP server **`tailscale-readonly`** only.
