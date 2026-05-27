# -*- coding: utf-8 -*-
"""حفظ ‎reason‎ الاعتراض عند طلبات جمع الرقم فقط (‎vip_phone_capture‎) دون استبداله."""
from __future__ import annotations

from typing import Final, Optional

# قيمة مسار الويدجت/الـ API القديم — ليست سبب تردد حقيقي للاستمرار أو العروض.
PHONE_CAPTURE_REASON_VALUES: Final[frozenset[str]] = frozenset({"vip_phone_capture"})

# «أحتاج مساعدة الآن» — تسليم للتاجر فقط؛ لا يستبدل سبب الاعتراض ولا يُجدول استرجاع جديد.
HANDOFF_ONLY_REASON_VALUES: Final[frozenset[str]] = frozenset({"human_support"})

NON_RECOVERY_REASON_VALUES: Final[frozenset[str]] = (
    PHONE_CAPTURE_REASON_VALUES | HANDOFF_ONLY_REASON_VALUES
)


def effective_cart_recovery_reason_row_value(
    *,
    incoming_reason: str,
    existing_reason: Optional[str],
) -> str:
    """
    إن كان الطلب «جمع رقم فقط» أو «تسليم مساعدة» وهناك سبب اعتراض سابق غير ذلك، نُبقي السابق.
    وإلا نُخزّن القيمة الواردة (مُطبّعة).
    """
    inc = (incoming_reason or "").strip().lower()
    prev = (existing_reason or "").strip().lower()
    if inc in NON_RECOVERY_REASON_VALUES and prev and prev not in NON_RECOVERY_REASON_VALUES:
        return prev[:64]
    return inc[:64]


def is_handoff_only_reason(reason: str) -> bool:
    return (reason or "").strip().lower() in HANDOFF_ONLY_REASON_VALUES
