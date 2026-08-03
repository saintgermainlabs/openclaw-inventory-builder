# tailscale-inventory

Read-only OpenClaw skill: discover Tailscale via MCP `tailscale-readonly`, write `raw/latest.json`, then build `inventory.yaml` / `inventory.json`.

## Architecture

```text
Tailscale API → tailscale-readonly MCP → OpenClaw skill
                                            ↓
                                     raw/latest.json
                                            ↓
                                build_inventory.py (no network)
                                            ↓
                               inventory.yaml + inventory.json
```

## Development vs runtime

| Location | Role |
|----------|------|
| `/data/apps/openclaw/skills/tailscale-inventory` | Source |
| `/data/workspace/skills/tailscale-inventory` | Runtime |

```bash
/data/apps/openclaw/deploy-skill.sh tailscale-inventory
```

## Output

```text
/knowledge/inventory/tailscale/
├── inventory.yaml
├── inventory.json
├── raw/latest.json
├── history/
└── logs/
```

## Manual tests

```bash
cd /data/apps/openclaw/skills/tailscale-inventory
python3 scripts/build_inventory.py \
  --input examples/raw.fixture.json \
  --output-dir /tmp/ts-inv-test \
  --format both
python3 scripts/validate_inventory.py /tmp/ts-inv-test/inventory.yaml
python3 tests/test_build_inventory.py
```

## Safety

- MCP risk `read` + OpenClaw tool allowlist
- No direct Tailscale API calls from Python
- No secrets in skill files or inventory output
