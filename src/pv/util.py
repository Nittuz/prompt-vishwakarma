"""Small shared helpers."""

from __future__ import annotations

import re


def slugify(text: str, max_len: int = 48) -> str:
    """Lowercase, hyphenated, filesystem-safe slug; never empty."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_len].strip("-")
    return slug or "prompt"
