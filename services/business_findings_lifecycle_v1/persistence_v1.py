# -*- coding: utf-8 -*-
"""Persist / load durable Business Findings."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import BusinessFinding
from schema_business_findings_lifecycle_v1 import ensure_business_findings_lifecycle_schema
from services.business_findings_lifecycle_v1.types_v1 import BFL_VERSION_V1

log = logging.getLogger("cartflow")


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dumps(obj: Any) -> str:
    return json.dumps(obj if obj is not None else {}, ensure_ascii=False, default=str)


def _loads(raw: Any, default: Any) -> Any:
    if raw is None or raw == "":
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        return default


def row_to_record(row: BusinessFinding) -> dict[str, Any]:
    return {
        "finding_id": row.finding_id,
        "finding_type": row.finding_type,
        "store_slug": row.store_slug,
        "merchant_id": row.merchant_id,
        "product_id": row.product_id,
        "category_id": row.category_id,
        "evidence": _loads(row.evidence_json, {}),
        "confidence": row.confidence,
        "confidence_score": row.confidence_score,
        "severity": row.severity,
        "generated_at": row.generated_at.isoformat(sep=" ") if row.generated_at else None,
        "expires_at": row.expires_at.isoformat(sep=" ") if row.expires_at else None,
        "lifecycle_state": row.lifecycle_state,
        "visibility_state": row.visibility_state,
        "reasoning": _loads(row.reasoning_json, {}),
        "recommended_action": row.recommended_action,
        "title": row.title,
        "merchant_summary": row.merchant_summary,
        "payload": _loads(row.payload_json, {}),
        "routing": _loads(row.routing_json, {}),
        "lifecycle_events": _loads(row.lifecycle_events_json, []),
        "diagnostics": _loads(row.diagnostics_json, {}),
        "fingerprint": row.fingerprint,
        "engine_version": row.engine_version,
        "lifecycle_version": row.lifecycle_version,
        "is_current": bool(row.is_current),
        "as_of": row.as_of.isoformat(sep=" ") if row.as_of else None,
        "as_of_key": row.as_of_key,
        "created_at": row.created_at.isoformat(sep=" ") if row.created_at else None,
        "refreshed_at": row.refreshed_at.isoformat(sep=" ") if row.refreshed_at else None,
    }


def upsert_finding_record_v1(record: dict[str, Any]) -> dict[str, Any]:
    """Insert or refresh a current finding row. Caller advances lifecycle."""
    ensure_business_findings_lifecycle_schema(db)
    fid = str(record.get("finding_id") or "")[:128]
    if not fid:
        return {"ok": False, "error": "finding_id_required"}
    now = _utc_naive_now()
    try:
        existing = (
            db.session.query(BusinessFinding)
            .filter(BusinessFinding.finding_id == fid)
            .first()
        )
        fields = dict(
            finding_type=str(record.get("finding_type") or "")[:96],
            store_slug=str(record.get("store_slug") or "")[:255],
            merchant_id=str(record.get("merchant_id") or "")[:64],
            product_id=record.get("product_id"),
            category_id=record.get("category_id"),
            evidence_json=_dumps(record.get("evidence") or {}),
            confidence=str(record.get("confidence") or "")[:32],
            confidence_score=str(record.get("confidence_score") or "")[:32],
            severity=str(record.get("severity") or "")[:32],
            generated_at=record.get("generated_at") or now,
            expires_at=record.get("expires_at"),
            lifecycle_state=str(record.get("lifecycle_state") or "detected")[:48],
            visibility_state=str(record.get("visibility_state") or "hidden")[:32],
            reasoning_json=_dumps(record.get("reasoning") or {}),
            recommended_action=str(record.get("recommended_action") or ""),
            title=str(record.get("title") or ""),
            merchant_summary=str(record.get("merchant_summary") or ""),
            payload_json=_dumps(record.get("payload") or {}),
            routing_json=_dumps(record.get("routing") or {}),
            lifecycle_events_json=_dumps(record.get("lifecycle_events") or []),
            diagnostics_json=_dumps(record.get("diagnostics") or {}),
            fingerprint=str(record.get("fingerprint") or "")[:64],
            engine_version=str(record.get("engine_version") or "")[:64],
            lifecycle_version=str(record.get("lifecycle_version") or BFL_VERSION_V1)[:32],
            is_current=bool(record.get("is_current", True)),
            as_of=record.get("as_of") or now,
            as_of_key=str(record.get("as_of_key") or "")[:32],
            refreshed_at=now,
            superseded_at=None,
        )
        if isinstance(fields["generated_at"], str):
            fields["generated_at"] = datetime.fromisoformat(fields["generated_at"])
        if isinstance(fields["as_of"], str):
            fields["as_of"] = datetime.fromisoformat(fields["as_of"])
        if isinstance(fields.get("expires_at"), str) and fields["expires_at"]:
            fields["expires_at"] = datetime.fromisoformat(fields["expires_at"])

        if existing is None:
            db.session.add(
                BusinessFinding(finding_id=fid, created_at=now, **fields)
            )
        else:
            for k, v in fields.items():
                setattr(existing, k, v)
            if existing.created_at is None:
                existing.created_at = now
        db.session.commit()
        return {"ok": True, "finding_id": fid}
    except (SQLAlchemyError, ValueError, TypeError) as exc:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        log.warning("bfl upsert failed: %s", exc)
        return {"ok": False, "error": type(exc).__name__}


def load_current_findings_v1(
    store_slug: str,
    *,
    lifecycle_min: Optional[str] = None,
) -> list[dict[str, Any]]:
    ensure_business_findings_lifecycle_schema(db)
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return []
    try:
        q = db.session.query(BusinessFinding).filter(
            BusinessFinding.store_slug == slug,
            BusinessFinding.is_current.is_(True),
        )
        rows = q.order_by(BusinessFinding.refreshed_at.desc()).limit(200).all()
        out = [row_to_record(r) for r in rows]
        if lifecycle_min:
            from services.business_findings_lifecycle_v1.lifecycle_v1 import (
                lifecycle_index,
            )

            min_i = lifecycle_index(lifecycle_min)
            out = [r for r in out if lifecycle_index(r.get("lifecycle_state")) >= min_i]
        return out
    except SQLAlchemyError as exc:
        log.warning("bfl load failed: %s", exc)
        return []


def save_record_fields_v1(record: dict[str, Any]) -> dict[str, Any]:
    """Persist lifecycle/routing/diagnostics updates for an existing finding_id."""
    return upsert_finding_record_v1(record)


__all__ = [
    "row_to_record",
    "upsert_finding_record_v1",
    "load_current_findings_v1",
    "save_record_fields_v1",
]
