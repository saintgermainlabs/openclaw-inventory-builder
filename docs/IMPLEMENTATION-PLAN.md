# OpenClaw Read-Only Infrastructure Inventory — Implementation Plan

## Goal

Enable OpenClaw to discover the current Coolify and Tailscale infrastructure through read-only MCP integrations, correlate the discovered resources, and generate a normalized YAML inventory that can later drive a private dashboard.

This phase must be strictly read-only with respect to infrastructure.

OpenClaw may write generated inventory files to the knowledge/config filesystem, but it must not be capable of deploying, restarting, deleting, modifying, or reconfiguring Coolify or Tailscale resources.

---

## Target Architecture

```text
                    OpenClaw
                       |
              inventory skill
                       |
          +------------+------------+
          |                         |
          v                         v
   Coolify MCP                Tailscale MCP
   read-only token            read-only/scoped auth
          |                         |
          v                         v
      Coolify API               Tailnet API
          \                         /
           \                       /
            +------ correlate ----+
                       |
                       v
            /knowledge/inventory/
                       |
             normalized YAML
                       |
                       v
              future dashboard
```

The MCP servers are the infrastructure adapters.

The OpenClaw skill should not directly implement Coolify or Tailscale API calls unless there is a later, explicitly approved reason to do so.

---

# Phase 1 — Verify OpenClaw Runtime (no config bind-mount)

OpenClaw’s live configuration is **full and dynamic**. Do **not** bind-mount a host `openclaw.json` into the container or overwrite `/data/.openclaw`.

Register MCP servers with:

```bash
openclaw mcp set …
```

or Control UI `/settings/mcp`, so existing settings are preserved.

Preferred Compose volumes for this project:

```yaml
volumes:
  - openclaw-data:/data
  - /srv/knowledge:/knowledge
```

Optional operator reference copies may live under `/data/apps/openclaw/` on the host; they are **not** injected as the live config.

Verify:

```bash
docker exec <openclaw-container> openclaw config path   # if supported
docker exec <openclaw-container> openclaw mcp status
```

---

# Phase 2 — Host Directory Permissions

Use `/data/apps` as the host-side application configuration root.

Desired layout:

```text
/data/apps/
├── openclaw/
│   └── openclaw.json
├── coolify/
├── n8n/
├── authentik/
└── ...
```

Keep `/data/apps` itself owned by root:

```bash
sudo chown root:root /data/apps
sudo chmod 755 /data/apps
```

Determine the UID/GID used by OpenClaw:

```bash
docker exec <openclaw-container> id
```

Then configure only the OpenClaw directory for that container:

```bash
sudo chown root:<OPENCLAW_GID> /data/apps/openclaw
sudo chmod 750 /data/apps/openclaw
```

Do not recursively assign ownership of `/data/apps` to OpenClaw.

Each application's directory must be permissioned independently.

OpenClaw live config permissions stay under OpenClaw’s own state volume — not a host-mounted `openclaw.json`.

---

# Phase 3 — Verify Coolify MCP

Determine whether the Coolify MCP server is enabled.

Verify:

1. Coolify API access is enabled.
2. Coolify MCP server is enabled.
3. The MCP endpoint exists.
4. A dedicated token is created for OpenClaw.
5. The token has only read permissions.

Expected MCP endpoint:

```text
https://ubuntu-server.tiger-bushmaster.ts.net/mcp
```

Test connectivity from the OpenClaw host/container.

Example:

```bash
curl -i https://ubuntu-server.tiger-bushmaster.ts.net/mcp
```

A `401`, `403`, or MCP-specific response can confirm the endpoint exists.

A `404` likely indicates the route is unavailable or MCP is disabled.

Then test with the dedicated read-only token.

Do not place the token directly into source control.

---

# Phase 4 — Secret Handling

Store MCP credentials outside the OpenClaw skill.

Preferred source:

```text
Coolify environment variables / secret variables
```

Example:

```text
COOLIFY_MCP_TOKEN=<secret>
TAILSCALE_MCP_TOKEN=<secret>
```

The OpenClaw configuration should reference environment variables rather than literal secrets.

Example conceptual configuration:

