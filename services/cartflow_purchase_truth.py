# -*- coding: utf-8 -*-
"""
Purchase Truth foundation v1 — durable evidence + recovery stop precedence.

Precedence (lifecycle): purchase > reply > return_to_site > delay > send

Additive only: does not change decision engine, widget, WhatsApp send, or onboarding.
Provider webhooks are not wired here — dev/manual evidence ingestion only.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from extensions import db
from models import PurchaseTruthRecord
from schema_purchase_truth import ensure_purchase_truth_schema

log = logging.getLogger("cartflow")

_lock = threading.Lock()
_memory_records: dict[str, dict[str, Any]] = {}

_TRUTH_FLAG_KEYS: tuple[tuple[str, str], ...] = (
    ("purchase_completed", "purchase_completed"),
    ("order_paid", "order_paid"),
    ("checkout_completed", "checkout_completed"),
    ("order_created", "order_created"),
)

_TRUTH_EVENT_NAMES: frozenset[str] = frozenset(
    {
        "purchase_completed",
        "order_paid",
        "checkout_completed",
        "order_created",
        "order_completed",
        "purchase_event",
        "user_converted",
    }
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PurchaseEvidence:
    recovery_key: str
    purchase_detected: bool = True
    purchase_time: datetime = field(default_factory=_utc_now)
    purchase_source: str = ""
    order_id: Optional[str] = None
    store_slug: str = ""
    session_id: str = ""
    cart_id: Optional[str] = None
    customer_phone: Optional[str] = None
    evidence_detail: str = ""

    def to_context_dict(self) -> dict[str, Any]:
        d = asdict(self)
        pt = d.get("purchase_time")
        if isinstance(pt, datetime):
            d["purchase_time"] = pt.astimezone(timezone.utc).isoformat()
        return d


def reset_purchase_truth_foundation_for_tests() -> None:
    with _lock:
        _memory_records.clear()


def extract_purchase_evidence(payload: dict[str, Any]) -> Optional[tuple[str, str]]:
    """Return ``(purchase_source, evidence_detail)`` when payload has verified evidence."""
    if not isinstance(payload, dict):
        return None
    for key, source in _TRUTH_FLAG_KEYS:
        if payload.get(key) is True:
            return source, f"{key}=true"
    ev_raw = payload.get("event") or payload.get("purchase_event")
    ev = str(ev_raw or "").strip().lower()
    if ev in _TRUTH_EVENT_NAMES:
        return ev, f"event={ev}"
    if payload.get("user_converted") is True:
        return "user_converted", "user_converted=true"
    return None


def _log_block(tag: str, **fields: Any) -> None:
    parts = [f"[{tag}]"]
    for k, v in fields.items():
        if v is None:
            continue
        parts.append(f"{k}={str(v)[:200]}")
    block = " ".join(parts)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block)
    except Exception:  # noqa: BLE001
        pass


def _row_to_evidence(row: PurchaseTruthRecord) -> PurchaseEvidence:
    return PurchaseEvidence(
        recovery_key=(row.recovery_key or "").strip(),
        purchase_detected=bool(row.purchase_detected),
        purchase_time=row.purchase_time or row.created_at or _utc_now(),
        purchase_source=(row.purchase_source or "").strip(),
        order_id=(row.order_id or "").strip() or None,
        store_slug=(row.store_slug or "").strip(),
        session_id=(row.session_id or "").strip(),
        cart_id=(row.cart_id or "").strip() or None,
        customer_phone=(row.customer_phone or "").strip() or None,
        evidence_detail=(row.evidence_detail or "").strip(),
    )


def _persist_durable_record(evidence: PurchaseEvidence) -> None:
    ensure_purchase_truth_schema(db)
    rk = evidence.recovery_key
    try:
        row = (
            db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.recovery_key == rk)
            .first()
        )
        if row is None:
            row = PurchaseTruthRecord(
                recovery_key=rk,
                purchase_detected=True,
                purchase_time=evidence.purchase_time,
                purchase_source=evidence.purchase_source[:128],
                order_id=(evidence.order_id or "")[:255] or None,
                store_slug=evidence.store_slug[:255],
                session_id=evidence.session_id[:512],
                cart_id=(evidence.cart_id or "")[:255] or None,
                customer_phone=(evidence.customer_phone or "")[:100] or None,
                evidence_detail=(evidence.evidence_detail or "")[:512] or None,
            )
            db.session.add(row)
        else:
            row.purchase_detected = True
            row.purchase_time = evidence.purchase_time
            row.purchase_source = evidence.purchase_source[:128]
            row.order_id = (evidence.order_id or "")[:255] or None
            row.store_slug = evidence.store_slug[:255]
            row.session_id = evidence.session_id[:512]
            row.cart_id = (evidence.cart_id or "")[:255] or None
            row.customer_phone = (evidence.customer_phone or "")[:100] or None
            row.evidence_detail = (evidence.evidence_detail or "")[:512] or None
        db.session.commit()
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        log.warning("purchase truth durable persist failed: %s", exc)


def _memory_put(evidence: PurchaseEvidence) -> None:
    with _lock:
        _memory_records[evidence.recovery_key] = evidence.to_context_dict()


def has_purchase(recovery_key: str) -> bool:
    rk = (recovery_key or "").strip()
    if not rk:
        return False
    with _lock:
        if rk in _memory_records:
            return True
    try:
        ensure_purchase_truth_schema(db)
        row = (
            db.session.query(PurchaseTruthRecord.id)
            .filter(
                PurchaseTruthRecord.recovery_key == rk,
                PurchaseTruthRecord.purchase_detected.is_(True),
            )
            .first()
        )
        return row is not None
    except Exception:  # noqa: BLE001
        return False


def purchase_context(recovery_key: str) -> Optional[dict[str, Any]]:
    rk = (recovery_key or "").strip()
    if not rk:
        return None
    with _lock:
        mem = _memory_records.get(rk)
        if mem:
            return dict(mem)
    try:
        ensure_purchase_truth_schema(db)
        row = (
            db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.recovery_key == rk)
            .first()
        )
        if row is None or not row.purchase_detected:
            return None
        return _row_to_evidence(row).to_context_dict()
    except Exception:  # noqa: BLE001
        return None


def _mark_session_converted(recovery_key: str) -> None:
    try:
        from main import _recovery_session_lock, _session_recovery_converted  # noqa: PLC0415

        with _recovery_session_lock:
            _session_recovery_converted[recovery_key] = True
    except Exception as exc:  # noqa: BLE001
        log.warning("purchase truth: session converted flag failed: %s", exc)


def _cancel_pending_recovery(recovery_key: str) -> int:
    from services.recovery_restart_survival import (  # noqa: PLC0415
        cancel_durable_schedules_for_purchase,
    )

    return cancel_durable_schedules_for_purchase(
        recovery_key, detail="purchase_truth_stop"
    )


def _apply_lifecycle_closure(
    evidence: PurchaseEvidence,
    *,
    context_payload: Optional[dict[str, Any]] = None,
) -> None:
    from services.purchase_truth import apply_purchase_truth_lifecycle_closure

    apply_purchase_truth_lifecycle_closure(
        evidence.recovery_key,
        session_id=evidence.session_id,
        cart_id=evidence.cart_id or "",
        source=evidence.purchase_source,
        evidence=evidence.evidence_detail,
        context_payload=context_payload,
    )


def stop_if_purchased(
    recovery_key: str,
    *,
    session_id: str = "",
    cart_id: str = "",
) -> bool:
    """
    If purchase truth exists, stop recovery (cancel durable schedules + block).

    Returns True when recovery must not proceed.
    """
    rk = (recovery_key or "").strip()
    if not rk or not has_purchase(rk):
        return False

    cancelled = _cancel_pending_recovery(rk)
    _mark_session_converted(rk)
    _log_block(
        "PURCHASE STOP",
        recovery_key=rk,
        session_id=session_id or "-",
        cart_id=cart_id or "-",
        schedules_cancelled=cancelled,
    )

    try:
        from services.purchase_lifecycle_closure import (
            is_purchase_lifecycle_closed,
            record_purchase_lifecycle_closure,
        )

        if not is_purchase_lifecycle_closed(rk):
            ctx = purchase_context(rk) or {}
            record_purchase_lifecycle_closure(
                rk,
                session_id=session_id or ctx.get("session_id") or "",
                cart_id=cart_id or ctx.get("cart_id") or "",
                reason="purchase_detected",
                source=f"purchase_truth:{ctx.get('purchase_source', 'durable')}",
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("purchase truth lifecycle sync on stop: %s", exc)

    return True


def record_purchase(
    *,
    recovery_key: str,
    purchase_source: str,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str] = None,
    order_id: Optional[str] = None,
    customer_phone: Optional[str] = None,
    evidence_detail: str = "",
    purchase_time: Optional[datetime] = None,
    context_payload: Optional[dict[str, Any]] = None,
    apply_lifecycle: bool = True,
) -> bool:
    """
    Record verified purchase evidence and stop future recovery.

    Returns False when recovery_key or source is missing (no fake purchases).
    """
    rk = (recovery_key or "").strip()
    source = (purchase_source or "").strip()
    if not rk or not source:
        return False

    already = has_purchase(rk)
    pt = purchase_time or _utc_now()
    evidence = PurchaseEvidence(
        recovery_key=rk,
        purchase_detected=True,
        purchase_time=pt,
        purchase_source=source,
        order_id=(order_id or "").strip() or None,
        store_slug=(store_slug or "").strip(),
        session_id=(session_id or "").strip(),
        cart_id=(cart_id or "").strip() or None,
        customer_phone=(customer_phone or "").strip() or None,
        evidence_detail=(evidence_detail or "").strip(),
    )

    if not already:
        _log_block(
            "PURCHASE DETECTED",
            recovery_key=rk,
            store_slug=evidence.store_slug,
            session_id=evidence.session_id,
            cart_id=evidence.cart_id or "-",
            order_id=evidence.order_id or "-",
        )
        _log_block(
            "PURCHASE SOURCE",
            source=source,
            evidence=evidence.evidence_detail or "-",
        )

    _memory_put(evidence)
    _persist_durable_record(evidence)

    if apply_lifecycle:
        try:
            from services.purchase_lifecycle_closure import is_purchase_lifecycle_closed

            if not is_purchase_lifecycle_closed(rk):
                _apply_lifecycle_closure(evidence, context_payload=context_payload)
        except Exception:  # noqa: BLE001
            if not already:
                _apply_lifecycle_closure(evidence, context_payload=context_payload)

    _mark_session_converted(rk)
    cancelled = _cancel_pending_recovery(rk)
    _log_block(
        "PURCHASE STOP",
        recovery_key=rk,
        schedules_cancelled=cancelled,
        first_record=not already,
    )

    return True


def record_purchase_from_payload(payload: dict[str, Any]) -> Optional[str]:
    """
    Ingest a dict-shaped evidence payload (dev/conversion/future webhooks).

    Returns recovery_key when recorded; None when no evidence or key.
    """
    extracted = extract_purchase_evidence(payload)
    if not extracted:
        return None

    source, detail = extracted
    try:
        from main import (  # noqa: PLC0415
            _cart_id_str_from_payload,
            _recovery_key_from_payload,
            _session_part_from_payload,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("purchase truth payload: main import failed: %s", exc)
        return None

    rk = _recovery_key_from_payload(payload)
    if not rk:
        return None

    store_slug = (
        str(payload.get("store_slug") or payload.get("store") or "").strip()
        or rk.split(":", 1)[0]
    )
    phone = (
        str(
            payload.get("customer_phone")
            or payload.get("phone")
            or payload.get("store_whatsapp_number")
            or ""
        ).strip()
        or None
    )
    order_id = str(payload.get("order_id") or payload.get("zid_order_id") or "").strip() or None

    record_purchase(
        recovery_key=rk,
        purchase_source=source,
        store_slug=store_slug,
        session_id=_session_part_from_payload(payload),
        cart_id=_cart_id_str_from_payload(payload),
        order_id=order_id,
        customer_phone=phone,
        evidence_detail=detail,
        context_payload=payload,
    )
    return rk


__all__ = [
    "PurchaseEvidence",
    "extract_purchase_evidence",
    "has_purchase",
    "purchase_context",
    "record_purchase",
    "record_purchase_from_payload",
    "reset_purchase_truth_foundation_for_tests",
    "stop_if_purchased",
]
