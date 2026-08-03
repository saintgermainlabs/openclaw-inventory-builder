# Host staging + skill deploy

**Development staging path** (current):

```text
/data/apps/openclaw/
├── skills/          # coolify-readonly, coolify-inventory, tailscale-inventory, …
├── scripts/         # optional shared helpers
├── docs/
├── config/
└── deploy-skill.sh  # promote a skill into OpenClaw runtime
```

## Sync from this repo

```bash
PROJ=/path/to/openclaw_coolify_tailnet_inventory
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/coolify-inventory/" \
  ubuntu:/data/apps/openclaw/skills/coolify-inventory/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/tailscale-inventory/" \
  ubuntu:/data/apps/openclaw/skills/tailscale-inventory/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/app-dashboard-inventory/" \
  ubuntu:/data/apps/openclaw/skills/app-dashboard-inventory/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/diagnostics/" \
  ubuntu:/data/apps/openclaw/skills/diagnostics/
# Optional: package src for non-vendored imports
rsync -az --no-owner --no-group --delete \
  "$PROJ/src/" \
  ubuntu:/data/apps/openclaw/src/
scp "$PROJ/deploy/deploy-skill.sh" ubuntu:/data/apps/openclaw/deploy-skill.sh
ssh ubuntu 'chmod +x /data/apps/openclaw/deploy-skill.sh'
```

## Deploy into OpenClaw runtime

On the host:

```bash
/data/apps/openclaw/deploy-skill.sh coolify-inventory
/data/apps/openclaw/deploy-skill.sh tailscale-inventory
/data/apps/openclaw/deploy-skill.sh app-dashboard-inventory
/data/apps/openclaw/deploy-skill.sh diagnostics/check_tailnet_urls
/data/apps/openclaw/deploy-skill.sh diagnostics/diagnose_tailnet_service
```

This copies:

```text
/data/apps/openclaw/skills/<skill>
  →  container:/data/workspace/skills/<skill>
```

via `docker cp` (no Compose changes, no `openclaw.json` edits).

## Inventory output

```text
/knowledge/inventory/coolify/
/knowledge/inventory/tailscale/
/data/apps/inventory/app-dashboard.yaml   # app-dashboard-inventory
```

Then ask OpenClaw: **Refresh the Coolify inventory.**, **Refresh the Tailscale inventory.**, **Refresh the app dashboard inventory.**, or **Check Tailnet URLs.**

Do **not** bind-mount `/data/apps/openclaw` over OpenClaw’s live config directory.
