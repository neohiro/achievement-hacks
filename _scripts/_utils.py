"""_utils.py — Shared utilities for achievement-hacks scripts.

Contains token-redaction helpers used by multiple scripts.
"""
from __future__ import annotations

import re

GITHUB_TOKEN_RE = re.compile(r"(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+")


def scrub_sensitive(text: str) -> str:
    """Remove likely GitHub token values from strings before logging or surfacing.

    Handles: ghp_..., github_pat_..., gho_..., ghs_..., ghr_... tokens.
    Replaces the full token with a sentinel so the redaction is obvious.
    """
    return GITHUB_TOKEN_RE.sub("***REDACTED***", text)
