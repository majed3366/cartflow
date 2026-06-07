# -*- coding: utf-8 -*-
"""تنبيه واتساب للتاجر فقط عند تفعيل VIP — بدون تغيير مسار رسائل العميل."""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

log = logging.getLogger("cartflow")

VIP_MERCHANT_ALERT_REASON_TAG = "vip_merchant_alert"
VIP_PHONE_CAPTURE_MERCHANT_REASON_TAG = "vip_phone_capture_merchant"

_VIP_REASON_AR = {
    "price": "السعر",
    "warranty": "الضمان",
    "shipping": "الشحن",
    "thinking": "التفكير",
    "quality": "الجودة",
    "other": "سبب آخر",
    "human_support": "دعم بشري",
}


def vip_dashboard_review_link() -> str:
    """
    رابط صفحة السلال المميزة في لوحة CartFlow للتاجر.
    يُفضّل ضبط ‎CARTFLOW_PUBLIC_BASE_URL‎ أو ‎PUBLIC_BASE_URL‎ على الخادم لرابط مطلق.
    """
    base = (
        os.getenv("CARTFLOW_PUBLIC_BASE_URL") or os.getenv("PUBLIC_BASE_URL") or ""
    ).strip().rstrip("/")
    if base:
        return f"{base}/dashboard/vip-cart-settings"
    return "https://smartreplyai.net/dashboard/vip-cart-settings"


