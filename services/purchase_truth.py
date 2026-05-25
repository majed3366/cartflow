# -*- coding: utf-8 -*-
"""
Purchase Truth v2 — canonical ingest + evidence-based lifecycle closure (facade).

All verified purchase paths call ``ingest_purchase_truth``.
Reply PURCHASE claims use ``ingest_purchase_truth_from_reply_claim`` (lower confidence).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from services.cartflow_purchase_truth import (
    extract_purchase_evidence as extract_purchase_truth_evidence,
    has_purchase,
    record_purchase,
)

log = logging.getLogger("cartflow")

_REPLY_STRONG_PHRASES = frozenset(
    {
        "تم الطلب",
        "تم الشراء",
        "اكملت الطلب",
        "أكملت الطلب",
        "تم الدفع",
        "order done",
        "purchased",
    }
)


def _emit_block(tag: str, **fields: Any) -> None:
    lines = [f"[{tag}]"]
    for k, v in fields.items():
        if v is None:
            continue
        lines.append(f"{k}={str(v)[:220]}")
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def log_purchase_truth(
    *,
    source: str,
    recovery_key: str,
    session_id: str = "",
    cart_id: str = "",
    evidence: str = "",
    verified: bool = True,
) -> None:
    block = "\n".join(
        [
            "[PURCHASE TRUTH]",
            f"source={(source or 'unknown')[:64]}",
            f"verified={'true' if verified else 'false'}",
            f"session_id={(session_id or '-')[:80]}",
            f"cart_id={(cart_id or '-')[:64]}",
            f"recovery_key={(recovery_key or '-')[:120]}",
        ]
        + ([f"evidence={evidence[:120]}"] if evidence else [])
    )
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def ingest_purchase_truth(
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
    Canonical purchase ingest — durable row + recovery stop + optional lifecycle.

    Emits ``[PURCHASE TRUTH INGESTED]`` with ``truth_written=``.
    """
    rk = (recovery_key or "").strip()
    source = (purchase_source or "").strip()
    if not rk or not source:
        _emit_block(
            "PURCHASE TRUTH INGESTED",
            source=source or "-",
            recovery_key=rk or "-",
            order=order_id or "-",
            store=store_slug or "-",
            truth_written="false",
            reason="missing_key_or_source",
        )
        return False

    already = has_purchase(rk)
    truth_written = record_purchase(
        recovery_key=rk,
        purchase_source=source,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        order_id=order_id,
        customer_phone=customer_phone,
        evidence_detail=evidence_detail,
        purchase_time=purchase_time,
        context_payload=context_payload,
        apply_lifecycle=False,
    )

    _emit_block(
        "PURCHASE TRUTH INGESTED",
        source=source,
        recovery_key=rk,
        order=order_id or "-",
        store=store_slug or "-",
        truth_written="true" if truth_written else "false",
        first_record="false" if already else "true",
    )

    if truth_written:
        from services.lifecycle_closure_records_v1 import (
            CLOSURE_PURCHASE_COMPLETED,
            record_lifecycle_closure,
        )

        record_lifecycle_closure(
            rk,
            closure_status=CLOSURE_PURCHASE_COMPLETED,
            closure_reason="purchase_truth_verified",
            closure_source=f"purchase_truth:{source}",
            closure_time=purchase_time,
            store_slug=store_slug,
            session_id=session_id,
            cart_id=str(cart_id or ""),
        )
        if apply_lifecycle:
            apply_purchase_truth_lifecycle_closure(
                rk,
                session_id=session_id,
                cart_id=cart_id or "",
                source=source,
                evidence=evidence_detail,
                context_payload=context_payload,
            )

    return truth_written


