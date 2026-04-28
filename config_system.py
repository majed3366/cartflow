# -*- coding: utf-8 -*-
"""
Layer B — إعدادات CartFlow المعزولة (بدون ربط بلوحة التحكم بعد).
السلوك الافتراضي يطابق التشغيل الحالي؛ لاحقاً يمكن تمرير المتجر لتجاوز القيم من الـ Dashboard.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

# قيم افتراضية ثابتة؛ لا تُقرأ من DB في هذه الطبقة
DEFAULT_RECOVERY_DELAY_MINUTES: int = 1
DEFAULT_MAX_RECOVERY_ATTEMPTS: int = 3
DEFAULT_LANGUAGE: str = "ar"
DEFAULT_WHATSAPP_RECOVERY_ENABLED: bool = True
DEFAULT_WIDGET_RECOVERY_ENABLED: bool = True

_DEFAULT_ENABLED_RECOVERY_REASONS: List[str] = [
    "price",
    "hesitation",
    "warranty",
    "shipping",
    "quality",
    "other",
]


def _default_config_dict() -> Dict[str, Any]:
    return {
        "recovery_delay_minutes": DEFAULT_RECOVERY_DELAY_MINUTES,
        "max_recovery_attempts": DEFAULT_MAX_RECOVERY_ATTEMPTS,
        "enabled_recovery_reasons": list(_DEFAULT_ENABLED_RECOVERY_REASONS),
        "default_language": DEFAULT_LANGUAGE,
        "whatsapp_recovery_enabled": DEFAULT_WHATSAPP_RECOVERY_ENABLED,
        "widget_recovery_enabled": DEFAULT_WIDGET_RECOVERY_ENABLED,
    }


def get_cartflow_config(store: Optional[Any] = None) -> Dict[str, Any]:
    """
    إرجاع إعدادات CartFlow.
    - بدون store: القيم الافتراضية الآمنة.
    - مع store: نفس الافتراضيات حالياً (تجاوزات لاحقاً من الـ Dashboard).
    """
    _ = store
    return deepcopy(_default_config_dict())