```json
{
  "mcp": {
    "servers": {
      "coolify-readonly": {
        "url": "https://ubuntu-server.tiger-bushmaster.ts.net/mcp",
        "transport": "streamable-http",
        "headers": {
          "Authorization": "Bearer ${COOLIFY_MCP_TOKEN}"
        }
      }
    }
  }
}
```

Apply via `openclaw mcp set` / Control UI — **not** by replacing the live config file.

Adapt this to the exact OpenClaw MCP schema supported by the installed OpenClaw version.

Do not guess configuration keys if the CLI or documentation can confirm them.

---

# Phase 5 — Register Coolify MCP in OpenClaw

Register the MCP server under a name that communicates its security scope:

```text
coolify-readonly
```

Do not call it simply:

```text
coolify
```

The name should make accidental privilege expansion obvious.

Use OpenClaw MCP CLI or Control UI. Do not bind-mount or overwrite the dynamic live `openclaw.json`.

After registration, verify:

```bash
openclaw mcp status
```

and, if supported:

```bash
openclaw mcp doctor coolify-readonly --probe
```

or equivalent MCP inspection commands available in the installed OpenClaw release.

Record:

* MCP server name
* transport
* URL
* authentication method
* available tools
* read-only guarantees
* failures/errors

---

# Phase 6 — Audit Coolify MCP Tools

Enumerate every tool exposed by the MCP server.

Create a document:

```text
/data/apps/openclaw/docs/mcp-coolify-tools.md
```

For every tool, record:

```text
tool name
purpose
read/write classification
needed for inventory?
allowed?
```

Example:

```text
list_servers              read     yes
list_applications         read     yes
list_services             read     yes
list_databases            read     yes
get_server_resources      read     yes
get_domains               read     yes
deploy_application        write    no
delete_application        write    no
```

If OpenClaw supports MCP tool include/exclude filters, configure an explicit allowlist.

Do not rely solely on model instructions to prevent write operations.

Security layers should be:

```text
1. Read-only credential
2. MCP tool allowlist
3. Skill instructions
```

---

# Phase 7 — Tailscale MCP Research and Selection

Do not immediately install an arbitrary third-party Tailscale MCP server.

First create:

```text
/data/apps/openclaw/docs/mcp-tailscale-evaluation.md
```

Evaluate candidate Tailscale MCP implementations using:

* project owner
* maintenance activity
* source availability
* authentication model
* OAuth support
* exposed tools
* support for read-only scopes
* whether destructive tools can be disabled
* deployment model
* Docker support
* compatibility with OpenClaw MCP
* trust/supply-chain risk

The preferred implementation must allow OpenClaw to discover:

```text
devices
hostnames
MagicDNS names
online/offline state
tags
addresses
routes if useful
tailnet metadata
```

without granting:

```text
device deletion
ACL changes
DNS changes
auth key creation
route modification
tag ownership modification
```

If no sufficiently safe Tailscale MCP exists, document that and defer Tailscale MCP integration rather than granting broad privileges.

A thin internal read-only MCP adapter is acceptable later if necessary.

---

# Phase 8 — Create the Inventory Skill

Create:

```text
/data/workspace/skills/infrastructure-inventory/
```

or the correct persistent OpenClaw skill path already used by this deployment.

Suggested structure:

```text
infrastructure-inventory/
├── SKILL.md
├── README.md
├── schemas/
│   └── inventory.schema.json
├── templates/
│   └── services.example.yaml
└── docs/
    └── correlation-rules.md
```

The skill should contain instructions and schemas rather than infrastructure credentials.

---

# Phase 9 — Skill Responsibilities

The skill should:

1. Query approved read-only MCP servers.
2. Retrieve Coolify infrastructure.
3. Retrieve Tailnet infrastructure.
4. Normalize records.
5. Correlate matching resources.
6. Detect likely web interfaces.
7. Generate stable service identifiers.
8. Preserve provenance.
9. mark uncertain correlations.
10. Write YAML.
11. Produce a change summary.

It must never make direct infrastructure changes.

---

# Phase 10 — Inventory Storage Model

Use:

```text
/knowledge/inventory/
├── services.yaml
├── overrides.yaml
├── generated/
│   ├── coolify.yaml
│   └── tailscale.yaml
└── history/
```

The generated source files should contain raw normalized discovery results.

