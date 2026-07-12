# -*- coding: utf-8 -*-
"""P3→merchant action commands — sole executor of approved Workspace actions."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from services.cart_workspace.contracts_v1 import _utc_now_iso
from services.cart_workspace.ownership_v1 import apply_transition
from services.cart_workspace.projection_v1 import ACTION_LABELS_AR, build_workspace_projection
from services.cart_workspace.shadow_store_v1 import ShadowStoreV1

# Engineering Spec Part 8 — implementable only (no OQ-deferred commands).
ALLOWED_COMMANDS = frozenset(
    {
        "approve_discount",
        "reject_exception",
        "provide_information",
        "fix_channel_configuration",
        "take_over_conversation",
        "dismiss_with_reason",
        "return_to_cartflow",
    }
)

# Map Decision.required_action → executable command_type
REQUIRED_ACTION_TO_COMMAND = {
    "approve_discount": "approve_discount",
    "reject_exception": "reject_exception",
    "provide_information": "provide_information",
    "fix_channel_configuration": "fix_channel_configuration",
    "take_over_conversation": "take_over_conversation",
    "dismiss_with_reason": "dismiss_with_reason",
    "return_to_cartflow": "return_to_cartflow",
    "approve_next_step": "return_to_cartflow",
    "approve_or_deny_discount": "approve_discount",
    "override_decision_action": "take_over_conversation",
    "provide_confirm_phone": "provide_information",
    "judgment_action": "return_to_cartflow",
    "recovery_action": "return_to_cartflow",
}


class CommandError(ValueError):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


def resolve_command_type(required_action: str, command_type: Optional[str] = None) -> str:
    if command_type and command_type in ALLOWED_COMMANDS:
        return command_type
    mapped = REQUIRED_ACTION_TO_COMMAND.get((required_action or "").strip())
    if mapped and mapped in ALLOWED_COMMANDS:
        return mapped
    raise CommandError("unknown_command", f"unsupported action:{required_action}")


def execute_command(
    *,
    store: ShadowStoreV1,
    store_slug: str,
    decision_id: str,
    command_type: str,
    actor_merchant_user_id: str,
    command_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Validate + execute. On success: T3 Decision Ownership → CartFlow, close Decision, rebuild projection.
    Idempotent on command_id replay after close.
    """
    command_id = (command_id or "").strip() or str(uuid.uuid4())
    ct = (command_type or "").strip()
    if ct not in ALLOWED_COMMANDS:
        raise CommandError("forbidden_command", ct)

    decision = store.get_decision(decision_id)
    if not decision:
        raise CommandError("decision_not_found")
    if (decision.store_slug or "").strip().lower() != (store_slug or "").strip().lower():
        raise CommandError("forbidden_store")

    # Idempotent: already closed
    if decision.status == "closed":
        proj = build_workspace_projection(store_slug, store)
        return {
            "ok": True,
            "idempotent": True,
            "command_id": command_id,
            "command_type": ct,
            "decision_id": decision_id,
            "ownership_transition": "T3",
            "decision_status": "closed",
            "projection": proj.to_dict(),
        }

    if decision.status != "open":
        raise CommandError("decision_not_open")

    ownership = store.get_ownership(decision.store_slug, decision.recovery_key)
    if ownership.decision_owner != "merchant":
        raise CommandError("ownership_not_merchant")

    # take_over: suppress automation intent (no T6 — OQ-2 deferred)
    intents: list[str] = []
    if ct == "take_over_conversation":
        intents.append("suppress_automation_messaging")
        intents.append("observe_continues")
        intents.append("handoff_audit")

    ownership2, audit, changed = apply_transition(
        ownership,
        transition_code="T3",
        evidence_refs=[command_id, ct, decision.admission_id],
        correlation_id=command_id,
    )
    store.set_ownership(ownership2)
    store.append_transition(audit)

    closed = store.close_decision(decision_id, resolved_at=_utc_now_iso())
    proj = build_workspace_projection(store_slug, store)

    return {
        "ok": True,
        "idempotent": False,
        "command_id": command_id,
        "command_type": ct,
        "decision_id": decision_id,
        "actor_merchant_user_id": actor_merchant_user_id,
        "ownership_transition": "T3",
        "transition_changed": changed,
        "decision_status": closed.status if closed else "closed",
        "intents": intents,
        "payload": payload or {},
        "projection": proj.to_dict(),
        "calm_recovery": bool(proj.quiet),
    }
