# -*- coding: utf-8 -*-
"""
Layer B — إعدادات CartFlow المعزولة (بدون ربط بلوحة التحكم أو DB بعد).
"""


def get_cartflow_config(store_slug=None):
    base_config = {
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

    # store-based override (hard-coded demo only)
    store_configs = {
        "demo": {
            "recovery_delay_minutes": 2,
        },
        "fast_store": {
            "recovery_delay_minutes": 0,
        },
    }

    if store_slug and store_slug in store_configs:
        base_config.update(store_configs[store_slug])

    return base_config
