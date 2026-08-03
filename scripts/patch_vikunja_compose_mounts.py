#!/usr/bin/env python3
"""Patch Vikunja Coolify compose to mount /data/apps/vikunja/{config.yml,serve.json}."""

from __future__ import annotations

import shutil
from pathlib import Path

COMPOSE = Path("/work/docker-compose.yml")
BACKUP = Path("/work/docker-compose.yml.bak.hostfiles")


def main() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    if not BACKUP.exists():
        shutil.copy2(COMPOSE, BACKUP)
        print("backup written")

    if "TS_SERVE_CONFIG" not in text:
        text = text.replace(
            "TS_USERSPACE: 'false'",
            "TS_USERSPACE: 'false'\n"
            "      TS_HOSTNAME: vikunja\n"
            "      TS_AUTH_ONCE: 'true'\n"
            "      TS_SERVE_CONFIG: /config/serve.json",
            1,
        )
        print("added TS_SERVE_CONFIG env")

    serve_vol = "- '/data/apps/vikunja/serve.json:/config/serve.json:ro'"
    if serve_vol not in text:
        needle = "- '/dev/net/tun:/dev/net/tun'"
        if needle in text:
            text = text.replace(needle, f"{serve_vol}\n      {needle}", 1)
            print("added serve.json volume on tailscale")
        else:
            state = "- 'isflhlgghylgr2ie8e0lask1_tailscale-state:/var/lib/tailscale'"
            if state in text:
                text = text.replace(state, f"{state}\n      {serve_vol}", 1)
                print("added serve.json after state volume")
            else:
                print("WARN: could not find place for serve.json volume")

    if "/etc/vikunja/config.yml" not in text:
        old_vol = "- 'isflhlgghylgr2ie8e0lask1_vikunja-data:/app/vikunja/'"
        new_vols = (
            "- '/data/apps/vikunja/config.yml:/etc/vikunja/config.yml:ro'\n"
            "      - 'isflhlgghylgr2ie8e0lask1_vikunja-data:/app/vikunja/files'"
        )
        if old_vol in text:
            text = text.replace(old_vol, new_vols, 1)
            print("replaced vikunja data mount + added config.yml")
        else:
            print("WARN: old vikunja volume line not found")
            for line in text.splitlines():
                if "vikunja-data" in line or "/app/vikunja" in line:
                    print("  ", line)

    text2 = text.replace(
        "VIKUNJA_SERVICE_PUBLICURL: $SERVICE_URL_VIKUNJA",
        "VIKUNJA_SERVICE_PUBLICURL: 'https://vikunja.tiger-bushmaster.ts.net'",
    )
    if text2 != text:
        print("updated VIKUNJA_SERVICE_PUBLICURL to MagicDNS")
        text = text2

    COMPOSE.write_text(text, encoding="utf-8")
    print("compose updated")
    keys = (
        "TS_SERVE",
        "TS_HOSTNAME",
        "serve.json",
        "config.yml",
        "/app/vikunja",
        "PUBLICURL",
        "TS_AUTH_ONCE",
    )
    for i, line in enumerate(COMPOSE.read_text(encoding="utf-8").splitlines(), 1):
        if any(k in line for k in keys):
            print(f"{i}:{line}")


if __name__ == "__main__":
    main()
