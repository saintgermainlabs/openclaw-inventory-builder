# Inventory schema and storage

## Layout on host

```text
/knowledge/inventory/
├── services.yaml
├── overrides.yaml
├── generated/
│   ├── coolify.yaml
│   └── tailscale.yaml
├── history/
└── logs/
```

## Canonical `services.yaml`

Correlated source of truth for a future dashboard. Validated by [`skills/infrastructure-inventory/schemas/inventory.schema.json`](../skills/infrastructure-inventory/schemas/inventory.schema.json).

Required top-level fields:

- `version` (integer ≥ 1)
- `generated_at` (ISO-8601 string)
- `services` (map of stable service id → service object)

Each service should include `name` and, where known, `sources`, `network`, `status`, `correlation`, `dashboard`.

Service ids: `^[a-z0-9][a-z0-9_-]*$` and unique (map keys).

## Status enums

- `status.application`: `running` | `stopped` | `degraded` | `unknown`
- `status.tailnet`: `online` | `offline` | `unknown`
- `correlation.status`: `confirmed` | `probable` | `unmatched` | `conflict`

## URLs

`network.private_url` must be a valid URI when present (typically `https://<host>.tiger-bushmaster.ts.net`).

## Overrides

[`overrides.yaml`](../examples/inventory/overrides.example.yaml) holds manual dashboard preferences. Refreshes must re-apply overrides after correlation.

## Atomic write + history

1. Write candidate to `services.yaml.tmp`
2. Validate against JSON Schema
3. On failure: keep previous `services.yaml`; save invalid candidate under `generated/`
4. On success: copy previous to `history/services-<UTC>.yaml` (retain 10–20)
5. `rename` tmp → `services.yaml`

## Diff

Each refresh reports: new/removed services, status changes, URL changes, new/missing Tailnet nodes, new Coolify resources, correlation conflicts.

## Examples

- [`examples/inventory/services.example.yaml`](../examples/inventory/services.example.yaml)
- [`examples/inventory/overrides.example.yaml`](../examples/inventory/overrides.example.yaml)
- [`examples/inventory/generated/`](../examples/inventory/generated/)
