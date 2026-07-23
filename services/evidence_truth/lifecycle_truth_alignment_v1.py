# -*- coding: utf-8 -*-
"""
Lifecycle Truth Contract alignment helpers — WP-ET-06 / C-12.

Maps recovery timeline statuses → Frozen v1 contract states.
Does not drive recovery execution or purchase stop.
"""
from __future__ import annotations

from typing import Any, Optional

# Lifecycle Truth Contract (Frozen v1) canonical states
CONTRACT_WAITING_SEND = "waiting_send"
CONTRACT_SENT = "sent"
CONTRACT_RETURNED = "returned"
CONTRACT_REPLIED = "replied"
CONTRACT_PURCHASED = "purchased"
CONTRACT_IGNORED = "ignored"
CONTRACT_WAITING_NEXT = "waiting_next"
CONTRACT_COMPLETED = "completed"
CONTRACT_ARCHIVED = "archived"
CONTRACT_UNKNOWN = "unknown"

LIFECYCLE_CONTRACT_STATES_V1: frozenset[str] = frozenset(
    {
        CONTRACT_WAITING_SEND,
        CONTRACT_SENT,
        CONTRACT_RETURNED,
        CONTRACT_REPLIED,
        CONTRACT_PURCHASED,
        CONTRACT_IGNORED,
        CONTRACT_WAITING_NEXT,
        CONTRACT_COMPLETED,
        CONTRACT_ARCHIVED,
        CONTRACT_UNKNOWN,
    }
)

# Timeline statuses (recovery_truth_timeline_v1)
TIMELINE_SCHEDULED = "scheduled"
TIMELINE_DELAY_STARTED = "delay_started"
TIMELINE_BEFORE_SEND = "before_send"
TIMELINE_PROVIDER_QUEUED = "provider_queued"
TIMELINE_PROVIDER_SENT = "provider_sent"
TIMELINE_WEBHOOK_DELIVERED = "webhook_delivered"
TIMELINE_CUSTOMER_REPLY = "customer_reply"
TIMELINE_CONTINUATION_STARTED = "continuation_started"

_WAITING_SEND_TIMELINE = frozenset(
    {
        TIMELINE_SCHEDULED,
        TIMELINE_DELAY_STARTED,
        TIMELINE_BEFORE_SEND,
        TIMELINE_PROVIDER_QUEUED,
    }
)


def map_timeline_status_to_contract_state_v1(timeline_status: str) -> str:
    """
    Map a durable timeline status to a Lifecycle Truth Contract state.

    Rules (Contract §2 / §4):
    - waiting_send until provider_sent proven
    - sent requires provider_sent (webhook_delivered does not invent replied)
    - replied requires customer_reply (continuation is replied + flag)
    - Never invent purchased from timeline alone
    """
    st = (timeline_status or "").strip().lower()
    if st in _WAITING_SEND_TIMELINE:
        return CONTRACT_WAITING_SEND
    if st in {TIMELINE_PROVIDER_SENT, TIMELINE_WEBHOOK_DELIVERED}:
        return CONTRACT_SENT
    if st == TIMELINE_CUSTOMER_REPLY:
        return CONTRACT_REPLIED
    if st == TIMELINE_CONTINUATION_STARTED:
        return CONTRACT_REPLIED
    return CONTRACT_UNKNOWN


def provider_sent_proven_from_timeline_status_v1(timeline_status: str) -> bool:
    st = (timeline_status or "").strip().lower()
    return st in {
        TIMELINE_PROVIDER_SENT,
        TIMELINE_WEBHOOK_DELIVERED,
        TIMELINE_CUSTOMER_REPLY,
        TIMELINE_CONTINUATION_STARTED,
    }


def customer_reply_proven_from_timeline_status_v1(timeline_status: str) -> bool:
    st = (timeline_status or "").strip().lower()
    return st in {TIMELINE_CUSTOMER_REPLY, TIMELINE_CONTINUATION_STARTED}


def delivery_signal_from_timeline_status_v1(timeline_status: str) -> bool:
    """Webhook delivery is a signal — not equivalent to contract replied."""
    return (timeline_status or "").strip().lower() == TIMELINE_WEBHOOK_DELIVERED


def assert_lifecycle_alignment_invariants_v1(
    *,
    timeline_status: str,
    contract_state: str,
    sent_claimed: bool,
    replied_claimed: bool,
    purchased_claimed: bool,
) -> list[str]:
    """
    Return list of violated Lifecycle Truth Contract invariants (empty = ok).

    Covers F2/F3-class defects for Evidence payload claims.
    """
    violations: list[str] = []
    st = (timeline_status or "").strip().lower()
    cs = (contract_state or "").strip().lower()

    if sent_claimed and not provider_sent_proven_from_timeline_status_v1(st):
        violations.append("F3_sent_without_provider_sent")
    if replied_claimed and not customer_reply_proven_from_timeline_status_v1(st):
        violations.append("F2_replied_without_customer_reply")
    if purchased_claimed:
        # Timeline alone must never invent purchased (purchase family owns it)
        violations.append("purchased_invented_from_timeline")
    if cs == CONTRACT_SENT and st in _WAITING_SEND_TIMELINE:
        violations.append("sent_state_without_send_proof")
    if cs == CONTRACT_REPLIED and st not in {
        TIMELINE_CUSTOMER_REPLY,
        TIMELINE_CONTINUATION_STARTED,
    }:
        violations.append("replied_state_without_reply_proof")
    if cs == CONTRACT_WAITING_SEND and provider_sent_proven_from_timeline_status_v1(st):
        violations.append("F7_waiting_send_after_provider_sent")
    return violations


def build_recovery_lifecycle_payload_v1(
    *,
    timeline_status: str,
    recovery_key: str,
    observation_type: str = "",
    raw_kind: str = "",
) -> dict[str, Any]:
    """Facts-only Recovery Evidence payload aligned to Lifecycle Truth Contract."""
    st = (timeline_status or "").strip().lower()
    contract_state = map_timeline_status_to_contract_state_v1(st)
    sent_claimed = provider_sent_proven_from_timeline_status_v1(st)
    replied_claimed = customer_reply_proven_from_timeline_status_v1(st)
    delivery_signal = delivery_signal_from_timeline_status_v1(st)
    continuation = st == TIMELINE_CONTINUATION_STARTED
    payload = {
        "timeline_status": st,
        "contract_state": contract_state,
        "sent_claimed": bool(sent_claimed),
        "replied_claimed": bool(replied_claimed),
        "delivered_claimed": False,  # delivery ≠ replied; Communication owns delivery
        "delivery_signal": bool(delivery_signal),
        "continuation_started": bool(continuation),
        "purchased_claimed": False,
        "must_not_weaken_purchase_stop": True,
        "production_stop_authority": "purchase_truth_legacy",
        "recovery_key": recovery_key,
        "observation_type": observation_type,
        "raw_kind": raw_kind,
        "sent_equals_delivered": False,
        "returned_equals_replied": False,
    }
    violations = assert_lifecycle_alignment_invariants_v1(
        timeline_status=st,
        contract_state=contract_state,
        sent_claimed=sent_claimed,
        replied_claimed=replied_claimed,
        purchased_claimed=False,
    )
    payload["alignment_violations"] = list(violations)
    payload["lifecycle_aligned"] = len(violations) == 0
    return payload
