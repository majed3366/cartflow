# -*- coding: utf-8 -*-
"""
WhatsApp Delivery Truth v1 — provider acceptance ≠ customer delivery.

Additive foundation: records truth from Twilio status callbacks and optional
send-time acceptance. Does not change recovery, queue, attribution decisions,
or send return values.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("cartflow")

PROVIDER_TWILIO = "twilio"
PROVIDER_META = "meta"

TRUTH_ACCEPTED = "accepted_by_provider"
TRUTH_SENT = "sent_to_network"
TRUTH_DELIVERED = "delivered_to_customer"
TRUTH_READ = "read_by_customer"
TRUTH_FAILED = "failed_delivery"
TRUTH_UNKNOWN = "unknown"

# Higher rank = more definitive delivery truth (failed is terminal for non-read).
_TRUTH_RANK: dict[str, int] = {
    TRUTH_UNKNOWN: 10,
    TRUTH_ACCEPTED: 20,
    TRUTH_SENT: 30,
    TRUTH_DELIVERED: 40,
    TRUTH_READ: 50,
    TRUTH_FAILED: 45,
}


@dataclass
class DeliveryTruth:
    provider: str = ""
    message_sid: str = ""
    customer_phone: str = ""
    store_slug: str = ""
    session_id: str = ""
    cart_id: str = ""
    recovery_key: str = ""
    send_status: str = ""
    delivery_status: str = ""
    read_status: str = ""
    provider_error: str = ""
    last_event_time: Optional[datetime] = None
    truth_level: str = TRUTH_UNKNOWN
    reason: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.last_event_time is not None:
            d["last_event_time"] = self.last_event_time.isoformat()
        return d


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def normalize_twilio_message_status(status: Optional[str]) -> str:
    """Map Twilio MessageStatus to truth_level."""
    raw = (status or "").strip().lower()
    if raw in ("queued", "accepted", "receiving"):
        return TRUTH_ACCEPTED
    if raw in ("sending",):
        return TRUTH_SENT
    if raw == "sent":
        return TRUTH_SENT
    if raw == "delivered":
        return TRUTH_DELIVERED
    if raw == "read":
        return TRUTH_READ
    if raw in ("failed", "undelivered"):
        return TRUTH_FAILED
    return TRUTH_UNKNOWN


def normalize_provider_status(
    provider: str, status: Optional[str]
) -> str:
    p = (provider or "").strip().lower()
    if p in (PROVIDER_TWILIO, ""):
        return normalize_twilio_message_status(status)
    # Meta / future providers — conservative until wired
    return TRUTH_UNKNOWN


def truth_level_rank(level: str) -> int:
    return _TRUTH_RANK.get((level or "").strip(), 0)


def _should_advance_truth(current: str, new: str) -> bool:
    if new == TRUTH_FAILED:
        return current != TRUTH_READ
    return truth_level_rank(new) > truth_level_rank(current)


def _log_delivery_event(
    *,
    provider: str,
    message_sid: str,
    delivery_status: str,
    read_status: str = "",
    provider_error: str = "",
) -> None:
    line = (
        f"[WA DELIVERY EVENT] provider={provider} sid={message_sid} "
        f"delivery_status={delivery_status}"
    )
    if read_status:
        line += f" read_status={read_status}"
    if provider_error:
        line += f" provider_error={provider_error}"
    print(line)
    log.info("%s", line)


def _log_delivery_truth(truth: DeliveryTruth) -> None:
    reason = (truth.reason or truth.truth_level or TRUTH_UNKNOWN)[:256]
    line = (
        f"[WA DELIVERY TRUTH] truth_level={truth.truth_level} reason={reason}"
    )
    if truth.message_sid:
        line += f" sid={truth.message_sid}"
    print(line)
    log.info("%s", line)


def _ensure_schema() -> None:
    try:
        from extensions import db
        from schema_widget import ensure_whatsapp_delivery_truth_schema

        ensure_whatsapp_delivery_truth_schema(db)
    except Exception:  # noqa: BLE001
        pass


def _row_to_delivery_truth(row: Any) -> DeliveryTruth:
    return DeliveryTruth(
        provider=getattr(row, "provider", "") or "",
        message_sid=getattr(row, "message_sid", "") or "",
        customer_phone=getattr(row, "customer_phone", "") or "",
        store_slug=getattr(row, "store_slug", "") or "",
        session_id=getattr(row, "session_id", "") or "",
        cart_id=getattr(row, "cart_id", "") or "",
        recovery_key=getattr(row, "recovery_key", "") or "",
        send_status=getattr(row, "send_status", "") or "",
        delivery_status=getattr(row, "delivery_status", "") or "",
        read_status=getattr(row, "read_status", "") or "",
        provider_error=getattr(row, "provider_error", "") or "",
        last_event_time=getattr(row, "last_event_time", None),
        truth_level=getattr(row, "truth_level", TRUTH_UNKNOWN) or TRUTH_UNKNOWN,
        reason="persisted",
    )


def get_delivery_truth(message_sid: str) -> Optional[DeliveryTruth]:
    """Read persisted truth; missing row → None (caller treats as unknown)."""
    sid = (message_sid or "").strip()
    if not sid:
        return None
    _ensure_schema()
    try:
        from extensions import db
        from models import WhatsAppDeliveryTruth

        db.create_all()
        row = (
            db.session.query(WhatsAppDeliveryTruth)
            .filter(WhatsAppDeliveryTruth.message_sid == sid[:128])
            .first()
        )
        if row is None:
            return None
        return _row_to_delivery_truth(row)
    except Exception as exc:  # noqa: BLE001
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass
        log.debug("get_delivery_truth failed: %s", exc)
        return None


def customer_delivered_for_attribution_future(message_sid: str) -> bool:
    """
    Future attribution hook — v1 returns False until delivered_to_customer+.
    Never treat queued / accepted_by_provider as delivery proof.
    """
    truth = get_delivery_truth(message_sid)
    if truth is None:
        return False
    return truth_level_rank(truth.truth_level) >= truth_level_rank(
        TRUTH_DELIVERED
    )


def persist_delivery_truth(
    truth: DeliveryTruth,
    *,
    event_payload: Optional[dict[str, Any]] = None,
) -> DeliveryTruth:
    """Idempotent upsert by message_sid; advances truth_level only when rank increases."""
    sid = (truth.message_sid or "").strip()[:128]
    if not sid:
        truth.reason = "missing_message_sid"
        _log_delivery_truth(truth)
        return truth

    _ensure_schema()
    from extensions import db
    from models import WhatsAppDeliveryTruth

    db.create_all()
    now = _utc_now()
    event_time = truth.last_event_time or now
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)

    try:
        row = (
            db.session.query(WhatsAppDeliveryTruth)
            .filter(WhatsAppDeliveryTruth.message_sid == sid)
            .first()
        )
        new_level = (truth.truth_level or TRUTH_UNKNOWN).strip()
        if row is None:
            row = WhatsAppDeliveryTruth(
                provider=(truth.provider or PROVIDER_TWILIO)[:32],
                message_sid=sid,
                customer_phone=(truth.customer_phone or "")[:100] or None,
                store_slug=(truth.store_slug or "")[:255] or None,
                session_id=(truth.session_id or "")[:512] or None,
                cart_id=(truth.cart_id or "")[:255] or None,
                recovery_key=(truth.recovery_key or "")[:512] or None,
                send_status=(truth.send_status or "")[:64] or None,
                delivery_status=(truth.delivery_status or "")[:64] or None,
                read_status=(truth.read_status or "")[:64] or None,
                provider_error=(truth.provider_error or "")[:512] or None,
                truth_level=new_level[:64],
                last_event_time=event_time,
                created_at=now,
                updated_at=now,
                raw_last_payload=(
                    json.dumps(event_payload, ensure_ascii=False)[:4000]
                    if event_payload
                    else None
                ),
            )
            db.session.add(row)
            truth.reason = truth.reason or "created"
        else:
            current = (row.truth_level or TRUTH_UNKNOWN).strip()
            if _should_advance_truth(current, new_level):
                row.truth_level = new_level[:64]
                truth.reason = truth.reason or f"advanced:{current}->{new_level}"
            else:
                truth.truth_level = current
                truth.reason = truth.reason or f"unchanged:{current}"
            if truth.provider and not row.provider:
                row.provider = truth.provider[:32]
            for attr, val, maxlen in (
                ("customer_phone", truth.customer_phone, 100),
                ("store_slug", truth.store_slug, 255),
                ("session_id", truth.session_id, 512),
                ("cart_id", truth.cart_id, 255),
                ("recovery_key", truth.recovery_key, 512),
            ):
                if val and not getattr(row, attr, None):
                    setattr(row, attr, val[:maxlen])
            if truth.send_status:
                row.send_status = truth.send_status[:64]
            if truth.delivery_status:
                row.delivery_status = truth.delivery_status[:64]
            if truth.read_status:
                row.read_status = truth.read_status[:64]
            if truth.provider_error:
                row.provider_error = truth.provider_error[:512]
            row.last_event_time = event_time
            row.updated_at = now
            if event_payload is not None:
                row.raw_last_payload = json.dumps(
                    event_payload, ensure_ascii=False
                )[:4000]
        db.session.commit()
        truth.last_event_time = event_time
        _log_delivery_truth(truth)
        try:
            from services.evidence_truth.observation_shadow_dual_write_v1 import (  # noqa: PLC0415
                maybe_shadow_communication_observation_v1,
            )

            _comm_payload = {
                "store_slug": truth.store_slug,
                "session_id": truth.session_id,
                "cart_id": truth.cart_id,
                "recovery_key": truth.recovery_key,
                "message_sid": truth.message_sid,
                "status": truth.delivery_status or truth.send_status,
            }
            obs_shadow = maybe_shadow_communication_observation_v1(
                _comm_payload,
                source="whatsapp_delivery_truth",
                provider=(truth.provider or ""),
            )
        except Exception:  # noqa: BLE001
            obs_shadow = None
            _comm_payload = {
                "store_slug": truth.store_slug,
                "session_id": truth.session_id,
                "cart_id": truth.cart_id,
                "recovery_key": truth.recovery_key,
                "message_sid": truth.message_sid,
                "status": truth.delivery_status or truth.send_status,
            }
        try:
            from services.evidence_truth.evidence_dual_write_v1 import (  # noqa: PLC0415
                maybe_publish_communication_evidence_v1,
            )

            oid = ""
            if isinstance(obs_shadow, dict):
                oid = str(obs_shadow.get("observation_id") or "")
            maybe_publish_communication_evidence_v1(
                _comm_payload,
                source="whatsapp_delivery_truth",
                provider=(truth.provider or ""),
                observation_id=oid,
            )
        except Exception:  # noqa: BLE001
            pass
        return truth
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        truth.reason = f"persist_error:{exc}"
        _log_delivery_truth(truth)
        log.warning("persist_delivery_truth failed: %s", exc)
        return truth


def record_provider_acceptance_from_send(
    *,
    provider: str,
    message_sid: str,
    send_status: str,
    customer_phone: str = "",
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    recovery_key: str = "",
) -> DeliveryTruth:
    """
    After Twilio messages.create — records accepted_by_provider only.
    Does not imply customer_received or delivered.
    """
    level = normalize_provider_status(provider, send_status)
    if not level or level == TRUTH_UNKNOWN:
        level = TRUTH_ACCEPTED
    truth = DeliveryTruth(
        provider=provider or PROVIDER_TWILIO,
        message_sid=message_sid,
        customer_phone=customer_phone,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        recovery_key=recovery_key,
        send_status=send_status,
        delivery_status=send_status,
        truth_level=level,
        last_event_time=_utc_now(),
        reason="provider_acceptance_from_send",
    )
    _log_delivery_event(
        provider=truth.provider,
        message_sid=message_sid,
        delivery_status=send_status,
    )
    return persist_delivery_truth(truth, event_payload={"source": "send"})


def ingest_twilio_status_callback(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize Twilio status webhook (form or JSON) → DeliveryTruth → persist.
    Does not invoke recovery, lifecycle, or queue workers.
    """
    sid = (
        payload.get("MessageSid")
        or payload.get("message_sid")
        or payload.get("SmsSid")
        or ""
    )
    sid = str(sid).strip()
    status = (
        payload.get("MessageStatus")
        or payload.get("message_status")
        or payload.get("status")
        or ""
    )
    status = str(status).strip()
    to_phone = str(
        payload.get("To") or payload.get("to") or payload.get("Recipient") or ""
    ).strip()
    error_code = str(
        payload.get("ErrorCode") or payload.get("error_code") or ""
    ).strip()
    error_message = str(
        payload.get("ErrorMessage") or payload.get("error_message") or ""
    ).strip()
    provider_error = ""
    if error_code or error_message:
        provider_error = f"{error_code}:{error_message}".strip(":")[:512]

    level = normalize_twilio_message_status(status)
    read_status = status if level == TRUTH_READ else ""
    delivery_status = status

    _log_delivery_event(
        provider=PROVIDER_TWILIO,
        message_sid=sid,
        delivery_status=delivery_status,
        read_status=read_status,
        provider_error=provider_error,
    )

    if not sid:
        truth = DeliveryTruth(
            provider=PROVIDER_TWILIO,
            truth_level=TRUTH_UNKNOWN,
            reason="missing_message_sid_in_callback",
        )
        _log_delivery_truth(truth)
        return {"ok": False, "error": "missing_message_sid", "truth": truth.to_dict()}

    existing = get_delivery_truth(sid)
    truth = DeliveryTruth(
        provider=PROVIDER_TWILIO,
        message_sid=sid,
        customer_phone=to_phone,
        store_slug=(existing.store_slug if existing else ""),
        session_id=(existing.session_id if existing else ""),
        cart_id=(existing.cart_id if existing else ""),
        recovery_key=(existing.recovery_key if existing else ""),
        send_status=(existing.send_status if existing else ""),
        delivery_status=delivery_status,
        read_status=read_status,
        provider_error=provider_error,
        truth_level=level,
        last_event_time=_utc_now(),
        reason="twilio_status_callback",
    )
    if level == TRUTH_READ:
        truth.read_status = status
    persist_delivery_truth(truth, event_payload=dict(payload))
    if level == TRUTH_DELIVERED and (truth.recovery_key or "").strip():
        try:
            from services.recovery_truth_timeline_v1 import (  # noqa: PLC0415
                STATUS_WEBHOOK_DELIVERED,
                record_recovery_truth_event,
            )

            record_recovery_truth_event(
                recovery_key=(truth.recovery_key or "").strip(),
                status=STATUS_WEBHOOK_DELIVERED,
                source="ingest_twilio_status_callback",
                store_slug=(truth.store_slug or "").strip(),
                session_id=(truth.session_id or "").strip(),
                cart_id=(truth.cart_id or "").strip(),
            )
        except Exception:  # noqa: BLE001
            pass
    return {"ok": True, "truth_level": truth.truth_level, "truth": truth.to_dict()}


def resolve_truth_without_callback(message_sid: str) -> DeliveryTruth:
    """
    When no status callback arrived: unknown if never recorded; else last persisted level
    (typically accepted_by_provider from send).
    """
    row_truth = get_delivery_truth(message_sid)
    if row_truth is not None:
        row_truth.reason = "no_callback_use_persisted"
        return row_truth
    return DeliveryTruth(
        message_sid=message_sid,
        truth_level=TRUTH_UNKNOWN,
        reason="no_callback_no_record",
    )
