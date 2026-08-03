#!/usr/bin/env bash
set -euo pipefail

SKILL="${1:-}"
OC_CONTAINER="${OPENCLAW_CONTAINER:-openclaw-syowig5e8r47c96qh26btdc0}"

if [[ -z "$SKILL" ]]; then
    echo "Usage: $0 <skill-name>"
    exit 1
fi

SOURCE="/data/apps/openclaw/skills/$SKILL"
RUNTIME="/data/workspace/skills/$SKILL"

if [[ ! -d "$SOURCE" ]]; then
    echo "Skill source not found: $SOURCE"
    exit 1
fi

if [[ ! -f "$SOURCE/SKILL.md" ]]; then
    echo "Missing SKILL.md: $SOURCE/SKILL.md"
    exit 1
fi

if ! docker inspect "$OC_CONTAINER" >/dev/null 2>&1; then
    echo "OpenClaw container not found: $OC_CONTAINER"
    exit 1
fi

echo "Deploying OpenClaw skill: $SKILL"
echo "  source: $SOURCE"
echo "  container: $OC_CONTAINER:$RUNTIME"

# Prefer docker cp (no sudo). Clear previous runtime copy first.
docker exec "$OC_CONTAINER" rm -rf "$RUNTIME"
docker exec "$OC_CONTAINER" mkdir -p /data/workspace/skills
docker cp "$SOURCE" "$OC_CONTAINER:$RUNTIME"

# Fallback: volume rsync with sudo if docker cp somehow incomplete
if ! docker exec "$OC_CONTAINER" test -f "$RUNTIME/SKILL.md"; then
    RUNTIME_ROOT="/var/lib/docker/volumes/syowig5e8r47c96qh26btdc0_openclaw-data/_data/workspace/skills"
    TARGET="$RUNTIME_ROOT/$SKILL"
    echo "docker cp verification failed; trying sudo rsync to $TARGET"
    sudo mkdir -p "$TARGET"
    sudo rsync -av --delete "$SOURCE/" "$TARGET/"
fi

echo
echo "Deployment complete:"
docker exec "$OC_CONTAINER" find "$RUNTIME" -type f | sort
