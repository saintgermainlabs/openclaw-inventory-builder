# Coolify MCP (`coolify-readonly`)

Remote Coolify MCP for OpenClaw — **read-only** discovery only.

## Endpoint

```text
https://ubuntu-server.tiger-bushmaster.ts.net/mcp
```

## Prerequisites

1. Coolify API enabled
2. Coolify MCP enabled on the instance
3. Endpoint reachable from OpenClaw host/container
4. Dedicated **read-only** token for OpenClaw
5. Token injected as env `COOLIFY_MCP_TOKEN` (never in git)

## Connectivity probe

```bash
curl -i https://ubuntu-server.tiger-bushmaster.ts.net/mcp
```

| Response | Meaning |
|----------|---------|
| `401` / `403` / MCP protocol response | Endpoint likely exists |
| `404` | Route missing or MCP disabled |

With token (do not log the token):

```bash
curl -i -H "Authorization: Bearer ${COOLIFY_MCP_TOKEN}" \
  https://ubuntu-server.tiger-bushmaster.ts.net/mcp
```

## Register from the host (recommended)

Use the fragment file [`config/coolify-readonly.mcp.json`](../config/coolify-readonly.mcp.json). Do **not** use `docker exec … << cat file` — that heredoc form is invalid.

**Simplest (host expands the file, passes JSON as one argument):**

```bash
OC=openclaw-syowig5e8r47c96qh26btdc0
CFG=/path/to/openclaw_coolify_tailnet_inventory/config/coolify-readonly.mcp.json

docker exec "$OC" openclaw mcp set coolify-readonly "$(cat "$CFG")"
```

**Or copy the file in, then set:**

```bash
OC=openclaw-syowig5e8r47c96qh26btdc0
CFG=/path/to/openclaw_coolify_tailnet_inventory/config/coolify-readonly.mcp.json

docker cp "$CFG" "$OC":/tmp/coolify-readonly.mcp.json
docker exec "$OC" sh -c 'openclaw mcp set coolify-readonly "$(cat /tmp/coolify-readonly.mcp.json)"'
```

Ensure `COOLIFY_MCP_TOKEN` is already set in the OpenClaw **container/service env** so `${COOLIFY_MCP_TOKEN}` resolves inside OpenClaw.

Then verify:

```bash
docker exec "$OC" openclaw mcp status
docker exec "$OC" openclaw mcp tools coolify-readonly
```

Example using CLI (adapt flags to your OpenClaw version — check `openclaw mcp set --help`):

```bash
openclaw mcp set coolify-readonly '{
  "url": "https://ubuntu-server.tiger-bushmaster.ts.net/mcp",
  "transport": "streamable-http",
  "headers": {
    "Authorization": "Bearer ${COOLIFY_MCP_TOKEN}"
  },
  "toolFilter": {
    "include": [
      "list_servers",
      "list_applications",
      "list_services",
      "list_databases",
      "get_server",
      "get_application",
      "get_service",
      "get_database",
      "get_server_resources",
      "get_domains",
      "server_resources",
      "server_domains",
      "list_deployments",
      "get_infrastructure_overview",
      "get_version",
      "diagnose_app",
      "diagnose_server",
      "find_issues"
    ]
  }
}'
```

Reference fragment (for operators only): [`config/openclaw.json.example`](../config/openclaw.json.example).

Server name **must** be `coolify-readonly` (never bare `coolify`).

Ensure `COOLIFY_MCP_TOKEN` is set in the OpenClaw container/service environment so `${COOLIFY_MCP_TOKEN}` resolves.

Then verify:

```bash
openclaw mcp status
openclaw mcp tools coolify-readonly
# if supported:
openclaw mcp doctor coolify-readonly --probe
```

## Record after probe

| Field | Value |
|-------|--------|
| MCP server name | `coolify-readonly` |
| Transport | `streamable-http` |
| URL | `https://ubuntu-server.tiger-bushmaster.ts.net/mcp` |
| Auth | Bearer `${COOLIFY_MCP_TOKEN}` |
| Available tools | See [`mcp-coolify-tools.md`](mcp-coolify-tools.md) |
| Read-only guarantees | Read token + toolFilter + skill |
| Probe status | _pending host verification_ |

## Security

1. Read-only Coolify credential  
2. Explicit `toolFilter.include`  
3. Skill instructions (`coolify-readonly`, `infrastructure-inventory`)

Never promote this token to admin later. Future writes use separate credentials and a policy gateway (see [`security-model.md`](security-model.md)).

## Related

- Tool audit: [`mcp-coolify-tools.md`](mcp-coolify-tools.md)
- Ops: [`ops-verification.md`](ops-verification.md)
