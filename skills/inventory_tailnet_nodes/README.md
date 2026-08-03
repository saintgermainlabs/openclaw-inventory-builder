# inventory_tailnet_nodes

Flat Tailscale **nodes** list → `/knowledge/inventory/tailscale/nodes.yaml`.

MCP: `tailscale-readonly` → `list_devices` (primary).

```bash
rsync -az --delete skills/inventory_tailnet_nodes/ ubuntu:/srv/openclaw/skills/inventory_tailnet_nodes/
ssh ubuntu '/srv/openclaw/deploy-skill.sh inventory_tailnet_nodes'
```

## Next

`inventory_tailnet_insert_ids` (not built yet) will walk `nodes.yaml` and fill basic identifying fields per id.