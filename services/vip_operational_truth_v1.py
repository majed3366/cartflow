# -*- coding: utf-8 -*-
"""
VIP operational truth v1 — merchant alerts isolated from customer recovery lane.

Merchant-only WhatsApp alerts must never increment customer sent_count,
recovery_attempts, follow-up progress, or lifecycle customer-send signals.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

log = logging.getLogger("cartflow")

VIP_MERCHANT_ALERT_REASON_TAGS = frozenset(
    {
        "vip_merchant_alert",
        "vip_phone_capture_merchant",
    }
)

VIP_MERCHANT_ALERT_LOG_STATUSES = frozenset(
    {
        "vip_merchant_alert_accepted",
        "vip_merchant_alert_delivered",
        "vip_merchant_alert_failed",
        "vip_merchant_alert_skipped",
        "vip_merchant_alert_mock",
    }
)

_CUSTOMER_RECOVERY_SENT_LOG_STATUSES = frozenset({"sent_real", "mock_sent"})


def is_vip_merchant_only_recovery_log(log: Any) -> bool:
    """True when log row is a merchant VIP alert — not customer recovery."""
    rt = (getattr(log, "reason_tag", None) or "").strip().lower()
    return rt in VIP_MERCHANT_ALERT_REASON_TAGS


def vip_merchant_alert_reason_tag_sql_exclusion() -> Any:
    """SQLAlchemy filter: exclude merchant-only VIP alert reason tags."""
    from sqlalchemy import or_

    from models import CartRecoveryLog

    return or_(
        CartRecoveryLog.reason_tag.is_(None),
        CartRecoveryLog.reason_tag == "",
        ~CartRecoveryLog.reason_tag.in_(tuple(VIP_MERCHANT_ALERT_REASON_TAGS)),
    )


def count_customer_recovery_sends(matched_logs: Any) -> int:
    """Count customer recovery sends — excludes merchant VIP alert logs."""
    n = 0
    for lg in matched_logs or ():
        if is_vip_merchant_only_recovery_log(lg):
            continue
        st = str((getattr(lg, "status", None) or "")).strip().lower()
        if st in _CUSTOMER_RECOVERY_SENT_LOG_STATUSES:
            n += 1
    return n


def resolve_vip_merchant_alert_log_status(
    wa_result: Any,
    *,
    delivery_truth: Any = None,
) -> str:
    """
    CartRecoveryLog.status for VIP merchant alerts — never ``sent_real``.
    """
    if not isinstance(wa_result, dict) or wa_result.get("ok") is not True:
        return "vip_merchant_alert_failed"
    try:
        from services.whatsapp_delivery_truth_v1 import (
            TRUTH_DELIVERED,
            TRUTH_FAILED,
            TRUTH_READ,
        )

        if delivery_truth is not None:
            level = str(getattr(delivery_truth, "truth_level", "") or "").strip()
            if level == TRUTH_FAILED:
                return "vip_merchant_alert_failed"
            if level in (TRUTH_DELIVERED, TRUTH_READ):
                return "vip_merchant_alert_delivered"
        dt_level = str(wa_result.get("delivery_truth_level") or "").strip()
        if dt_level == TRUTH_FAILED:
            return "vip_merchant_alert_failed"
        if dt_level in (TRUTH_DELIVERED, TRUTH_READ):
            return "vip_merchant_alert_delivered"
        if wa_result.get("delivered_to_device") is True:
            return "vip_merchant_alert_delivered"
    except Exception:  # noqa: BLE001
        pass
    sid = str(wa_result.get("sid") or "").strip()
    if sid:
        return "vip_merchant_alert_accepted"
    return "vip_merchant_alert_mock"


def poll_twilio_vip_alert_delivery_truth(
    message_sid: str,
    *,
    customer_phone: str = "",
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    max_wait_seconds: float = 30.0,
    poll_interval_seconds: float = 2.0,
) -> Any:
    """
    Poll Twilio message status until delivered/read/failed/timeout.
    Persists delivery truth rows; does not affect customer recovery lane.
    """
    from services.whatsapp_delivery_truth_v1 import (
        TRUTH_DELIVERED,
        TRUTH_FAILED,
        TRUTH_READ,
        DeliveryTruth,
        get_delivery_truth,
        normalize_twilio_message_status,
        persist_delivery_truth,
        resolve_truth_without_callback,
        truth_level_rank,
    )

    sid = (message_sid or "").strip()
    if not sid:
        return DeliveryTruth(
            truth_level="unknown",
            reason="missing_message_sid",
        )

    account_sid = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
    auth_token = (os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
    if not account_sid or not auth_token:
        return resolve_truth_without_callback(sid)

    try:
        from services.whatsapp_send import build_twilio_client
    except Exception:  # noqa: BLE001
        return resolve_truth_without_callback(sid)

    deadline = time.monotonic() + max(1.0, float(max_wait_seconds))
    best: Optional[Any] = get_delivery_truth(sid)
    last_status = ""

    while time.monotonic() < deadline:
        try:
            client = build_twilio_client(account_sid, auth_token)
            msg = client.messages(sid).fetch()
            tw_status = str(getattr(msg, "status", "") or "").strip()
            last_status = tw_status
            level = normalize_twilio_message_status(tw_status)
            truth = DeliveryTruth(
                provider="twilio",
                message_sid=sid,
                customer_phone=customer_phone,
                store_slug=store_slug,
                session_id=session_id,
                cart_id=cart_id,
                send_status=tw_status,
                delivery_status=tw_status,
                truth_level=level,
                reason="vip_merchant_alert_poll",
            )
            best = persist_delivery_truth(truth, event_payload={"source": "vip_poll"})
            if truth_level_rank(level) >= truth_level_rank(TRUTH_DELIVERED):
                log.info(
                    "[VIP MERCHANT ALERT DELIVERY] sid=%s status=%s truth=%s",
                    sid,
                    tw_status,
                    level,
                )
                return best
            if level == TRUTH_FAILED:
                log.warning(
                    "[VIP MERCHANT ALERT DELIVERY FAILED] sid=%s status=%s",
                    sid,
                    tw_status,
                )
                return best
        except Exception as exc:  # noqa: BLE001
            log.debug("vip alert delivery poll failed sid=%s err=%s", sid, exc)
        time.sleep(max(0.5, float(poll_interval_seconds)))

    if best is not None:
        best.reason = f"poll_timeout_last_status={last_status or 'unknown'}"
        return best
    truth = resolve_truth_without_callback(sid)
    truth.reason = f"poll_timeout_no_record_last_status={last_status or 'unknown'}"
    return truth


def vip_alert_delivery_summary(truth: Any) -> dict[str, Any]:
    """Compact delivery truth for dev/audit endpoints."""
    if truth is None:
        return {
            "truth_level": "unknown",
            "delivered_to_device": False,
            "delivery_status": "",
            "message_sid": "",
        }
    level = str(getattr(truth, "truth_level", "") or "unknown")
    try:
        from services.whatsapp_delivery_truth_v1 import (
            TRUTH_DELIVERED,
            TRUTH_FAILED,
            TRUTH_READ,
        )

        delivered = level in (TRUTH_DELIVERED, TRUTH_READ)
        failed = level == TRUTH_FAILED
    except Exception:  # noqa: BLE001
        delivered = level in ("delivered_to_customer", "read_by_customer")
        failed = level == "failed_delivery"
    return {
        "truth_level": level,
        "delivered_to_device": bool(delivered and not failed),
        "delivery_status": str(getattr(truth, "delivery_status", "") or ""),
        "send_status": str(getattr(truth, "send_status", "") or ""),
        "message_sid": str(getattr(truth, "message_sid", "") or ""),
        "provider_error": str(getattr(truth, "provider_error", "") or ""),
        "reason": str(getattr(truth, "reason", "") or ""),
    }
