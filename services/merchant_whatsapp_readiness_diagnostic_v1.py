# -*- coding: utf-8 -*-
"""
Temporary diagnostic — why checklist item «واتساب جاهز» is ✗.

Read-only audit helper; does not change readiness engine behavior.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

CHECKLIST_SOURCE_PATH = (
    "evaluate_onboarding_readiness"
    " → evaluate_whatsapp_connection_readiness"
    " → _readiness_dimensions"
    " → whatsapp_setup_checklist_for_merchant"
    " → setup_checklist.checklist_ar[key=whatsapp_ready]"
)


def _dim_by_key(dimensions: list[dict[str, Any]], key: str) -> Optional[dict[str, Any]]:
    for dim in dimensions:
        if dim.get("key") == key:
            return dim
    return None


def _trace_whatsapp_ready_conditions(
    store: Optional[Any],
    flags: Mapping[str, bool],
) -> tuple[bool, list[dict[str, Any]], dict[str, Any]]:
    """
    Mirror _readiness_dimensions whatsapp_ok logic with per-condition audit trail.
    """
    widget_ok = bool(flags.get("widget_installed"))
    store_ok = bool(flags.get("store_connected"))
    wa_number = bool(
        store is not None
        and (getattr(store, "store_whatsapp_number", None) or "").strip()
    )
    recovery_on = bool(flags.get("recovery_enabled"))
    sandbox = bool(flags.get("sandbox_mode_active"))
    prov = bool(flags.get("provider_ready"))
    wa_cfg = bool(flags.get("whatsapp_configured"))

    merchant_recovery_toggle = None
    if store is not None:
        raw = getattr(store, "whatsapp_recovery_enabled", None)
        merchant_recovery_toggle = True if raw is None else bool(raw)

    inputs = {
        "flags.recovery_enabled": recovery_on,
        "flags.sandbox_mode_active": sandbox,
        "flags.provider_ready": prov,
        "flags.whatsapp_configured": wa_cfg,
        "flags.widget_installed": widget_ok,
        "flags.store_connected": store_ok,
        "store.store_whatsapp_number_present": wa_number,
        "store.whatsapp_recovery_enabled": merchant_recovery_toggle,
        "store.is_active": (
            bool(getattr(store, "is_active", True)) if store is not None else None
        ),
        "store.recovery_attempts": (
            getattr(store, "recovery_attempts", None) if store is not None else None
        ),
    }

    conditions: list[dict[str, Any]] = [
        {
            "field": "flags.recovery_enabled",
            "value": recovery_on,
            "required": True,
            "passed": recovery_on,
            "note_ar": (
                "يُشتق من store.is_active و recovery_attempts>=1 "
                "(وليس من store.whatsapp_recovery_enabled)"
            ),
            "code_path": (
                "cartflow_onboarding_readiness.evaluate_onboarding_readiness"
                " → flags['recovery_enabled']"
            ),
        },
        {
            "field": "store.store_whatsapp_number",
            "value": wa_number,
            "required": True,
            "passed": wa_number,
            "note_ar": "وجود رقم غير فارغ على Store",
            "code_path": (
                "merchant_whatsapp_connection_readiness_v1._readiness_dimensions"
                " → wa_number"
            ),
        },
        {
            "field": "flags.sandbox_mode_active",
            "value": sandbox,
            "required": False,
            "passed": not sandbox,
            "note_ar": "يجب أن يكون False لاجتياز الصيغة الأساسية (not sandbox)",
            "code_path": (
                "merchant_whatsapp_connection_readiness_v1._readiness_dimensions"
                " → whatsapp_ok term: not sandbox"
            ),
        },
        {
            "field": "flags.whatsapp_configured",
            "value": wa_cfg,
            "required": not sandbox,
            "passed": wa_cfg or sandbox,
            "note_ar": (
                "في غير الوضع التجريبي: Twilio مضبوط "
                "(TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_WHATSAPP_FROM)"
            ),
            "code_path": (
                "cartflow_onboarding_readiness → whatsapp_real_configured()"
                " → flags['whatsapp_configured']"
            ),
        },
        {
            "field": "flags.provider_ready",
            "value": prov,
            "required": not sandbox,
            "passed": prov or not sandbox,
            "note_ar": "في الإنتاج: get_whatsapp_provider_readiness().ready",
            "code_path": (
                "cartflow_onboarding_readiness → get_whatsapp_provider_readiness"
            ),
        },
    ]

    base_formula = (
        recovery_on
        and wa_number
        and not sandbox
        and (prov or not sandbox)
        and (wa_cfg or sandbox)
    )
    conditions.append(
        {
            "field": "whatsapp_ok_base_formula",
            "value": base_formula,
            "required": True,
            "passed": base_formula,
            "note_ar": (
                "recovery_on ∧ wa_number ∧ ¬sandbox ∧ "
                "(prov ∨ ¬sandbox_mode_active) ∧ (wa_cfg ∨ sandbox)"
            ),
            "code_path": (
                "merchant_whatsapp_connection_readiness_v1._readiness_dimensions"
                " → whatsapp_ok assignment"
            ),
        }
    )

    sandbox_override = bool(
        sandbox and store_ok and widget_ok and wa_number and recovery_on
    )
    conditions.append(
        {
            "field": "sandbox_merchant_setup_complete_override",
            "value": sandbox_override,
            "required": False,
            "passed": not sandbox_override,
            "note_ar": (
                "إذا كان الوضع تجريبياً والمتجر/الودجت/الرقم/الاسترجاع مكتملة "
                "يُفرض whatsapp_ok=False صراحة"
            ),
            "code_path": (
                "merchant_whatsapp_connection_readiness_v1._readiness_dimensions"
                " → if sandbox and store_ok and widget_ok and wa_number "
                "and recovery_on: whatsapp_ok = False"
            ),
        }
    )

    whatsapp_ok = base_formula
    if sandbox_override:
        whatsapp_ok = False

    failing = [c for c in conditions if not c["passed"]]

    return whatsapp_ok, failing, inputs


def build_whatsapp_readiness_diagnostic_temp(
    readiness: Mapping[str, Any],
    store: Optional[Any],
    *,
    action_first: Optional[Mapping[str, Any]] = None,
    onboarding_flags: Optional[Mapping[str, bool]] = None,
    blocking_steps: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Temporary merchant/admin diagnostic payload — remove after audit."""
    flags = dict(onboarding_flags or {})
    dimensions = list(readiness.get("readiness_dimensions") or [])
    setup = dict(readiness.get("setup_checklist") or {})
    wa_dim = _dim_by_key(dimensions, "whatsapp_ready") or {}
    checklist_items = list(setup.get("checklist_ar") or [])
    wa_item = next(
        (i for i in checklist_items if i.get("key") == "whatsapp_ready"),
        {},
    )

    whatsapp_ok, failing, inputs = _trace_whatsapp_ready_conditions(store, flags)
    af = dict(action_first or {})

    primary_fail = failing[0] if failing else None
    return {
        "temporary": True,
        "audit_only": True,
        "readiness_state": readiness.get("connection_state"),
        "readiness_state_ar": readiness.get("connection_state_ar"),
        "readiness_overall": readiness.get("readiness_overall"),
        "readiness_overall_ar": readiness.get("readiness_overall_ar"),
        "readiness_title_ar": af.get("title_ar") or "",
        "readiness_title_source": (
            "build_action_first_card"
            " → CONNECTION_STATE_ACTION_FIRST[connection_state].title_ar"
        ),
        "checklist_source": CHECKLIST_SOURCE_PATH,
        "checklist_item": {
            "key": wa_item.get("key") or "whatsapp_ready",
            "label_ar": wa_item.get("label_ar") or "واتساب جاهز",
            "complete": bool(wa_item.get("complete")),
            "mark_ar": wa_item.get("mark_ar") or ("✓" if wa_dim.get("ready") else "✗"),
            "ready_field": "readiness_dimensions[].ready where key=whatsapp_ready",
            "ready_value": bool(wa_dim.get("ready")),
            "computed_whatsapp_ok": whatsapp_ok,
        },
        "onboarding_flags": flags,
        "blocking_steps": list(blocking_steps or []),
        "store_inputs": inputs,
        "failing_conditions": failing,
        "primary_failing_condition": primary_fail,
        "journey_vs_readiness_note_ar": (
            "اكتمال المسار يعتمد store_whatsapp_number + whatsapp_recovery_enabled. "
            "بند «واتساب جاهز» يعتمد flags من evaluate_onboarding_readiness "
            "ويشمل sandbox_mode_active وwhatsapp_configured (Twilio) "
            "ولا يستخدم whatsapp_recovery_enabled مباشرة."
        ),
    }
