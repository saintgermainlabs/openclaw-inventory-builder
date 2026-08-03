# Coolify MCP tool audit (`coolify-readonly`)

Enumerate tools from a live probe (`openclaw mcp tools coolify-readonly`) and update this table. Until probed on the host, the **allowlist candidates** below are the intended inventory set; anything write-oriented is **denied**.

Host mirror path when deployed: `/data/apps/openclaw/docs/mcp-coolify-tools.md`.

## Classification legend

| Class | Meaning |
|-------|---------|
| read | Discovery / get / list / diagnose |
| write | Mutate infrastructure — **never allow** for inventory |

## Allowlist candidates (inventory)

| Tool name | Purpose | Class | Needed for inventory? | Allowed? |
|-----------|---------|-------|------------------------|----------|
| list_servers | List Coolify servers | read | yes | yes |
| list_applications | List applications | read | yes | yes |
| list_services | List services | read | yes | yes |
| list_databases | List databases | read | yes | yes |
| get_server | Server detail | read | yes | yes |
| get_application | Application detail | read | yes | yes |
| get_service | Service detail | read | yes | yes |
| get_database | Database detail | read | yes | yes |
| get_server_resources | Server resources | read | yes | yes |
| server_resources | Alias / variant | read | yes | yes |
| get_domains | Domains | read | yes | yes |
| server_domains | Domains variant | read | yes | yes |
| list_deployments | Deployment history (read) | read | optional | yes |
| get_infrastructure_overview | Estate summary | read | yes | yes |
| get_version | Coolify/API version | read | optional | yes |
| diagnose_app | App diagnostics | read | optional | yes |
| diagnose_server | Server diagnostics | read | optional | yes |
| find_issues | Issue scan | read | optional | yes |

After live probe: **delete rows that do not exist**; **add any extra read tools** with allowed=yes only if needed for inventory; leave all write tools allowed=no.

## Explicit deny (never in toolFilter.include)

| Tool name / pattern | Purpose | Class | Needed? | Allowed? |
|---------------------|---------|-------|---------|----------|
| deploy* | Deploy applications | write | no | **no** |
| control / start / stop / restart | Lifecycle | write | no | **no** |
| delete_* | Delete resources | write | no | **no** |
| create_* / update_* | CRUD mutators | write | no | **no** |
| bulk_env_update | Env mutation | write | no | **no** |
| stop_all_apps / redeploy_* | Batch mutators | write | no | **no** |
| private_keys / cloud_tokens | Credentials | write/sensitive | no | **no** |
| env_vars (reveal) | Secret disclosure | write/sensitive | no | **no** |

## Live probe log

| Date | Operator | Tools seen | Notes |
|------|----------|------------|-------|
| _pending_ | | | Run on OpenClaw host after registration |

## Security layers

```text
1. Read-only credential
2. MCP tool allowlist (this document + openclaw.json toolFilter)
3. Skill instructions
```
