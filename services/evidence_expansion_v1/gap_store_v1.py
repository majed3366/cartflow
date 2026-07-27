# -*- coding: utf-8 -*-
"""
Evidence Gap persistence — internal registry only.

Never attach gaps to merchant Home / dashboard summary payloads.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

log = logging.getLogger("cartflow")


def _utc_naive(dt: Optional[datetime] = None) -> datetime:
    d = dt or datetime.now(timezone.utc)
    if d.tzinfo is not None:
        return d.astimezone(timezone.utc).replace(tzinfo=None)
    return d


def _parse_iso(raw: Any) -> Optional[datetime]:
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return _utc_naive(datetime.fromisoformat(s))
    except ValueError:
        return None


def _content_hash(gap: Mapping[str, Any]) -> str:
    payload = {
        "family": gap.get("diagnostic_family"),
        "status": gap.get("diagnosis_status"),
        "missing": [
            m.get("observable_key")
            for m in list(gap.get("evidence_missing") or [])
            if isinstance(m, Mapping)
        ],
        "causes": list(gap.get("competing_causes") or []),
        "priority": gap.get("priority"),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def upsert_evidence_gap_v1(gap: Mapping[str, Any]) -> dict[str, Any]:
    """Idempotent persist of an Evidence Gap (internal)."""
    from extensions import db
    from models import EvidenceGap
    from schema_evidence_expansion_v1 import ensure_evidence_expansion_schema
    from services.evidence_expansion_v1.contract_v1 import (  # noqa: PLC0415
        resolve_gap_status_transition_v1,
    )

    ensure_evidence_expansion_schema(db)
    slug = str(gap.get("store_slug") or "").strip()
    family = str(gap.get("diagnostic_family") or "").strip()
    gap_id = str(gap.get("gap_id") or "").strip()
    if not (slug and family and gap_id):
        return {"ok": False, "reason": "identity_required"}

    ch = _content_hash(gap)
    generated = _parse_iso(gap.get("generated_at")) or _utc_naive()

    row = (
        db.session.query(EvidenceGap)
        .filter(EvidenceGap.gap_id == gap_id)
        .first()
    )
    if row is not None and str(row.content_hash or "") == ch:
        row.updated_at = _utc_naive()
        db.session.commit()
        return {"ok": True, "mode": "touch", "gap_id": gap_id}

    incoming_status = str(gap.get("gap_status") or "open")
    existing_status = str(row.gap_status or "open") if row is not None else "open"
    effective_status, transition = resolve_gap_status_transition_v1(
        existing_status=existing_status,
        incoming_status=incoming_status,
        reopen_reason=str(gap.get("reopen_reason") or ""),
    )

    # Persist effective lifecycle; never silently reopen terminal gaps.
    payload = dict(gap)
    payload["gap_status"] = effective_status
    if transition == "terminal_preserved_no_reopen_reason":
        payload["lifecycle_note"] = transition
    payload_json = json.dumps(payload, ensure_ascii=False)

    if row is None:
        row = EvidenceGap(gap_id=gap_id, store_slug=slug, diagnostic_family=family)
        db.session.add(row)
        mode = "insert"
    elif transition == "terminal_preserved_no_reopen_reason":
        # Refresh metadata hash/payload but keep terminal status.
        mode = "terminal_preserved"
    else:
        mode = "update"

    row.store_slug = slug
    row.diagnostic_family = family
    row.diagnostic_id = str(gap.get("diagnostic_id") or "")
    row.subject_type = str(gap.get("subject_type") or "")
    row.subject_id = str(gap.get("subject_id") or "")
    row.diagnosis_status = str(gap.get("diagnosis_status") or "")
    row.gap_status = effective_status
    row.priority = str(gap.get("priority") or "medium")
    row.payload_json = payload_json
    row.content_hash = ch
    row.evidence_expansion_version = str(
        gap.get("evidence_expansion_version") or "evidence_expansion_v1"
    )
    row.generated_at = generated
    row.internal_only = True
    row.updated_at = _utc_naive()
    db.session.commit()
    return {
        "ok": True,
        "mode": mode,
        "gap_id": gap_id,
        "gap_status": effective_status,
        "transition": transition,
    }


def list_open_evidence_gaps_v1(
    store_slug: str,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Internal read — never wire into merchant summary."""
    from extensions import db
    from models import EvidenceGap
    from schema_evidence_expansion_v1 import ensure_evidence_expansion_schema

    slug = (store_slug or "").strip()
    if not slug:
        return []
    try:
        ensure_evidence_expansion_schema(db)
        rows = (
            db.session.query(EvidenceGap)
            .filter(EvidenceGap.store_slug == slug)
            .filter(EvidenceGap.gap_status == "open")
            .filter(EvidenceGap.internal_only.is_(True))
            .order_by(EvidenceGap.generated_at.desc())
            .limit(max(1, min(200, int(limit))))
            .all()
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("evidence gap list failed: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            out.append(json.loads(row.payload_json or "{}"))
        except Exception:  # noqa: BLE001
            out.append(
                {
                    "gap_id": row.gap_id,
                    "diagnostic_family": row.diagnostic_family,
                    "gap_status": row.gap_status,
                }
            )
    return out


__all__ = [
    "list_open_evidence_gaps_v1",
    "upsert_evidence_gap_v1",
]
