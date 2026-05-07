# -*- coding: utf-8 -*-
"""رسائل المتابعة الذكية للاسترجاع العادي — نصوص مختصرة غير مكررة للرسالة الأولى."""
from __future__ import annotations

from typing import Any, Optional

from services.recovery_message_strategy import get_recovery_message


def resolve_smart_second_recovery_message(
    first_message_body: str,
    reason_tag: Optional[str],
    store: Any,
) -> str:
    """
    رسالة المحاولة الثانية — نبرة طمأنة عبر طبقة الاسترجاع السلوكي الموحدة.
    """
    _ = (first_message_body, store)
    return get_recovery_message(reason_tag, 2, store)
