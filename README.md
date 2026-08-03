# openclaw_coolify_tailnet_inventory

OpenClaw **skills and workflows** for **read-only** Coolify and Tailscale infrastructure discovery via MCP, correlation, and YAML inventory under `/knowledge/inventory/`.

Canonical specification: [`docs/IMPLEMENTATION-PLAN.md`](docs/IMPLEMENTATION-PLAN.md).

## Architecture

```text
OpenClaw → infrastructure-inventory skill
        → coolify-readonly MCP (HTTPS) → Coolify API
        → tailscale-readonly MCP (later) → Tailnet API
        → correlate → /knowledge/inventory/services.yaml
        → future dashboard
```

OpenClaw must not deploy, restart, delete, or reconfigure Coolify/Tailscale through this capability.

## Security layers

1. Read-only credential (`COOLIFY_MCP_TOKEN`, later `TAILSCALE_MCP_TOKEN`)
2. MCP `toolFilter` allowlist
3. Skill instructions

## Host paths

| Path | Role |
|------|------|
| OpenClaw live config | Managed dynamically inside OpenClaw — **do not bind-mount** a host `openclaw.json` over it |
| `/knowledge/inventory/` | Generated + canonical inventory (knowledge mount) |
| `/srv/openclaw/skills/` | **Canonical skills library** (bind-mounted + `skills.load.extraDirs`) |
| `/data/apps/openclaw/` | Legacy staging / MCP config fragments (not the skills library) |

## Quick start

1. Follow [`docs/ops-verification.md`](docs/ops-verification.md) (knowledge mount + inventory dirs).
2. Create a Coolify **read-only** token; inject as OpenClaw env `COOLIFY_MCP_TOKEN` (never commit).
3. Register MCP server `coolify-readonly` via `openclaw mcp set` / Control UI using [`config/coolify-readonly.mcp.json`](config/coolify-readonly.mcp.json) (endpoint: `https://ubuntu-server.tiger-bushmaster.ts.net/mcp`).
4. Sync skills to **`/srv/openclaw/skills`** (see [`deploy/README.md`](deploy/README.md)). With the bind-mount + `extraDirs` configured, OpenClaw loads them live.
5. Ask OpenClaw: **Generate Coolify inventory** or **Refresh infrastructure inventory**.

## Skills

| Skill | Role |
|-------|------|
| [`coolify-readonly`](skills/coolify-readonly/SKILL.md) | Coolify MCP safety contract |
| [`inventory_coolify_apps`](skills/inventory_coolify_apps/SKILL.md) | **Preferred:** flat Coolify apps+services → `/knowledge/inventory/coolify/apps.yaml` |
| [`inventory_tailnet_nodes`](skills/inventory_tailnet_nodes/SKILL.md) | **Preferred:** flat Tailscale nodes → `/knowledge/inventory/tailscale/nodes.yaml` |
| [`inventory`](skills/inventory/SKILL.md) | Older merged dump skill (prefer the two flat skills above) |
| [`coolify-inventory`](skills/coolify-inventory/SKILL.md) | Deprecated alias → use `/inventory_coolify_apps` |
| [`tailscale-inventory`](skills/tailscale-inventory/SKILL.md) | Deprecated alias → use `/inventory_tailnet_nodes` |
| [`app-dashboard-inventory`](skills/app-dashboard-inventory/SKILL.md) | Dashboard apps catalogue → `/data/apps/inventory/app-dashboard.yaml` |
| [`check-tailnet-urls`](skills/diagnostics/check_tailnet_urls/SKILL.md) | Probe UI URLs from app-dashboard; report reachable / unreachable |
| [`diagnose-tailnet-service`](skills/diagnostics/diagnose_tailnet_service/SKILL.md) | Deep-diagnose one Tailnet UI hostname (DNS/HTTP/Docker/Serve) |
| [`infrastructure-inventory`](skills/infrastructure-inventory/SKILL.md) | Full Coolify (+ Tailscale later) correlation refresh |

**Next (not built yet):** `inventory_coolify_insert_ids` and `inventory_tailnet_insert_ids` — walk the flat lists and fill basic identifying fields per id.

Legacy list/inspect helpers were folded into `infrastructure-inventory`.

## Docs

| Doc | Purpose |
|-----|---------|
| [IMPLEMENTATION-PLAN.md](docs/IMPLEMENTATION-PLAN.md) | Full phased plan (source of truth) |
| [ops-verification.md](docs/ops-verification.md) | Mount + permissions + endpoint checks |
| [mcp-coolify.md](docs/mcp-coolify.md) | Coolify MCP registration |
| [mcp-coolify-tools.md](docs/mcp-coolify-tools.md) | Tool audit / allowlist |
| [mcp-tailscale-evaluation.md](docs/mcp-tailscale-evaluation.md) | Tailscale MCP selection (gated) |
| [inventory-schema.md](docs/inventory-schema.md) | `services.yaml` model |
| [infrastructure-inventory.md](docs/infrastructure-inventory.md) | Skill + refresh workflow |
| [security-model.md](docs/security-model.md) | Read path vs future write path |

## Inventory layout

```text
/knowledge/inventory/
├── coolify/
│   └── apps.yaml     # inventory_coolify_apps (flat apps + services)
├── tailscale/
│   └── nodes.yaml    # inventory_tailnet_nodes (flat nodes)
├── services.yaml     # correlated (infrastructure-inventory)
├── overrides.yaml
├── generated/
├── history/
└── logs/
```

Examples and schema live under [`examples/inventory/`](examples/inventory/) and skill `schemas/` dirs.

## Roadmap

1. Coolify MCP + Coolify-only inventory ✓
2. Tailscale MCP + Tailscale-only inventory ✓
3. Full correlation + dashboard consumer (dashboard UI out of scope here)
