---
id: workflow.infrastructure.generate-service-inventory
title: Generate service inventory
description: Refresh read-only Coolify (and optional Tailscale) inventory into /knowledge/inventory/.
type: workflow
risk: low
---

# Generate service inventory

## Objective

Produce a validated `/knowledge/inventory/services.yaml` via MCP discovery without modifying infrastructure.

## Skills used

- `coolify-readonly`
- `infrastructure-inventory`

## Procedure

1. Confirm OpenClaw mounts and `coolify-readonly` MCP (see `docs/ops-verification.md`, `docs/mcp-coolify.md`).
2. Ask OpenClaw: **Refresh infrastructure inventory**.
3. Review diff summary; confirm `No infrastructure modifications were performed.`
4. Spot-check `/knowledge/inventory/services.yaml` and `overrides.yaml` preservation.

## Rollback

Restore previous file from `/knowledge/inventory/history/`.

## Related

- `docs/IMPLEMENTATION-PLAN.md`
- `docs/security-model.md`
