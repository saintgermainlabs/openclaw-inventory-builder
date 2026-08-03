# Tailscale MCP evaluation

**Status: evaluation only — do not install a Tailscale MCP until this document concludes with an approved option.**

Host mirror when deployed: `/data/apps/openclaw/docs/mcp-tailscale-evaluation.md`.

## Required discovery capabilities

Must support read access to:

- devices
- hostnames
- MagicDNS names
- online/offline state
- tags
- addresses
- routes (useful, optional)
- tailnet metadata (optional)

## Must not grant (or must be disableable)

- device deletion
- ACL changes
- DNS changes
- auth key creation
- route modification
- tag ownership modification

## Evaluation criteria

| Criterion | Weight |
|-----------|--------|
| Project owner / provenance | high |
| Maintenance activity | high |
| Source availability | high |
| Authentication model (API key / OAuth) | high |
| OAuth support | medium |
| Exposed tools (read vs write) | critical |
| Read-only scopes / risk levels | critical |
| Destructive tools disableable (allowlist) | critical |
| Deployment model / Docker | medium |
| OpenClaw MCP compatibility (stdio or streamable-http) | high |
| Trust / supply-chain risk | high |

## Candidates

### 1. `mcp-tailscale` (aplaceforallmystuff)

| Field | Notes |
|-------|--------|
| Owner | community npm package |
| Tools | list/get/online/offline/summary/updates — **read-only by design** |
| Auth | `TAILSCALE_API_KEY`, optional `TAILSCALE_TAILNET` |
| Destructive tools | none documented |
| Deploy | often needs local build; weaker `npx` story |
| OpenClaw | stdio MCP |
| Trust | low download volume; review source before use |

### 2. `@hexsleeves/tailscale-mcp-server`

| Field | Notes |
|-------|--------|
| Owner | HexSleeves |
| Tools | includes list_devices **and** authorize/delete/routes/ACL-oriented tools |
| Auth | API key / CLI |
| Destructive tools | present — **requires** strict OpenClaw `toolFilter.include` + never write token scopes if available |
| Deploy | `npx -y @hexsleeves/tailscale-mcp-server` |
| OpenClaw | stdio |
| Trust | review releases; allowlist-only if chosen |

### 3. `tailscale-mcp` (broader API gateway)

| Field | Notes |
|-------|--------|
| Tools | large surface including delete/ACL/keys |
| Read-only | only via aggressive allowlist |
| Recommendation | **reject** for inventory unless heavily filtered and separately audited |

### 4. Thin internal read-only MCP adapter

| Field | Notes |
|-------|--------|
| Owner | this organization |
| Tools | only `list_devices` / get fields needed |
| Auth | Tailscale API key or OAuth with minimal scopes |
| Destructive tools | none implemented |
| Deploy | container beside OpenClaw |
| Recommendation | **preferred fallback** if no third-party option is trustworthy enough |

## Decision (current)

| Decision | **Install `@hexsleeves/tailscale-mcp-server` as `tailscale-readonly`** |
|----------|--------|
| Package | `npx -y @hexsleeves/tailscale-mcp-server` |
| Risk gate | `TAILSCALE_ALLOWED_TOOL_RISK=read` (package default / enforced) |
| OpenClaw filter | `list_devices`, `get_tailnet_info`, `get_network_status`, `get_version`, `get_version_info`, `ping_peer` |
| Auth | Coolify/OpenClaw env `TAILSCALE_API_KEY` (never in git) |
| Tailnet | `-` (default) |
| Config fragment | `config/tailscale-readonly.mcp.json` |

Register with:

```bash
docker exec openclaw-… openclaw mcp set tailscale-readonly "$(cat /data/apps/openclaw/config/tailscale-readonly.mcp.json)"
```