# check_tailnet_urls

OpenClaw skill: probe UI URLs from `/data/apps/inventory/app-dashboard.yaml`.

## Run

```bash
python3 scripts/check_tailnet_urls.py
python3 scripts/check_tailnet_urls.py --json
python3 scripts/check_tailnet_urls.py --inventory /path/to/app-dashboard.yaml
```

Uses package module `diagnostics` when installed (`pip install -e .` from repo root). The script also adds `src/` to `sys.path` for local/dev runs.

## Module

Implementation lives in [`src/diagnostics/`](../../../src/diagnostics/).
