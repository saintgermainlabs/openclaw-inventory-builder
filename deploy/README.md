# Host skills library + deploy

**Canonical skills library** (host):

```text
/srv/openclaw/
├── skills/            # coolify-readonly, coolify-inventory, tailscale-inventory, …
├── deploy-skill.sh    # optional: copy a skill into OpenClaw workspace
└── sandbox/           # unrelated sandbox tooling
```

OpenClaw loads this library when the container bind-mounts it and
`skills.load.extraDirs` includes `/srv/openclaw/skills`.

Legacy staging under `/data/apps/openclaw/skills/` is retired for new syncs.

## Sync from this repo

```bash
PROJ=/path/to/openclaw_coolify_tailnet_inventory
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/inventory_coolify_apps/" \
  ubuntu:/srv/openclaw/skills/inventory_coolify_apps/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/inventory_tailnet_nodes/" \
  ubuntu:/srv/openclaw/skills/inventory_tailnet_nodes/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/inventory/" \
  ubuntu:/srv/openclaw/skills/inventory/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/coolify-inventory/" \
  ubuntu:/srv/openclaw/skills/coolify-inventory/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/tailscale-inventory/" \
  ubuntu:/srv/openclaw/skills/tailscale-inventory/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/app-dashboard-inventory/" \
  ubuntu:/srv/openclaw/skills/app-dashboard-inventory/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/diagnostics/" \
  ubuntu:/srv/openclaw/skills/diagnostics/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/coolify-readonly/" \
  ubuntu:/srv/openclaw/skills/coolify-readonly/
rsync -az --no-owner --no-group --delete \
  "$PROJ/skills/infrastructure-inventory/" \
  ubuntu:/srv/openclaw/skills/infrastructure-inventory/
scp "$PROJ/deploy/deploy-skill.sh" ubuntu:/srv/openclaw/deploy-skill.sh
ssh ubuntu 'chmod +x /srv/openclaw/deploy-skill.sh'
```

## Container mount (Coolify compose)

```yaml
volumes:
  - 'syowig5e8r47c96qh26btdc0_openclaw-data:/data'
  - '/srv/knowledge:/knowledge'
  - '/srv/openclaw/skills:/srv/openclaw/skills'
```

## Live OpenClaw config

In `/data/.openclaw/openclaw.json` (inside the OpenClaw volume):

```json5
{
  skills: {
    load: {
      extraDirs: ["/srv/openclaw/skills"],
      watch: true,
    },
    // ... existing entries ...
  },
}
```

`extraDirs` is lowest precedence. A same-named skill under
`/data/workspace/skills/` still wins. Prefer editing the library and
removing stale workspace copies of inventory skills.

## Optional workspace copy

If you still want a workspace override/copy:

```bash
/srv/openclaw/deploy-skill.sh inventory
/srv/openclaw/deploy-skill.sh coolify-inventory
/srv/openclaw/deploy-skill.sh tailscale-inventory
/srv/openclaw/deploy-skill.sh app-dashboard-inventory
/srv/openclaw/deploy-skill.sh diagnostics/check_tailnet_urls
/srv/openclaw/deploy-skill.sh diagnostics/diagnose_tailnet_service
```

## Inventory output

```text
/knowledge/inventory/coolify/
/knowledge/inventory/tailscale/
/data/apps/inventory/app-dashboard.yaml   # app-dashboard-inventory
```

Do **not** bind-mount `/data/apps/openclaw` or `/srv/openclaw` over OpenClaw’s live config directory (`/data/.openclaw`).
