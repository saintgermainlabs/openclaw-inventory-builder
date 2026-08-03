# Ops verification — OpenClaw runtime and inventory mounts

Run these checks on the **Coolify/OpenClaw host**.

**Do not bind-mount a host `openclaw.json` over the container config.** OpenClaw’s live config is already full and dynamic. Register MCP servers with `openclaw mcp add` / `openclaw mcp set` (or Control UI `/settings/mcp`) so existing settings are preserved.

Optional: keep a host-side **development staging** tree under `/data/apps/openclaw/` (`skills/`, `scripts/`, `docs/`, `config/`). See [`../deploy/README.md`](../deploy/README.md). Do **not** bind-mount that tree over OpenClaw’s live config.

## 1. Identify the OpenClaw container

```bash
docker ps --format '{{.Names}}\t{{.Image}}' | grep -i openclaw
OC=<openclaw-container-name>
```

## 2. Confirm OpenClaw can read its existing config

```bash
docker exec "$OC" openclaw config path   # if supported
docker exec "$OC" openclaw mcp status
```

Do **not** replace or overlay `/data/.openclaw` unless OpenClaw docs for your version explicitly require it.

## 3. Knowledge mount (required for inventory writes)

Ensure Compose includes a knowledge volume, for example:

```yaml
volumes:
  - /srv/knowledge:/knowledge
```

Inventory output path inside the container: `/knowledge/inventory/`.

## 4. Host `/data/apps` (optional operator tree)

`/data/apps` remains the Coolify-independent app config root for **other** apps and for operator docs. It is **not** used to inject OpenClaw’s live `openclaw.json`.

```bash
sudo mkdir -p /data/apps/openclaw/docs
sudo chown root:root /data/apps
sudo chmod 755 /data/apps
# Permission /data/apps/openclaw for operators as needed; do not chown all of /data/apps to OpenClaw
```

## 5. Inventory directories on knowledge mount

```bash
sudo mkdir -p /srv/knowledge/inventory/{generated,history,logs}
docker exec "$OC" id   # OPENCLAW_UID / OPENCLAW_GID
sudo chown -R "<OPENCLAW_UID>:<OPENCLAW_GID>" /srv/knowledge/inventory
sudo chmod -R u+rwX /srv/knowledge/inventory
```

## 6. Verification checklist

| Check | Result | Notes |
|-------|--------|-------|
| OpenClaw container name | _pending_ | |
| Live config left intact (no json bind-mount) | _pending_ | |
| `/knowledge` mounted and writable for inventory | _pending_ | |
| `COOLIFY_MCP_TOKEN` present in OpenClaw env | _pending_ | |
| `coolify-readonly` registered via MCP CLI/UI | _pending_ | |

## Related

- [`mcp-coolify.md`](mcp-coolify.md) — register `coolify-readonly`
- [`IMPLEMENTATION-PLAN.md`](IMPLEMENTATION-PLAN.md)
