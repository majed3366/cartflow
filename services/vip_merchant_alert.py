# -*- coding: utf-8 -*-
"""تنبيه واتساب للتاجر فقط عند تفعيل VIP — بدون تغيير مسار رسائل العميل."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

log = logging.getLogger("cartflow")


def _digits_only(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def resolve_merchant_whatsapp_phone(store: Any) -> Tuple[Optional[str], str]:
    """
    يُرجع ‎(رقم لـ Twilio ‎whatsapp:+…‎, مصدر)‎ أو ‎(None, reason)‎.
    يُفضّل ‎store_whatsapp_number‎ ثم استخراج من ‎whatsapp_support_url‎ (‎wa.me‎ / ‎api.whatsapp.com‎).
    """
    if store is None:
        return None, "no_store"
    raw_num = getattr(store, "store_whatsapp_number", None)
    if isinstance(raw_num, str) and raw_num.strip():
        d = _digits_only(raw_num)
        if len(d) >= 8:
            return raw_num.strip()[:64], "store_whatsapp_number"
    url = getattr(store, "whatsapp_support_url", None)
    if not isinstance(url, str) or not url.strip():
        return None, "no_merchant_contact"
    u = url.strip()
    low = u.lower()
    try:
        p = urlparse(u)
        host = (p.netloc or "").lower()
        path = p.path or ""
        if "wa.me" in host or host == "wa.me":
            seg = path.strip("/").split("/")[0] if path else ""
            d = _digits_only(seg)
            if len(d) >= 8:
                return d, "whatsapp_support_url_wa_me"
        if "api.whatsapp.com" in host:
            qs = parse_qs(p.query or "")
            ph = (qs.get("phone") or [""])[0]
            d = _digits_only(str(ph))
            if len(d) >= 8:
                return d, "whatsapp_support_url_api"
        m = re.search(r"(?:wa\.me/|phone=)(\d{8,15})", low)
        if m:
            return m.group(1), "whatsapp_support_url_regex"
    except Exception:  # noqa: BLE001
        pass
    return None, "url_unparsed"


def build_vip_merchant_alert_body(cart_total: float) -> str:
    if cart_total == int(cart_total):
        v = str(int(cart_total))
    else:
        v = f"{cart_total:.2f}".rstrip("0").rstrip(".")
    return f"تنبيه VIP: سلة عالية القيمة ({v} ريال) تحتاج متابعة"


def try_send_vip_merchant_whatsapp_alert(
    store: Any,
    *,
    message: str,
) -> Dict[str, Any]:
    """
    إرسال نص للتاجر عبر ‎send_whatsapp‎ (Twilio) إن وُجد رقم صالح.
    لا يستخدم ‎wa_trace_session_id‎ حتى لا يُحجب بسبب ‎user_rejected_help‎ للعميل.
    """
    from services.whatsapp_send import send_whatsapp

    phone, src = resolve_merchant_whatsapp_phone(store)
    if not phone:
        log.info("[VIP MERCHANT ALERT SENT] status=no_target source=%s", src)
        return {"ok": False, "error": "no_merchant_phone", "source": src}
    try:
        out = send_whatsapp(
            phone,
            message,
            reason_tag="vip_merchant_alert",
            wa_trace_path=__file__,
            wa_trace_session_id=None,
            wa_trace_store_slug=None,
            wa_trace_last_activity=None,
            wa_trace_recovery_delay_minutes=None,
            wa_trace_delay_passed=None,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("VIP merchant alert send exception: %s", e, exc_info=True)
        log.info("[VIP MERCHANT ALERT SENT] status=exception err=%s", str(e)[:200])
        return {"ok": False, "error": str(e)}
    ok = isinstance(out, dict) and out.get("ok") is True
    sid = str((out or {}).get("sid") or "").strip() if isinstance(out, dict) else ""
    st = "sent" if ok else "twilio_error"
    log.info("[VIP MERCHANT ALERT SENT] status=%s ok=%s sid=%s", st, ok, sid or "none")
    return out if isinstance(out, dict) else {"ok": False, "error": "invalid_result"}
