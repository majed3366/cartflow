# -*- coding: utf-8 -*-
"""Part 3 — suggested actions (read-only navigation)."""
from __future__ import annotations

from typing import Any

from services.admin_operational_control.context import OperationalControlContext


def build_admin_actions_layer(ctx: OperationalControlContext) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for issue in ctx.issues:
        if not issue.active:
            continue
        items.append(
            {
                "code": issue.code,
                "recommended_action_ar": issue.action_ar,
                "detail_href": issue.detail_href,
                "detail_label_ar": "فتح التفاصيل ←",
                "problem_ar": issue.problem_ar,
            }
        )
    return {
        "has_actions": bool(items),
        "items": items,
        "empty_message_ar": "لا إجراء مطلوب — استمر بالمراقبة الروتينية",
    }
