# -*- coding: utf-8 -*-
"""
Evidence versioning primitives — immutable (evidence_id, evidence_version).

WP-ET-00: helpers only. No persistence / supersession store.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Optional


def build_evidence_id_v1(
    *,
    evidence_family: str,
    evidence_type: str,
    store_slug: str,
    subject: str,
    window_key: str = "",
) -> str:
    """
    Stable logical identity: family + type + store + subject + window key.

    Format is opaque but deterministic for equivalent inputs.
    """
    parts = [
        (evidence_family or "").strip().lower(),
        (evidence_type or "").strip(),
        (store_slug or "").strip().lower(),
        (subject or "").strip(),
        (window_key or "").strip(),
    ]
    if not parts[0] or not parts[1] or not parts[2] or not parts[3]:
        raise ValueError("evidence_id_requires_family_type_store_subject")
    return "|".join(parts)


def next_evidence_version_v1(
    current_version: Optional[int] = None,
    *,
    supersedes: Optional[int] = None,
) -> int:
    """
    Monotonic version helper.

    If supersedes is set, next version must be supersedes + 1.
    Otherwise increments current_version (default start at 1).
    """
    if supersedes is not None:
        if int(supersedes) < 1:
            raise ValueError("supersedes_must_be_positive")
        return int(supersedes) + 1
    if current_version is None:
        return 1
    cur = int(current_version)
    if cur < 1:
        raise ValueError("current_version_must_be_positive")
    return cur + 1


def content_integrity_hash_v1(payload: Mapping[str, Any]) -> str:
    """
    Deterministic content hash for immutability verification.

    Excludes volatile envelope identity fields; callers pass the canonical
    content dict they wish to seal.
    """
    raw = json.dumps(dict(payload or {}), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