Example:

```yaml
applications:
  - id: app-123
    name: uptime-kuma
    status: running
    server: hetzner-main
```

Tailscale example:

```yaml
devices:
  - hostname: uptime-kuma
    dns_name: uptime-kuma.tiger-bushmaster.ts.net
    online: true
```

---

# Phase 11 — Canonical services.yaml

`services.yaml` is the correlated source of truth used by downstream dashboard tooling.

Example:

```yaml
version: 1

generated_at: "2026-08-02T21:00:00-05:00"

services:

  uptime-kuma:
    name: "Uptime Kuma"
    type: monitoring

    sources:
      coolify:
        resource_id: "abc123"

      tailscale:
        hostname: "uptime-kuma"

    network:
      private_url: "https://uptime-kuma.tiger-bushmaster.ts.net"

    status:
      application: running
      tailnet: online

    dashboard:
      enabled: true
      category: Monitoring
```

Every correlated property should retain provenance where practical.

---

# Phase 12 — Manual Overrides

Never mix generated discovery data with manually maintained dashboard preferences.

Use:

```text
/knowledge/inventory/overrides.yaml
```

Example:

```yaml
uptime-kuma:
  dashboard:
    name: "Uptime"
    category: "Monitoring"
    icon: "uptime-kuma"
    order: 10
```

Inventory refreshes must preserve these values.

Define precedence as:

```text
MCP discovery
    ↓
normalized source data
    ↓
correlation
    ↓
manual overrides
    ↓
services.yaml
```

---

# Phase 13 — Correlation Rules

Create deterministic matching rules.

Suggested confidence order:

```text
1. Explicit configured mapping
2. Exact Tailscale hostname == Coolify service name
3. Exact hostname == application name
4. Exact known domain mapping
5. Docker/Compose labels
6. normalized-name match
7. fuzzy match
```

Fuzzy matches must never silently become authoritative.

Represent uncertain matches like:

```yaml
correlation:
  status: probable
  confidence: 0.82
  evidence:
    - "normalized service names match"
```

Possible values:

```text
confirmed
probable
unmatched
conflict
```

---

# Phase 14 — Schema Validation

Create a JSON Schema for `services.yaml`.

Validate at minimum:

* unique service IDs
* valid URLs
* allowed status values
* allowed correlation states
* source provenance
* required service names
* generated timestamp
* version number

The skill should validate before replacing the existing canonical inventory.

If validation fails:

```text
do not overwrite the previous valid services.yaml
```

Write the invalid candidate to a temporary/debug file instead.

---

# Phase 15 — Atomic Writes

Avoid partially written inventory files.

Use:

```text
services.yaml.tmp
```

Then:

```text
validate
→ rename atomically
```

Keep at least a small history if practical:

```text
/knowledge/inventory/history/
    services-2026-08-02T210000.yaml
```

Retention can initially be limited to the latest 10–20 inventories.

---

# Phase 16 — Inventory Diff

Each refresh should compare the new inventory with the previous one.

Report:

```text
new services
removed services
status changes
URL changes
new Tailnet nodes
missing Tailnet nodes
new Coolify resources
correlation conflicts
```

Example result:

```text
Inventory refreshed.

Added:
- vikunja

Changed:
- uptime-kuma: tailnet offline -> online

Unmatched:
- postgres-production

No infrastructure modifications were performed.
```

---

# Phase 17 — Slash Command Interface

Expose a simple user-facing workflow.

Desired commands:

```text
/inventory
/inventory refresh
/inventory show
/inventory coolify
/inventory tailscale
/inventory diff
```

If OpenClaw's current skill system does not automatically generate slash commands, document the supported invocation syntax instead of inventing unsupported behavior.

---

# Phase 18 — Safety Rules

The skill's `SKILL.md` must explicitly state:

```text
This is a read-only infrastructure discovery skill.
```

Allowed:

```text
read MCP data
write /knowledge/inventory/**
validate files
compare inventories
generate dashboard metadata
```

Forbidden:

```text
deploy
restart
stop
delete
create infrastructure
change Coolify environment variables
change DNS
modify Tailscale ACLs
create auth keys
change routes
retrieve secrets
write credentials
call direct infrastructure APIs
```

