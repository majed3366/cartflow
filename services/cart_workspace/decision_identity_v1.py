# -*- coding: utf-8 -*-
"""Decision identity — stable decision_id + evidence fingerprint; no UI."""
from __future__ import annotations

import hashlib
import uuid
from typing import Iterable, Optional


def build_evidence_fingerprint(
    *,
    store_slug: str,
    recovery_key: str,
    proof_class: str,
    evidence_ids: Iterable[str],
    matrix_path: str = "normal",
) -> str:
    """Canonical fingerprint for AS-1 / AI-9 / R17 stability."""
    parts = [
        (store_slug or "").strip().lower(),
        (recovery_key or "").strip(),
        (proof_class or "").strip().lower(),
        (matrix_path or "normal").strip().lower(),
        "|".join(sorted({(e or "").strip() for e in evidence_ids if (e or "").strip()})),
    ]
    material = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def allocate_decision_id() -> str:
    return str(uuid.uuid4())


def allocate_admission_id() -> str:
    return str(uuid.uuid4())


def open_decision_duplicate_key(
    *,
    store_slug: str,
    recovery_key: str,
    evidence_fingerprint: str,
) -> str:
    return f"{(store_slug or '').strip().lower()}::{(recovery_key or '').strip()}::{evidence_fingerprint}"


def find_open_duplicate(
    open_decisions: Iterable[dict],
    *,
    store_slug: str,
    recovery_key: str,
    evidence_fingerprint: str,
) -> Optional[dict]:
    """Return existing open Decision dict if fingerprint already admitted."""
    slug = (store_slug or "").strip().lower()
    rk = (recovery_key or "").strip()
    fp = (evidence_fingerprint or "").strip()
    for d in open_decisions:
        if (d.get("status") or "open") != "open":
            continue
        if (d.get("store_slug") or "").strip().lower() != slug:
            continue
        if (d.get("recovery_key") or "").strip() != rk:
            continue
        if (d.get("evidence_fingerprint") or "").strip() == fp:
            return d
    return None
