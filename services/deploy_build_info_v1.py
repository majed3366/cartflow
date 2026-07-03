# -*- coding: utf-8 -*-
"""Deploy build identity for startup logs and verification (logging only)."""
from __future__ import annotations

import os
import subprocess
from typing import Optional

_DEPLOY_GIT_SHA_ENV_KEYS = (
    "CARTFLOW_GIT_SHA",
    "RAILWAY_GIT_COMMIT_SHA",
    "RENDER_GIT_COMMIT",
    "SOURCE_VERSION",
    "HEROKU_SLUG_COMMIT",
    "K_REVISION",
)


def normalize_git_sha(sha: Optional[str], *, short_len: int = 7) -> str:
    raw = (sha or "").strip().lower()
    if not raw:
        return "unknown"
    if len(raw) > short_len:
        return raw[:short_len]
    return raw


def resolve_deploy_git_sha(*, short: bool = True) -> str:
    """Best-effort commit SHA from PaaS env or local git."""
    for key in _DEPLOY_GIT_SHA_ENV_KEYS:
        v = (os.environ.get(key) or "").strip()
        if v:
            return normalize_git_sha(v) if short else v[:48]
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).decode("utf-8", errors="replace").strip()
        if out:
            return normalize_git_sha(out) if short else out
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


__all__ = ["normalize_git_sha", "resolve_deploy_git_sha"]
