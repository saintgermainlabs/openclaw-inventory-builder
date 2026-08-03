# coolify-inventory

Read-only OpenClaw skill: discover Coolify via MCP `coolify-readonly`, write normalized `raw/latest.json`, then build hierarchical `inventory.yaml` / `inventory.json`.

## Architecture

```text
Coolify → coolify-readonly MCP → OpenClaw skill (orchestration)
                                      ↓
                               raw/latest.json
                                      ↓
                          build_inventory.py (no network)
                                      ↓
                         inventory.yaml + inventory.json
                                      ↓
                          validate_inventory.py
```

| Layer | Responsibility |
|-------|----------------|
| MCP | Infrastructure retrieval |
| `SKILL.md` | Agent orchestration |
| Python scripts | Deterministic transform + validation |

## Directory structure

```text
coolify-inventory/
├── SKILL.md
├── README.md
├── scripts/
│   ├── build_inventory.py
│   └── validate_inventory.py
├── schemas/
│   └── inventory.schema.json
├── examples/
│   ├── inventory.yaml
│   └── inventory.json
└── tests/
```

## Development vs runtime

| Location | Role |
|----------|------|
| `/data/apps/openclaw/skills/coolify-inventory` | Source / development |
| `/data/workspace/skills/coolify-inventory` | OpenClaw runtime (after deploy) |

```bash
/data/apps/openclaw/deploy-skill.sh coolify-inventory
```

## Output location

```text
/knowledge/inventory/coolify/
├── inventory.yaml
├── inventory.json
├── raw/latest.json
├── history/
└── logs/
```

## Intermediate raw JSON

Stable schema for builders (not raw MCP payloads):

```json
{
  "projects": [
    {
      "id": "…",
      "name": "…",
      "environments": [
        {
          "id": "…",
          "name": "…",
          "applications": [],
          "services": [],
          "databases": []
        }
      ]
    }
  ]
}
```

Optional per-resource fields (only when known): `status`, `domains`, `git`, `server`, `type`, etc. Never invent values.

## Manual script tests

```bash
cd /data/apps/openclaw/skills/coolify-inventory

python3 scripts/build_inventory.py \
  --input examples/raw.fixture.json \
  --output-dir /tmp/coolify-inv-test \
  --format both

python3 scripts/validate_inventory.py /tmp/coolify-inv-test/inventory.yaml
python3 scripts/validate_inventory.py /tmp/coolify-inv-test/inventory.json
```

Or use repo fixtures under `tests/fixtures/`.

## Safety model

- Read-only MCP + read-only skill instructions
- No Coolify API calls from Python
- No secrets in skill files or inventory output
- No deploy/restart/delete/create/env changes

## Future

Separate skills (`tailscale-inventory`, etc.) will produce sibling inventories; a later merger builds `infrastructure.yaml`. This Coolify schema stays Coolify-focused.
