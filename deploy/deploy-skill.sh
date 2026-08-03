#!/usr/bin/env bash
set -euo pipefail

SKILL="${1:-}"
OC_CONTAINER="${OPENCLAW_CONTAINER:-openclaw-syowig5e8r47c96qh26btdc0}"
SOURCE_ROOT="${OPENCLAW_SKILLS_LIBRARY:-/srv/openclaw/skills}"
RUNTIME_ROOT="${OPENCLAW_SKILLS_RUNTIME:-/data/workspace/skills}"

if [[ -z "$SKILL" ]]; then
    echo "Usage: $0 <skill-name>"
    echo "  Canonical library: $SOURCE_ROOT"
    echo "  Runtime copy:      \$OC_CONTAINER:$RUNTIME_ROOT"
    echo
    echo "When /srv/openclaw/skills is bind-mounted and skills.load.extraDirs"
    echo "includes it, OpenClaw loads skills live — this script is optional"
    echo "and only refreshes the workspace copy (higher precedence)."
    exit 1
fi

SOURCE="$SOURCE_ROOT/$SKILL"
RUNTIME="$RUNTIME_ROOT/$SKILL"

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
echo "  library: $SOURCE"
echo "  container: $OC_CONTAINER:$RUNTIME"

# Prefer docker cp (no sudo). Clear previous runtime copy first.
docker exec "$OC_CONTAINER" rm -rf "$RUNTIME"
docker exec "$OC_CONTAINER" mkdir -p "$RUNTIME_ROOT"
docker cp "$SOURCE" "$OC_CONTAINER:$RUNTIME"

# Fallback: volume rsync with sudo if docker cp somehow incomplete
if ! docker exec "$OC_CONTAINER" test -f "$RUNTIME/SKILL.md"; then
    VOLUME_RUNTIME="/var/lib/docker/volumes/syowig5e8r47c96qh26btdc0_openclaw-data/_data/workspace/skills"
    TARGET="$VOLUME_RUNTIME/$SKILL"
    echo "docker cp verification failed; trying sudo rsync to $TARGET"
    sudo mkdir -p "$TARGET"
    sudo rsync -av --delete "$SOURCE/" "$TARGET/"
fi

echo
echo "Deployment complete:"
docker exec "$OC_CONTAINER" find "$RUNTIME" -type f | sort
