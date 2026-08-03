# Security model

## Principle

Inventory capabilities are **read-only** with respect to Coolify and Tailscale.

OpenClaw may write generated files under `/knowledge/inventory/**` only.

## Defense in depth

```text
1. Read-only credential (COOLIFY_MCP_TOKEN / future TAILSCALE_MCP_TOKEN)
2. MCP tool allowlist (toolFilter.include)
3. Skill instructions (coolify-readonly + infrastructure-inventory)
```

Never rely on model instructions alone.

## READ path (this project)

```text
OpenClaw
   ↓
read-only MCP (coolify-readonly / tailscale-readonly)
   ↓
Coolify / Tailscale APIs
   ↓
/knowledge/inventory/
```

MCP server names include `-readonly` so privilege expansion is obvious.

Do **not** later upgrade these tokens to admin. Create separate credentials for writes.

## WRITE path — future (not implemented)

```text
OpenClaw
   ↓
controlled action interface
   ↓
n8n / policy gateway
   ↓
schema validation + allowlist + approval + audit log
   ↓
Coolify / Tailscale
```

Potential future tools (examples only):

```text
restart_service
redeploy_service
create_application
change_configuration
remove_device
```

Illustrative risk classes:

```yaml
actions:
  restart_service:
    risk: low
    approval: false
  redeploy_service:
    risk: medium
    approval: true
  delete_service:
    risk: critical
    approval: always
  modify_tailnet_acl:
    risk: critical
    approval: always
  expose_secret:
    permitted: false
```

## Forbidden through inventory

- deploy / restart / stop / delete / create infrastructure
- change Coolify environment variables
- change DNS / Tailscale ACLs / routes / auth keys
- retrieve or write secrets
- call Coolify/Tailscale REST APIs outside MCP

## Secrets

Never store tokens in:

- skill files
- generated YAML
- git
- inventory logs

Logs may record tool names and counts, never Authorization headers.
