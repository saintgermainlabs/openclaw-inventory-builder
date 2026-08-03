# Correlation rules

Deterministic matching from Coolify resources to Tailscale devices.

## Confidence order

1. Explicit mapping in `/knowledge/inventory/overrides.yaml` (e.g. `sources.tailscale.hostname` forced)
2. Exact Tailscale hostname == Coolify service name
3. Exact Tailscale hostname == Coolify application name
4. Exact known domain mapping (MagicDNS label == Coolify name)
5. Docker/Compose labels (`TS_HOSTNAME`, `app.name`, sidecar `<name>-tailscale`)
6. Normalized-name match (lowercase, strip non-alnum)
7. Fuzzy match — **never** silently authoritative

## Correlation status

| Status | Meaning |
|--------|---------|
| `confirmed` | Rules 1–5 exact evidence |
| `probable` | Normalized or fuzzy; include `confidence` + `evidence` |
| `unmatched` | No acceptable peer |
| `conflict` | Multiple candidates or contradictory evidence |

## Probable example

```yaml
correlation:
  status: probable
  confidence: 0.82
  evidence:
    - "normalized service names match"
```

## Do not

- Match on Coolify `servers[].ip` when it is `host.docker.internal`
- Promote fuzzy matches to `confirmed` without human override
- Drop unmatched Coolify or Tailscale entries — list them under inventory unmatched sections or leave as services with `correlation.status: unmatched`