def ingest_purchase_truth_from_reply_claim(
    *,
    recovery_key: str,
    store_slug: str,
    session_id: str,
    cart_id: str = "",
    reply_preview: str = "",
    confidence: str = "low",
    ac: Any = None,
) -> bool:
    """
    Durable low/medium-confidence purchase from customer reply (not order_paid).

    Emits ``[PURCHASE TRUTH FROM REPLY]``.
    """
    rk = (recovery_key or "").strip()
    conf = (confidence or "low").strip().lower()
    if conf not in ("low", "medium"):
        conf = "low"
    if not rk:
        _emit_block(
            "PURCHASE TRUTH FROM REPLY",
            confidence=conf,
            truth_written="false",
            reason="empty_recovery_key",
        )
        return False

    preview = (reply_preview or "").strip()[:200]
    detail = f"reply_claim;confidence={conf}"
    if preview:
        detail += f";preview={preview[:120]}"

    truth_written = ingest_purchase_truth(
        recovery_key=rk,
        purchase_source="reply_purchase_claim",
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id or None,
        evidence_detail=detail,
        apply_lifecycle=True,
    )

    _emit_block(
        "PURCHASE TRUTH FROM REPLY",
        confidence=conf,
        truth_written="true" if truth_written else "false",
        recovery_key=rk,
    )

    return truth_written


def reply_purchase_confidence(reply: str) -> str:
    """Classify reply PURCHASE claim strength (not equal to order_paid)."""
    raw = (reply or "").strip()
    if not raw:
        return "low"
    norm = raw.lower()
    for phrase in _REPLY_STRONG_PHRASES:
        pn = phrase.lower()
        if norm == pn or (len(pn) > 3 and pn in norm):
            return "medium"
    return "low"


def apply_purchase_truth_lifecycle_closure(
    recovery_key: str,
    *,
    session_id: str = "",
    cart_id: str = "",
    source: str,
    evidence: str = "",
    ac: Any = None,
    context_payload: Optional[dict[str, Any]] = None,
) -> None:
    """Emit ``[PURCHASE TRUTH]`` then terminal ``[PURCHASE LIFECYCLE CLOSED]``."""
    from services.purchase_lifecycle_closure import record_purchase_lifecycle_closure

    rk = (recovery_key or "").strip()
    if not rk:
        return

    verified = (source or "").strip() != "reply_purchase_claim"
    log_purchase_truth(
        source=source,
        recovery_key=rk,
        session_id=session_id,
        cart_id=cart_id,
        evidence=evidence,
        verified=verified,
    )
    record_purchase_lifecycle_closure(
        rk,
        session_id=session_id,
        cart_id=cart_id,
        reason="purchase_truth_verified",
        source=f"purchase_truth:{source}",
        ac=ac,
        mark_converted=True,
    )
    if verified:
        try:
            from services.purchase_attribution_v1 import run_purchase_attribution_after_truth_closure

            run_purchase_attribution_after_truth_closure(
                rk,
                session_id=session_id,
                cart_id=cart_id,
                ac=ac,
                context_payload=context_payload,
                purchase_truth_source=source,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "purchase attribution hook failed (closure complete): %s",
                exc,
                exc_info=True,
            )


def ingest_purchase_truth_payload(payload: dict[str, Any]) -> Optional[str]:
    """
    Verify purchase evidence, persist durable truth via canonical ingest.

    Returns ``recovery_key`` when evidence was applied; ``None`` if no evidence.
    """
    extracted = extract_purchase_truth_evidence(payload)
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
    platform_src = str(payload.get("purchase_source") or "").strip()
    ingest_source = platform_src or source

    written = ingest_purchase_truth(
        recovery_key=rk,
        purchase_source=ingest_source,
        store_slug=store_slug,
        session_id=_session_part_from_payload(payload),
        cart_id=_cart_id_str_from_payload(payload),
        order_id=order_id,
        customer_phone=phone,
        evidence_detail=detail,
        context_payload=payload,
        apply_lifecycle=True,
    )
    return rk if written else None


__all__ = [
    "apply_purchase_truth_lifecycle_closure",
    "extract_purchase_truth_evidence",
    "ingest_purchase_truth",
    "ingest_purchase_truth_from_reply_claim",
    "ingest_purchase_truth_payload",
    "log_purchase_truth",
    "reply_purchase_confidence",
]
