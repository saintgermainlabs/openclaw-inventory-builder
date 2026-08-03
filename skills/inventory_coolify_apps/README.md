# inventory_coolify_apps

Flat Coolify **applications + services** list → `/knowledge/inventory/coolify/apps.yaml`.

MCP: `coolify-readonly` → `list_applications` + `list_services` only.

```bash
rsync -az --delete skills/inventory_coolify_apps/ ubuntu:/srv/openclaw/skills/inventory_coolify_apps/
ssh ubuntu '/srv/openclaw/deploy-skill.sh inventory_coolify_apps'
```

## Next

`inventory_coolify_insert_ids` (not built yet) will walk `apps.yaml` and fill basic identifying fields per id.