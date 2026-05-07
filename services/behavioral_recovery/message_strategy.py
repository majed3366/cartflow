# -*- coding: utf-8 -*-
"""يتصل بطبقة ‎recovery_message_strategy‎ لعدم تكرار النصوص بين المحاولات."""
from __future__ import annotations

from typing import Any, Optional

from services.recovery_message_strategy import get_recovery_message


def resolve_behavioral_followup_message(
    *,
    step_num: int,
    first_message_body: str,
    second_message_body: str,
    reason_tag: Optional[str],
    store: Any,
) -> str:
    """محاولة 2+ — نبرة مختلفة عن المحاولة الأولى عبر get_recovery_message."""
    _ = (first_message_body, second_message_body, store)
    return get_recovery_message(reason_tag, int(step_num))
