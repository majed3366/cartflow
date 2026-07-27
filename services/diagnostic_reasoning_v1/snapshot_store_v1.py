# -*- coding: utf-8 -*-
"""
Diagnostic snapshot store — idempotent upsert, last-good preservation, expiry.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.diagnostic_reasoning_v1.publish_v1 import publish_diagnostic_for_merchant_v1

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
        dt = datetime.fromisoformat(s)
        return _utc_naive(dt)
    except ValueError:
        return None


def _content_hash(contract: Mapping[str, Any]) -> str:
    payload = {
        "selected": contract.get("selected_diagnosis"),
        "status": contract.get("diagnosis_status"),
        "diagnosis_ar": contract.get("diagnosis_ar"),
        "recommendation_ar": contract.get("recommendation_ar"),
        "family": contract.get("diagnostic_family"),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def upsert_diagnostic_snapshot_v1(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Idempotent persist. On failure caller should preserve last-good (no delete)."""
    from extensions import db
    from models import DiagnosticSnapshot
    from schema_diagnostic_reasoning_v1 import ensure_diagnostic_reasoning_schema

    ensure_diagnostic_reasoning_schema(db)
    slug = str(contract.get("store_slug") or "").strip()
    family = str(contract.get("diagnostic_family") or "").strip()
    stype = str(contract.get("subject_type") or "store").strip()
    sid = str(contract.get("subject_id") or "store").strip()
    if not (slug and family):
        return {"ok": False, "reason": "identity_required"}

    pub = publish_diagnostic_for_merchant_v1(contract)
    ch = _content_hash(contract)
    generated = _parse_iso(contract.get("generated_at")) or _utc_naive()
    expires = _parse_iso(contract.get("expires_at"))
    contract_json = json.dumps(dict(contract), ensure_ascii=False)
    publication_json = json.dumps(pub, ensure_ascii=False)

    row = (
        db.session.query(DiagnosticSnapshot)
        .filter(
            DiagnosticSnapshot.store_slug == slug,
            DiagnosticSnapshot.subject_type == stype,
            DiagnosticSnapshot.subject_id == sid,
            DiagnosticSnapshot.diagnostic_family == family,
        )
        .first()
    )
    if row is not None and str(row.content_hash or "") == ch:
        row.updated_at = _utc_naive()
        db.session.commit()
        return {"ok": True, "mode": "touch", "diagnostic_id": row.diagnostic_id}

    if row is None:
        row = DiagnosticSnapshot(
            store_slug=slug,
            subject_type=stype,
            subject_id=sid,
            diagnostic_family=family,
        )
        db.session.add(row)
        mode = "insert"
    else:
        mode = "update"
        # Preserve previous as last-good before overwrite.
        if row.contract_json:
            row.last_good_contract_json = row.contract_json
            row.last_good_generated_at = row.generated_at

    row.diagnostic_id = str(contract.get("diagnostic_id") or row.diagnostic_id or "")
    row.diagnosis_status = str(contract.get("diagnosis_status") or "")
    row.confidence_level = str(contract.get("confidence_level") or "")
    row.selected_diagnosis = (
        str(contract.get("selected_diagnosis"))
        if contract.get("selected_diagnosis") is not None
        else None
    )
    row.observation_ar = str(contract.get("observation_ar") or "")
    row.diagnosis_ar = str(contract.get("diagnosis_ar") or "")
    row.recommendation_ar = str(contract.get("recommendation_ar") or "")
    row.contract_json = contract_json
    row.publication_json = publication_json
    row.content_hash = ch
    row.diagnostic_version = str(contract.get("diagnostic_version") or "")
    row.generated_at = generated
    row.expires_at = expires
    row.status = "active"
    row.updated_at = _utc_naive()
    # First successful write seeds last-good.
    if not row.last_good_contract_json:
        row.last_good_contract_json = contract_json
        row.last_good_generated_at = generated
    db.session.commit()
    return {"ok": True, "mode": mode, "diagnostic_id": row.diagnostic_id}


def read_diagnostic_snapshots_for_store_v1(
    store_slug: str,
    *,
    allow_expired_last_good: bool = True,
) -> list[dict[str, Any]]:
    """Read ready publications for a store (Home hot path — no compose)."""
    from extensions import db
    from models import DiagnosticSnapshot
    from schema_diagnostic_reasoning_v1 import ensure_diagnostic_reasoning_schema

    slug = (store_slug or "").strip()
    if not slug:
        return []
    try:
        ensure_diagnostic_reasoning_schema(db)
    except Exception:  # noqa: BLE001
        pass
    try:
        rows = (
            db.session.query(DiagnosticSnapshot)
            .filter(DiagnosticSnapshot.store_slug == slug)
            .filter(DiagnosticSnapshot.status == "active")
            .order_by(DiagnosticSnapshot.generated_at.desc())
            .limit(12)
            .all()
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("diagnostic snapshot read failed: %s", exc)
        return []

    now = _utc_naive()
    out: list[dict[str, Any]] = []
    for row in rows:
        expired = bool(row.expires_at and row.expires_at < now)
        pub: dict[str, Any] = {}
        try:
            pub = json.loads(row.publication_json or "{}")
        except Exception:  # noqa: BLE001
            pub = {}
        if expired and allow_expired_last_good:
            # Serve last-good contract publication with honest freshness.
            try:
                last = json.loads(row.last_good_contract_json or "{}")
                if last:
                    pub = publish_diagnostic_for_merchant_v1(last)
            except Exception:  # noqa: BLE001
                pass
            pub["freshness"] = "stale_last_good"
        elif expired:
            continue
        else:
            pub["freshness"] = "fresh"
        if not pub.get("diagnosis_ar"):
            pub.update(
                {
                    "diagnosis_ar": row.diagnosis_ar,
                    "recommendation_ar": row.recommendation_ar,
                    "observation_ar": row.observation_ar,
                    "diagnosis_status": row.diagnosis_status,
                    "diagnostic_family": row.diagnostic_family,
                    "diagnostic_id": row.diagnostic_id,
                }
            )
        out.append(pub)
    return out


def read_primary_diagnostic_publication_v1(
    store_slug: str,
) -> Optional[dict[str, Any]]:
    from services.diagnostic_reasoning_v1.publish_v1 import (
        pick_primary_diagnostic_publication_v1,
    )

    return pick_primary_diagnostic_publication_v1(
        read_diagnostic_snapshots_for_store_v1(store_slug)
    )


__all__ = [
    "read_diagnostic_snapshots_for_store_v1",
    "read_primary_diagnostic_publication_v1",
    "upsert_diagnostic_snapshot_v1",
]
