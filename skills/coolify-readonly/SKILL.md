---
name: coolify-readonly
description: Safety contract for Coolify MCP server coolify-readonly — read-only discovery only; never mutate, deploy, or print tokens.
metadata:
  openclaw:
    requires:
      env:
        - COOLIFY_MCP_TOKEN
---

# Coolify read-only

This is a **read-only** Coolify MCP safety contract. Use before any Coolify MCP call.

MCP server name: **`coolify-readonly`** (never treat a server named bare `coolify` as approved for inventory).

## When to use

- Before Coolify MCP tools
- When `infrastructure-inventory` refreshes Coolify data

## When not to use

- Any Coolify write (deploy, restart, create, delete, env changes) — **refuse**; that belongs to a future infrastructure-actions capability
- Direct Coolify REST/API calls — **forbidden**; use MCP only

## Prerequisites

- `coolify-readonly` registered in OpenClaw via MCP CLI/UI (do not overwrite live dynamic config with a bind-mounted file)
- Endpoint: `https://ubuntu-server.tiger-bushmaster.ts.net/mcp`
- `COOLIFY_MCP_TOKEN` injected (read-only); never print it
- Tool allowlist applied — see repo `docs/mcp-coolify-tools.md`

## Allowed

- Call allowlisted **read** tools on `coolify-readonly` only
- Summarize name, uuid/id, status, domains (non-secret)

## Forbidden

- deploy, restart, stop, delete, create, update infrastructure
- change Coolify environment variables
- retrieve secrets / `reveal: true`
- print tokens or Authorization headers
- call Coolify HTTP APIs outside MCP

## Procedure

1. Confirm MCP server id is `coolify-readonly`.
2. Use only tools present in the OpenClaw allowlist for that server.
3. Redact secrets from all outputs.
4. If the user asks to mutate Coolify, refuse and point to future write-path architecture.

## Security

Defense in depth: read-only token + toolFilter + this skill.
