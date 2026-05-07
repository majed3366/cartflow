# -*- coding: utf-8 -*-
"""Behavioral recovery — react to customer actions without replacing core send/VIP flows."""
from __future__ import annotations

from services.behavioral_recovery.inbound_whatsapp import (
    process_inbound_behavioral_recovery,
)
from services.behavioral_recovery.link_tracking import (
    apply_outbound_tracking_to_message,
    handle_recovery_link_click,
)
from services.behavioral_recovery.message_strategy import (
    resolve_behavioral_followup_message,
)
from services.behavioral_recovery.state_store import (
    behavioral_dict_for_abandoned_cart,
    merge_behavioral_state,
)
from services.behavioral_recovery.user_return import (
    record_behavioral_user_return_from_payload,
)

__all__ = [
    "apply_outbound_tracking_to_message",
    "behavioral_dict_for_abandoned_cart",
    "handle_recovery_link_click",
    "merge_behavioral_state",
    "process_inbound_behavioral_recovery",
    "record_behavioral_user_return_from_payload",
    "resolve_behavioral_followup_message",
]
