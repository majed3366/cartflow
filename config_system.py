# -*- coding: utf-8 -*-
"""
Layer B — إعدادات CartFlow المعزولة (بدون ربط بلوحة التحكم أو DB بعد).
"""


def get_cartflow_config(store_slug=None):
    _ = store_slug
    return {
        "recovery_delay_minutes": 1,
        "max_recovery_attempts": 2,
        "enabled_recovery_reasons": [
            "price",
            "hesitation",
            "warranty",
            "shipping",
            "quality",
            "other",
        ],
        "default_language": "ar",
        "whatsapp_recovery_enabled": True,
        "widget_recovery_enabled": True,
    }
