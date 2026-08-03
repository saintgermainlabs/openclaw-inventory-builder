---
name: tailscale-inventory
description: Generate YAML and JSON inventories of Tailscale devices (hostname, MagicDNS, online state, tags, addresses) using the configured read-only Tailscale MCP.
metadata:
  openclaw:
    requires:
      env:
        - TAILSCALE_API_KEY
---

# Tailscale inventory

**This is a read-only Tailscale discovery skill.**

Use the configured MCP server **`tailscale-readonly`** only. Discover tailnet devices, normalize results, write intermediate JSON, then run deterministic Python builders to produce YAML/JSON under `/knowledge/inventory/tailscale/`.

Do **not** call the Tailscale HTTP API directly. Do **not** store or print API tokens.

## When to use

- `/tailscale-inventory` (default: both YAML and JSON)
- `/tailscale-inventory yaml` | `json` | `both` | `summary`
- Natural language: “Refresh the Tailscale inventory”, “List Tailscale devices as YAML”, “Generate a JSON inventory of the tailnet”

## When not to use

- Coolify-only inventory → `coolify-inventory`
- Correlated Coolify+Tailscale merger → future infrastructure merger skill
- Any Tailscale mutation → refuse

## Safety (mandatory)

Never perform infrastructure mutations. Do **not** use MCP tools that:

```text
authorize / deauthorize
delete devices
expire keys
set routes
modify ACL / DNS / policy
create or delete auth keys
connect / disconnect this host
change tags (write)
retrieve secrets
```

Use only allowlisted read tools on `tailscale-readonly` (typically `list_devices`, `get_tailnet_info`, and other read-only tools exposed by the filter). Even if write tools appear, skip them. Package risk must stay at `read`.

## Paths

```text
Skill source (dev):     /data/apps/openclaw/skills/tailscale-inventory/
Skill runtime:          /data/workspace/skills/tailscale-inventory/

Output:
/knowledge/inventory/tailscale/
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
tailscale-readonly MCP  →  agent normalizes  →  raw/latest.json
                                                 →  scripts/build_inventory.py
                                                 →  inventory.yaml / inventory.json
                                                 →  scripts/validate_inventory.py
```

Python scripts must **not** make network calls.

## Output format

Default `/tailscale-inventory` → **both** YAML and JSON.

| Request | Formats |
|---------|---------|
| (default) / both | yaml + json |
| yaml | yaml only |
| json | json only |
| summary | generate both if needed, then summarize counts |

## MCP discovery workflow

1. Ensure dirs under `/knowledge/inventory/tailscale/{raw,history,logs}` exist.
2. Using **only** `tailscale-readonly`, call read tools (prefer `list_devices`; optionally `get_tailnet_info` for metadata).
3. Normalize into `raw/latest.json`:

```json
{
  "tailnet": {
    "name": "optional-or-omitted",
    "dns_suffix": "optional-or-omitted"
  },
  "devices": [
    {
      "id": "device-id",
      "hostname": "uptime-kuma",
      "name": "uptime-kuma.tiger-bushmaster.ts.net",
      "online": true,
      "addresses": ["100.x.x.x"],
      "tags": ["tag:example"],
      "os": "linux",
      "client_version": "optional"
    }
  ]
}
```

   Only include fields actually returned. **Never invent** values.
4. Build:

```bash
python3 scripts/build_inventory.py \
  --input /knowledge/inventory/tailscale/raw/latest.json \
  --output-dir /knowledge/inventory/tailscale \
  --format both
```

5. Validate:

```bash
python3 scripts/validate_inventory.py /knowledge/inventory/tailscale/inventory.yaml
python3 scripts/validate_inventory.py /knowledge/inventory/tailscale/inventory.json
```

6. Reply with a summary (no secrets):

```text
Tailscale inventory refreshed.

Devices: N
Online: N
Offline: N
Unknown: N

Generated:
- /knowledge/inventory/tailscale/inventory.yaml
- /knowledge/inventory/tailscale/inventory.json

No infrastructure modifications were performed.
```

## Canonical inventory shape

Produced by `build_inventory.py`:

```yaml
version: 1
source:
  type: tailscale
  mcp_server: tailscale-readonly
generated_at: "…"
tailnet:
  dns_suffix: tiger-bushmaster.ts.net   # if known
devices:
  uptime-kuma:
    id: "…"
    hostname: uptime-kuma
    name: uptime-kuma.tiger-bushmaster.ts.net
    online: true
    addresses: […]
    tags: […]
```

Device map keys are hostname slugs for readability; **device `id` remains the identity**.

## Related

- MCP server: `tailscale-readonly`
- Deploy: `/data/apps/openclaw/deploy-skill.sh tailscale-inventory`
- Sibling: `coolify-inventory`
