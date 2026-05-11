# -*- coding: utf-8 -*-
"""إعدادات عرض التاجر لمسار الاسترجاع العادي — نوافذ زمنية وتمكين أرشفة «خامل»."""
from __future__ import annotations

import os
from typing import Any


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return int(default)
    try:
        v = int(raw)
        return v if v >= 0 else int(default)
    except (TypeError, ValueError):
        return int(default)


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return bool(default)
    return raw in ("1", "true", "yes", "on")


def normal_recovery_merchant_stale_config() -> dict[str, Any]:
    """
    قيم آمنة عند الغياب:
    - ‎active_sent_window_minutes‎: بعدها تُعتبر سلّة «أُرسلت» خاملَة بلا تفاعل.
    - ‎active_pending_window_minutes‎: بعدها تُعتبر «بانتظار الإرسال» خاملَة.
    - ‎stale_archive_enabled‎: تفعيل نقل الخامل إلى السجل (عرض فقط).
    """
    return {
        "active_sent_window_minutes": _env_int(
            "CARTFLOW_ACTIVE_SENT_WINDOW_MINUTES", 2880
        ),
        "active_pending_window_minutes": _env_int(
            "CARTFLOW_ACTIVE_PENDING_WINDOW_MINUTES", 4320
        ),
        "stale_archive_enabled": _env_bool("CARTFLOW_STALE_ARCHIVE_ENABLED", True),
    }