def _digits_only(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def resolve_merchant_whatsapp_phone_with_default_env(store: Any) -> Tuple[Optional[str], str]:
    """
    مثل ‎resolve_merchant_whatsapp_phone‎ ثم ‎DEFAULT_MERCHANT_PHONE‎ (اختبار/احتياطي).
    """
    p, src = resolve_merchant_whatsapp_phone(store)
    if p:
        return p, src
    env_phone = (os.getenv("DEFAULT_MERCHANT_PHONE") or "").strip()
    if env_phone:
        d = _digits_only(env_phone)
        if len(d) >= 8:
            return env_phone[:64], "default_merchant_phone_env"
    return None, src


def _store_slug_from_row(store: Any) -> str:
    if store is None:
        return ""
    return (
        str(getattr(store, "zid_store_id", None) or getattr(store, "store_slug", None) or "")
        .strip()[:255]
    )


def emit_vip_merchant_alert_truth_log(
    *,
    store_slug: str = "",
    store_id: Any = None,
    cart_id: str = "",
    session_id: str = "",
    merchant_phone: str = "",
    phone_source: str = "",
    vip_threshold: Any = None,
    vip_notify_enabled: Any = None,
    alert_decision: str = "",
    send_attempted: Any = None,
    provider_result: Any = None,
    final_status: str = "",
    message_body: str = "",
    message_hash: str = "",
) -> None:
    import hashlib

    def _h(s: str) -> str:
        return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:16]

    mh = message_hash or _h(message_body) or _h(str(provider_result or ""))
    line = (
        "[VIP MERCHANT ALERT TRUTH] "
        f"store_slug={store_slug or '-'} "
        f"store_id={store_id if store_id is not None else '-'} "
        f"cart_id={cart_id or '-'} "
        f"session_id={session_id or '-'} "
        f"merchant_phone={merchant_phone or '-'} "
        f"phone_source={phone_source or '-'} "
        f"vip_threshold={vip_threshold if vip_threshold is not None else '-'} "
        f"vip_notify_enabled={vip_notify_enabled if vip_notify_enabled is not None else '-'} "
        f"alert_decision={alert_decision or '-'} "
        f"send_attempted={send_attempted if send_attempted is not None else '-'} "
        f"provider_result={str(provider_result or '-')[:120]} "
        f"final_status={final_status or '-'} "
        f"message_hash={mh}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.info("%s", line)


def normalize_vip_alert_phone(raw: str) -> Tuple[Optional[str], str]:
    """Normalize merchant destination to digits-only E.164-ish for Twilio."""
    d = _digits_only(raw or "")
    if len(d) < 8:
        return None, ""
    return d[:64], d


def resolve_vip_alert_destination(store: Any) -> Tuple[Optional[str], str, str]:
    """
    Resolve VIP merchant alert destination (priority order):
    1. ``store_whatsapp_number`` (merchant WhatsApp)
    2. ``whatsapp_support_url`` (merchant support WhatsApp)
    3. ``CARTFLOW_VIP_ALERT_DESTINATION`` env (ops override / fallback)
    Returns ``(phone_for_twilio, source, normalized_digits)``.
    """
    if store is None:
        env_only = (os.getenv("CARTFLOW_VIP_ALERT_DESTINATION") or "").strip()
        if env_only:
            norm, digits = normalize_vip_alert_phone(env_only)
            if norm:
                return norm, "cartflow_vip_alert_destination_env", digits
        return None, "no_store", ""

    raw_num = getattr(store, "store_whatsapp_number", None)
    if isinstance(raw_num, str) and raw_num.strip():
        norm, digits = normalize_vip_alert_phone(raw_num.strip())
        if norm:
            return norm[:64], "store_whatsapp_number", digits

    url = getattr(store, "whatsapp_support_url", None)
    if isinstance(url, str) and url.strip():
        u = url.strip()
        low = u.lower()
        try:
            p = urlparse(u)
            host = (p.netloc or "").lower()
            path = p.path or ""
            if "wa.me" in host or host == "wa.me":
                seg = path.strip("/").split("/")[0] if path else ""
                norm, digits = normalize_vip_alert_phone(seg)
                if norm:
                    return norm, "whatsapp_support_url_wa_me", digits
            if "api.whatsapp.com" in host:
                qs = parse_qs(p.query or "")
                ph = (qs.get("phone") or [""])[0]
                norm, digits = normalize_vip_alert_phone(str(ph))
                if norm:
                    return norm, "whatsapp_support_url_api", digits
            m = re.search(r"(?:wa\.me/|phone=)(\d{8,15})", low)
            if m:
                norm, digits = normalize_vip_alert_phone(m.group(1))
                if norm:
                    return norm, "whatsapp_support_url_regex", digits
        except Exception:  # noqa: BLE001
            pass

    env_dest = (os.getenv("CARTFLOW_VIP_ALERT_DESTINATION") or "").strip()
    if env_dest:
        norm, digits = normalize_vip_alert_phone(env_dest)
        if norm:
            return norm[:64], "cartflow_vip_alert_destination_env", digits

    return None, "no_merchant_contact", ""


def resolve_merchant_whatsapp_phone(store: Any) -> Tuple[Optional[str], str]:
    """
    يُرجع ‎(رقم لـ Twilio ‎whatsapp:+…‎, مصدر)‎ أو ‎(None, reason)‎.
    يُفضّل ‎store_whatsapp_number‎ ثم استخراج من ‎whatsapp_support_url‎ ثم ‎CARTFLOW_VIP_ALERT_DESTINATION‎.
    """
    phone, src, _digits = resolve_vip_alert_destination(store)
    if phone:
        return phone, src
    if store is None:
        return None, "no_store"
    return None, src or "no_merchant_contact"


def build_vip_merchant_alert_body(
    cart_total: float,
    *,
    reason_tag: Optional[str] = None,
    dashboard_link: Optional[str] = None,
) -> str:
    if cart_total == int(cart_total):
        v = str(int(cart_total))
    else:
        v = f"{cart_total:.2f}".rstrip("0").rstrip(".")
    link = (dashboard_link or "").strip() or vip_dashboard_review_link()
    lines: list[str] = [
        "تنبيه VIP 🚨",
        "",
        f"سلة عالية القيمة: {v} ريال",
        "",
    ]
    rt = (reason_tag or "").strip()
    if rt:
        ar = _VIP_REASON_AR.get(rt.lower(), rt)
        lines.extend([f"السبب: {ar}", ""])
    lines.extend(["رابط المراجعة:", link])
    return "\n".join(lines)


def _format_cart_total_display(cart_total: float) -> str:
    if cart_total == int(cart_total):
        return str(int(cart_total))
    return f"{cart_total:.2f}".rstrip("0").rstrip(".")


def build_vip_phone_capture_merchant_message(
    cart_total: float,
    customer_phone_e164: str,
) -> str:
    v = _format_cart_total_display(cart_total)
    ph = (customer_phone_e164 or "").strip()
    lines = [
        "🔥 سلة مميزة تحتاج متابعة",
        "",
        f"عميل أضاف سلة بقيمة {v} ريال",
        "",
        "رقم العميل:",
        ph,
        "",
        "اضغط للتواصل معه مباشرة",
    ]
    body = "\n".join(lines)
    d = _digits_only(ph)
    if len(d) >= 8:
        body = f"{body}\n\nhttps://wa.me/{d}"
    return body


def try_send_vip_phone_capture_merchant_alert(
    store: Any,
    *,
    cart_total: float,
    customer_phone: str,
) -> Dict[str, Any]:
    """
    تنبيه فوري للتاجر عند حفظ رقم من ‎vip_phone_capture‎ — نفس ‎send_whatsapp‎ (Twilio).
    """
    from services.whatsapp_send import send_whatsapp

    phone, src = resolve_merchant_whatsapp_phone_with_default_env(store)
    log.info(
        "[VIP ALERT SENDING] merchant_to=%s source=%s cart_total=%s",
        phone or "none",
        src,
        cart_total,
    )
    try:
        print(
            "[VIP ALERT SENDING]\n"
            "merchant_to=" + (phone or "none") + "\n"
            "source=" + str(src),
            flush=True,
        )
    except OSError:
        pass
    if not phone:
        log.warning(
            "[VIP ALERT FAILED] reason=no_merchant_phone source=%s",
            src,
        )
        return {"ok": False, "error": "no_merchant_phone", "source": src}
    msg = build_vip_phone_capture_merchant_message(cart_total, customer_phone)
    ss = _store_slug_from_row(store)
    try:
        out = send_whatsapp(
            phone,
            msg,
            reason_tag=VIP_PHONE_CAPTURE_MERCHANT_REASON_TAG,
            wa_trace_path=__file__,
            wa_trace_session_id=None,
            wa_trace_store_slug=ss or None,
            wa_trace_last_activity=None,
            wa_trace_recovery_delay_minutes=None,
            wa_trace_delay_passed=None,
        )
    except Exception as e:  # noqa: BLE001
        log.warning(
            "[VIP ALERT FAILED] reason=exception err=%s",
            str(e),
            exc_info=True,
        )
        return {"ok": False, "error": str(e)}
    ok = isinstance(out, dict) and out.get("ok") is True
    if ok:
        log.info("[VIP ALERT SENT]")
        try:
            print("[VIP ALERT SENT]", flush=True)
        except OSError:
            pass
    else:
        detail = ""
        if isinstance(out, dict):
            detail = str(out.get("error") or "")[:256]
        log.warning("[VIP ALERT FAILED] reason=send_failed detail=%s", detail or "unknown")
    return out if isinstance(out, dict) else {"ok": False, "error": "invalid_result"}


def try_send_vip_merchant_whatsapp_alert(
    store: Any,
    *,
    message: str,
    session_id: str = "",
    cart_id: str = "",
) -> Dict[str, Any]:
    """
    إرسال نص للتاجر عبر ‎send_whatsapp‎ (Twilio) إن وُجد رقم صالح.
    لا يستخدم ‎wa_trace_session_id‎ حتى لا يُحجب بسبب ‎user_rejected_help‎ للعميل.
    يُ polling حالة Twilio بعد القبول — القبول وحده ليس نجاحاً تشغيلياً.
    """
    from services.vip_operational_truth_v1 import (
        poll_twilio_vip_alert_delivery_truth,
        vip_alert_delivery_summary,
    )
    from services.whatsapp_send import send_whatsapp

    phone, src, normalized = resolve_vip_alert_destination(store)
    ss = _store_slug_from_row(store)
    log.info(
        "[VIP MERCHANT ALERT ATTEMPT] to=%s normalized=%s source=%s store=%s",
        phone or "none",
        normalized or "-",
        src,
        ss or "-",
    )
    if not phone:
        log.warning("[VIP MERCHANT ALERT FAILED] reason=no_merchant_phone source=%s", src)
        return {"ok": False, "error": "no_merchant_phone", "source": src}
    try:
        out = send_whatsapp(
            phone,
            message,
            reason_tag=VIP_MERCHANT_ALERT_REASON_TAG,
            wa_trace_path=__file__,
            wa_trace_session_id=None,
            wa_trace_store_slug=ss or None,
            wa_trace_last_activity=None,
            wa_trace_recovery_delay_minutes=None,
            wa_trace_delay_passed=None,
        )
    except Exception as e:  # noqa: BLE001
        log.warning(
            "[VIP MERCHANT ALERT FAILED] reason=exception err=%s",
            str(e),
            exc_info=True,
        )
        return {"ok": False, "error": str(e), "phone_source": src, "normalized_phone": normalized}
    ok = isinstance(out, dict) and out.get("ok") is True
    if ok:
        sid = str(out.get("sid") or "").strip()
        out["phone_source"] = src
        out["normalized_phone"] = normalized
        out["destination_type"] = src
        if sid:
            truth = poll_twilio_vip_alert_delivery_truth(
                sid,
                customer_phone=normalized or phone,
                store_slug=ss,
                session_id=(session_id or "")[:512],
                cart_id=(cart_id or "")[:255],
            )
            summary = vip_alert_delivery_summary(truth)
            out["delivery_truth"] = summary
            out["delivery_truth_level"] = summary.get("truth_level")
            out["delivered_to_device"] = summary.get("delivered_to_device")
            log.info(
                "[VIP MERCHANT ALERT SENT] sid=%s truth=%s delivered=%s",
                sid,
                summary.get("truth_level"),
                summary.get("delivered_to_device"),
            )
        else:
            log.info("[VIP MERCHANT ALERT SENT] mock path")
    else:
        detail = ""
        if isinstance(out, dict):
            detail = str(out.get("error") or "")[:256]
        log.warning("[VIP MERCHANT ALERT FAILED] reason=send_failed detail=%s", detail or "unknown")
    if isinstance(out, dict):
        out.setdefault("phone_source", src)
        out.setdefault("normalized_phone", normalized)
    return out if isinstance(out, dict) else {"ok": False, "error": "invalid_result"}
