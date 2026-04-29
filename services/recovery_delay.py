"""Reason-tag recovery delays (seconds). Defaults here; optional overrides via store_config.recovery_delays (dashboard-ready)."""


def get_recovery_delay(reason_tag, store_config=None):
    default_mapping = {
        "price_high": 300,
        "quality": 180,
        "shipping": 120,
        "delivery": 120,
        "warranty": 180,
        "other": 240,
    }
    key = (reason_tag or "").strip().lower()
    if store_config:
        custom_delays = store_config.get("recovery_delays", {})
        if key in custom_delays:
            return custom_delays[key]

    return default_mapping.get(key, 180)
