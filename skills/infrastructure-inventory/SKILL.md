---
name: infrastructure-inventory
description: Read-only Coolify (and later Tailscale) MCP discovery, correlation, and YAML inventory under /knowledge/inventory/.
metadata:
  openclaw:
    requires:
      env:
        - COOLIFY_MCP_TOKEN
---

# Infrastructure inventory

**This is a read-only infrastructure discovery skill.**

It queries approved read-only MCP servers, normalizes and correlates resources, applies manual overrides, validates, and writes inventory under `/knowledge/inventory/`. It must never modify Coolify or Tailscale infrastructure.

## When to use

- User asks to **refresh infrastructure inventory**, `/inventory refresh`, or equivalent
- `/inventory show`, `/inventory coolify`, `/inventory tailscale`, `/inventory diff` (or natural-language equivalents)
- Building or updating the private dashboard source of truth (`services.yaml`)

## When not to use

- Deploy, restart, stop, delete, create, or reconfigure anything
- Changing Coolify env vars, Tailscale ACLs, DNS, routes, or auth keys
- Retrieving secrets or writing credentials
- Calling Coolify/Tailscale HTTP APIs directly (MCP only)

If the user requests a write action, explain it belongs to the **future infrastructure-actions** capability (n8n / policy gateway), not this skill.

## Prerequisites

- Follow [`coolify-readonly`](../coolify-readonly/SKILL.md) for Coolify MCP safety
- MCP server `coolify-readonly` configured; Tailscale only if `tailscale-readonly` is approved after evaluation
- Writable `/knowledge/inventory/` (see repo `docs/ops-verification.md`)
- Schemas: `schemas/inventory.schema.json` in this skill directory

## Allowed

```text
read MCP data
write /knowledge/inventory/**
validate files
compare inventories
generate dashboard metadata
```

## Forbidden

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

## Paths

```text
/knowledge/inventory/
├── services.yaml              # canonical correlated SoT
├── overrides.yaml             # manual dashboard prefs (preserve)
├── generated/
│   ├── coolify.yaml
│   └── tailscale.yaml
├── history/
│   └── services-<timestamp>.yaml
└── logs/
```

## Refresh procedure (Coolify-only until Tailscale approved)

1. **Safety** — Confirm read-only; load `coolify-readonly`.
2. **Discover Coolify** — Via `coolify-readonly` allowlisted tools (`list_applications`, `list_services`, `list_databases`, `list_servers`, overview/get as needed). Do not call write tools.
3. **Normalize** — Write `/knowledge/inventory/generated/coolify.yaml` (atomic: `.tmp` → rename). No secrets.
4. **Discover Tailscale** — If `tailscale-readonly` is registered and approved, list devices and write `generated/tailscale.yaml`. Otherwise skip and note Tailscale deferred in the summary.
5. **Correlate** — Apply rules in `docs/correlation-rules.md`. Status: `confirmed` | `probable` | `unmatched` | `conflict`. Fuzzy matches must **not** silently become authoritative (`probable` + evidence).
6. **Overrides** — Read `/knowledge/inventory/overrides.yaml` if present; merge **after** correlation (overrides win for dashboard fields).
7. **Build candidate** `services.yaml` with `version`, `generated_at`, provenance under `sources`, status, network URLs when known.
8. **Validate** against `schemas/inventory.schema.json`. On failure: write candidate to `/knowledge/inventory/generated/services.invalid.yaml` (or similar); **do not** overwrite a valid `services.yaml`.
9. **History** — Copy previous `services.yaml` to `history/services-<UTC compact timestamp>.yaml`; retain latest 10–20 files.
10. **Atomic write** — Write `services.yaml.tmp` → validate again if needed → `rename` to `services.yaml`.
11. **Diff** — Compare previous vs new; report added/removed/changed/unmatched/conflicts.
12. **Log** — Append under `/knowledge/inventory/logs/` (timestamp, command, MCP servers, tool names, counts, validation, diff summary, paths). Never log tokens or Authorization headers.
13. **Reply** — Human-readable summary ending with: `No infrastructure modifications were performed.`

## Invocation

Preferred phrases / commands (document if slash commands are unsupported in this OpenClaw build):

| Intent | Phrase |
|--------|--------|
| Refresh | `Refresh infrastructure inventory` / `/inventory refresh` |
| Show | `/inventory show` |
| Coolify only | `/inventory coolify` |
| Tailscale only | `/inventory tailscale` |
| Diff | `/inventory diff` |

## Stable service IDs

Prefer lowercase slug from Coolify service/application name; otherwise hostname; ensure uniqueness. Conflicts → `correlation.status: conflict` and do not invent silent merges.

## Web interfaces

Mark `dashboard.enabled: true` when a MagicDNS HTTPS URL or known UI port/label suggests a web UI; otherwise leave false/omit and let overrides enable.

## Validation

- Schema passes before replace
- Overrides survive refresh
- No secrets in YAML or logs
- Diff summary produced

## Related

- Repo docs: `docs/infrastructure-inventory.md`, `docs/inventory-schema.md`, `docs/security-model.md`
- Templates: `templates/services.example.yaml`
- Correlation: `docs/correlation-rules.md`