If a user requests a write action through this skill, it should explain that the operation belongs to the future infrastructure-actions capability.

---

# Phase 19 — Logging

Create useful audit logs without logging secrets.

Record:

```text
timestamp
inventory command
MCP servers queried
tools invoked
number of resources discovered
validation result
diff summary
output path
error messages
```

Never log:

```text
API tokens
Authorization headers
environment secrets
private keys
auth keys
credentials
```

Suggested location:

```text
/knowledge/inventory/logs/
```

or the existing OpenClaw logging mechanism if more appropriate.

---

# Phase 20 — Testing

Create tests for:

### Configuration

* OpenClaw sees the mounted config.
* MCP credentials resolve through environment variables.
* secrets are absent from committed files.

### Coolify

* MCP connection succeeds.
* inventory tools work.
* write tools are unavailable or blocked.

### Tailscale

* read-only discovery succeeds.
* destructive capabilities are absent.

### Inventory

* resources normalize correctly.
* correlation rules work.
* overrides survive refreshes.
* invalid YAML/schema does not replace valid inventory.
* atomic writes work.
* diff detects additions/removals/changes.

### Security

Attempt intentionally forbidden operations and verify failure.

Examples:

```text
deploy an application
delete an application
delete a Tailnet node
create a Tailscale auth key
modify ACL policy
```

These must be impossible through the inventory capability.

---

# Phase 21 — Documentation Deliverables

Create:

```text
/data/apps/openclaw/docs/
├── infrastructure-inventory.md
├── mcp-coolify.md
├── mcp-coolify-tools.md
├── mcp-tailscale-evaluation.md
├── inventory-schema.md
└── security-model.md
```

`security-model.md` should explain the intended long-term split:

```text
READ PATH

OpenClaw
   ↓
read-only MCP
   ↓
Coolify / Tailscale


WRITE PATH — future

OpenClaw
   ↓
controlled action interface
   ↓
n8n / policy gateway
   ↓
approval / validation / logging
   ↓
Coolify / Tailscale
```

Never turn the read-only MCP identities into admin identities later.

Create separate credentials and separate tools for future write operations.

---

# Phase 22 — Future Infrastructure Actions Layer

Do not implement write actions in this task.

Document the future architecture only.

Potential future tools:

```text
restart_service
redeploy_service
create_application
change_configuration
remove_device
```

These should not expose unrestricted Coolify/Tailscale APIs directly to OpenClaw.

Preferred path:

```text
OpenClaw
    ↓
n8n or dedicated policy gateway
    ↓
schema validation
    ↓
allowlist
    ↓
approval if required
    ↓
audit log
    ↓
infrastructure API
```

Risk classification could eventually look like:

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

This is explicitly outside the current implementation.

---

# Implementation Order

Work in this order:

```text
1. Inspect existing OpenClaw deployment.
2. Confirm live config is dynamic (no host openclaw.json bind-mount).
3. Ensure /knowledge mount and inventory dirs.
4. Verify Coolify MCP endpoint (ubuntu-server…/mcp).
5. Create read-only Coolify credential (COOLIFY_MCP_TOKEN).
6. Register coolify-readonly via openclaw mcp set / Control UI.
7. Probe and document tools.
8. Apply an explicit read-tool allowlist.
9. Build Coolify-only inventory generation.
10. Define and validate YAML schema.
11. Implement override handling.
12. Implement inventory diff.
13. Evaluate Tailscale MCP implementations.
14. Add safe Tailscale read-only discovery.
15. Implement deterministic correlation.
16. Add tests.
17. Document security architecture.
```

Do not begin with the dashboard UI.

The inventory model must be stable first.

---

# Acceptance Criteria

The first milestone is complete when this command/workflow:

```text
Refresh infrastructure inventory
```

causes OpenClaw to:

```text
query Coolify through read-only MCP
query Tailscale through read-only MCP
normalize resources
correlate them
apply manual overrides
validate the result
write /knowledge/inventory/services.yaml
show a useful diff
```

while being technically unable to modify Coolify or Tailscale infrastructure through the inventory capability.

No secret should exist in the skill files, generated YAML, Git repository, or logs.

The resulting `services.yaml` should be suitable as the source of truth for a later dashboard generator.
