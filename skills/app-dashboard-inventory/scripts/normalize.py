"""Name normalization for stable IDs and matching."""

from __future__ import annotations

import re

_PUNCT_RE = re.compile(r"[^a-z0-9\s_-]+")
_SEP_RE = re.compile(r"[\s_]+")
_HYPHEN_RE = re.compile(r"-{2,}")


def normalize_name(value: str) -> str:
    """Normalize a display name to a hyphenated slug.

    Examples:
      "Uptime Kuma"  -> "uptime-kuma"
      "Open WebUI"   -> "open-webui"
      "VaultWarden"  -> "vaultwarden"
    """
    s = (value or "").strip().lower()
    s = _PUNCT_RE.sub("", s)
    s = _SEP_RE.sub("-", s)
    s = _HYPHEN_RE.sub("-", s)
    return s.strip("-")
