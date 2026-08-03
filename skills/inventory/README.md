# inventory

Merged **complete** Coolify + Tailscale inventory skill for OpenClaw.

Discovery dumps everything available from read-only MCP into `/knowledge/inventory/`. Filtering (app dashboard, correlation, etc.) is **out of scope** — use later extract scripts.

## Commands

| Trigger | Behavior |
|---------|----------|
| `/inventory` | Coolify + Tailscale complete dumps |
| `/inventory coolify` | Coolify only |
| `/inventory tailscale` | Tailscale only |
| `/inventory summary` | Summarize after generate |

## Outputs

```text
/knowledge/inventory/coolify/raw/mcp/*.json
/knowledge/inventory/coolify/raw/latest.json
/knowledge/inventory/coolify/raw/complete.json
/knowledge/inventory/coolify/inventory.yaml|json

/knowledge/inventory/tailscale/raw/mcp/*.json
/knowledge/inventory/tailscale/raw/latest.json
/knowledge/inventory/tailscale/raw/complete.json
/knowledge/inventory/tailscale/inventory.yaml|json
```

## Local script tests

```bash
cd skills/inventory
python3 tests/test_build_coolify_inventory.py
python3 tests/test_build_tailscale_inventory.py
```

## Deploy

```bash
rsync -az --delete skills/inventory/ ubuntu:/srv/openclaw/skills/inventory/
ssh ubuntu '/srv/openclaw/deploy-skill.sh inventory'
```

## Deprecated

- `coolify-inventory` → use `/inventory coolify`
- `tailscale-inventory` → use `/inventory tailscale`
