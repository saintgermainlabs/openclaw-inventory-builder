# AGENTS.md

Instructions for agents working in `openclaw_coolify_tailnet_inventory`.

## Purpose

OpenClaw skills/workflows for **read-only** Coolify + Tailscale discovery via MCP, writing inventory under `/knowledge/inventory/`. Follow [`docs/IMPLEMENTATION-PLAN.md`](docs/IMPLEMENTATION-PLAN.md).

## Core rules

1. **Never commit secrets.** No API tokens, Authorization headers, or live `openclaw.json` with credentials. Use env var names only (`COOLIFY_MCP_TOKEN`, `TAILSCALE_MCP_TOKEN`).
2. **Read-only infrastructure.** Never deploy, restart, stop, delete, create, or reconfigure Coolify/Tailscale through inventory skills.
3. **MCP adapters only.** Do not call Coolify/Tailscale REST APIs directly from skills unless explicitly approved later.
4. **Server naming.** Register Coolify as `coolify-readonly` (never bare `coolify`). Tailscale as `tailscale-readonly` when approved.
5. **Writes allowed only** under `/knowledge/inventory/**` (plus skill/docs in this repo).
6. **Do not invent** hosts, UUIDs, MagicDNS names, or tool lists — discover via MCP or leave TODO / verification pending.
7. **Tailscale MCP** is gated: complete `docs/mcp-tailscale-evaluation.md` before installing any Tailscale MCP.

## Security layers

```text
1. Read-only credential
2. MCP tool allowlist (toolFilter.include)
3. Skill instructions
```

## Host paths

| Path | Role |
|------|------|
| OpenClaw live config | Dynamic — register MCP via CLI/UI; never bind-mount over it |
| `/knowledge/inventory/` | Inventory SoT + generated + history + logs |
| `/srv/openclaw/skills/` | **Canonical skills library** (host; bind-mounted into OpenClaw) |
| `/data/apps/openclaw/` | Legacy staging / MCP fragments only |
| Coolify MCP URL | `https://ubuntu-server.tiger-bushmaster.ts.net/mcp` |

## Precedence for inventory

```text
MCP discovery → normalize → correlate → overrides.yaml → services.yaml
```

Validate before atomic replace. On validation failure, write a debug candidate; do not overwrite a valid `services.yaml`.
