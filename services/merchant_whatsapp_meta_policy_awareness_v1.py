# -*- coding: utf-8 -*-
"""Meta policy awareness — calm merchant guidance (no Meta terminology)."""
from __future__ import annotations

from typing import Any

META_POLICY_GUIDANCE_AR: tuple[str, ...] = (
    "للحفاظ على جودة التواصل مع العملاء، تفرض CartFlow حدوداً دنيا بين مراحل المتابعة.",
)

TIMING_POLICY_EXPLANATION_AR = META_POLICY_GUIDANCE_AR[0]

TIMING_AUTO_ADJUST_MESSAGE_AR = TIMING_POLICY_EXPLANATION_AR


def meta_policy_guidance_for_merchant_api() -> dict[str, Any]:
    return {
        "meta_policy_awareness_architecture_only": True,
        "meta_technical_terms_hidden": True,
        "guidance_lines_ar": list(META_POLICY_GUIDANCE_AR),
        "timing_auto_adjust_message_ar": TIMING_AUTO_ADJUST_MESSAGE_AR,
    }
