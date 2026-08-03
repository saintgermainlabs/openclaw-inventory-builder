---
name: coolify-inventory
description: Generate hierarchical YAML and JSON inventories of Coolify projects, environments, applications, services, databases, domains, and resource metadata using the configured read-only Coolify MCP.
metadata:
  openclaw:
    requires:
      env:
        - COOLIFY_MCP_TOKEN
---

# Coolify inventory

**This is a read-only Coolify discovery skill.**

Use the configured MCP server **`coolify-readonly`** only. Discover Coolify infrastructure, normalize results, write intermediate JSON, then run deterministic Python builders to produce YAML/JSON inventories under `/knowledge/inventory/coolify/`.

Do **not** call the Coolify HTTP API directly. Do **not** store or print API tokens.

## When to use

- `/coolify-inventory` (default: both YAML and JSON)
- `/coolify-inventory yaml` | `json` | `both` | `summary`
- Natural language: “Refresh the Coolify inventory”, “Generate a JSON inventory of Coolify”, “Show me the current Coolify project hierarchy”

## When not to use

- Tailscale / correlated multi-source inventory → other skills later
- Any Coolify mutation → refuse; belongs to a future write-path capability

## Safety (mandatory)

Never perform infrastructure mutations. Do **not** use MCP tools that:

```text
deploy
restart
stop
delete
create
modify domains
modify environment variables
modify server configuration
retrieve secrets
change Coolify configuration
```

Even if write tools appear in the MCP catalog, skip them. Prefer list/get/overview/diagnose-style reads only.

## Paths

```text
Skill source (dev):     /data/apps/openclaw/skills/coolify-inventory/
Skill runtime:          /data/workspace/skills/coolify-inventory/

Output:
/knowledge/inventory/coolify/
├── inventory.yaml
├── inventory.json
├── raw/
│   └── latest.json
├── history/
└── logs/
```

Create missing directories automatically.

## Architecture

```text
coolify-readonly MCP  →  agent normalizes  →  raw/latest.json
                                              →  scripts/build_inventory.py
                                              →  inventory.yaml / inventory.json
                                              →  scripts/validate_inventory.py
```

Python scripts must **not** make network calls.

## Output format

Default `/coolify-inventory` → **both** YAML and JSON.

| Request | Formats |
|---------|---------|
| (default) / both | yaml + json |
| yaml | yaml only |
| json | json only |
| summary | generate both if missing/stale, then summarize counts only |

## MCP discovery workflow

1. Ensure dirs under `/knowledge/inventory/coolify/{raw,history,logs}` exist.
2. Using **only** `coolify-readonly`, discover:
   - projects
   - environments per project
   - applications, services, databases (attach under the correct project/environment when IDs/links are available)
   - useful detail fields and domains/URLs when returned by MCP
3. Do **not** hardcode tool names if discovery works via available list/get tools. Prefer currently available read tools (inspect with MCP tools listing when unsure). Common read candidates include list/get for projects, environments, applications, services, databases, servers, domains, and infrastructure overview.
4. **Never invent** missing fields. Omit unknowns.
5. Write normalized intermediate JSON to `/knowledge/inventory/coolify/raw/latest.json` using this shape:

```json
{
  "projects": [
    {
      "id": "project-uuid",
      "name": "Project Name",
      "environments": [
        {
          "id": "environment-uuid",
          "name": "production",
          "applications": [],
          "services": [],
          "databases": []
        }
      ]
    }
  ]
}
```

6. Run the builder (from this skill directory):

```bash
python3 scripts/build_inventory.py \
  --input /knowledge/inventory/coolify/raw/latest.json \
  --output-dir /knowledge/inventory/coolify \
  --format both
```

For yaml-only or json-only, pass `--format yaml` or `--format json`.

7. Validate:

```bash
python3 scripts/validate_inventory.py /knowledge/inventory/coolify/inventory.yaml
python3 scripts/validate_inventory.py /knowledge/inventory/coolify/inventory.json
```

8. Reply with a summary (no secrets), for example:

```text
Coolify inventory refreshed.

Projects: N
Environments: N
Applications: N
Services: N
Databases: N

Running resources: N
Stopped resources: N
Unknown states: N

Generated:
- /knowledge/inventory/coolify/inventory.yaml
- /knowledge/inventory/coolify/inventory.json

No infrastructure modifications were performed.
```

## Hierarchy

```text
Project
  └── Environment
       ├── Applications
       ├── Services
       └── Databases
```

Canonical inventory fields are produced by `build_inventory.py` (version, source, generated_at, nested maps). Resource map keys are stable slugs for readability; **IDs remain the identity**.

## Related

- MCP server name: `coolify-readonly`
- Deploy from host: `/data/apps/openclaw/deploy-skill.sh coolify-inventory`
- README in this skill directory for script testing and schema details
