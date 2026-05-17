# -*- coding: utf-8 -*-
"""Part 4 — verification when issues clear (in-process state, read-only)."""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

from services.admin_operational_control.context import OperationalControlContext

_MAX_RECOVERIES = 30
_lock = threading.Lock()
_prev_active_codes: set[str] = set()
_recoveries: deque[dict[str, Any]] = deque(maxlen=_MAX_RECOVERIES)

_ISSUE_LABELS_AR: dict[str, str] = {
    "cart_event_slow": "أداء cart-event",
    "db_pool_timeout": "مسبح قاعدة البيانات",
    "background_task_failure": "المهام الخلفية",
    "whatsapp_failure": "واتساب",
    "provider_instability": "المزود",
    "recovery_runtime_down": "مسار الاسترداد",
    "runtime_degraded": "ثقة التشغيل",
}


def clear_verification_state_for_tests() -> None:
    global _prev_active_codes
    with _lock:
        _prev_active_codes = set()
        _recoveries.clear()


def _minutes_ago_ar(iso_ts: str) -> str:
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ts
        mins = int(delta.total_seconds() // 60)
        if mins < 1:
            return "الآن"
        if mins < 60:
            return f"قبل {mins} دقيقة"
        hrs = mins // 60
        return f"قبل {hrs} ساعة"
    except Exception:
        return "—"


def _update_recovery_state(active_codes: set[str]) -> None:
    global _prev_active_codes
    with _lock:
        cleared = _prev_active_codes - active_codes
        now = datetime.now(timezone.utc).isoformat()
        for code in sorted(cleared):
            label = _ISSUE_LABELS_AR.get(code, code)
            _recoveries.appendleft(
                {
                    "code": code,
                    "recovered_at_utc": now,
                    "recovered_ago_ar": _minutes_ago_ar(now),
                    "message_ar": f"تمت استعادة {label} للوضع الطبيعي",
                    "checkmark": True,
                }
            )
        _prev_active_codes = set(active_codes)


def build_admin_verification_layer(ctx: OperationalControlContext) -> dict[str, Any]:
    active_codes = {i.code for i in ctx.issues if i.active}
    _update_recovery_state(active_codes)

    with _lock:
        recent = list(_recoveries)[:10]

    items = [
        {
            **r,
            "headline_ar": "✓ عاد الأداء للوضع الطبيعي",
            "timestamp_ar": r.get("recovered_ago_ar") or "—",
        }
        for r in recent
    ]

    return {
        "has_recoveries": bool(items),
        "items": items,
        "empty_message_ar": "لا استعادات حديثة — راقب المؤشرات عند زوال التحذير",
    }
