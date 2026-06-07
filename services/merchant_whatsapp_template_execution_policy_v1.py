# -*- coding: utf-8 -*-
"""WhatsApp template execution policy — read-only helpers (no send/runtime migration)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from services.merchant_whatsapp_reason_mapping_v1 import (
    normalize_reason_tag,
    resolve_template_key_for_followup_slot,
    resolve_template_key_for_reason,
)
from services.merchant_whatsapp_template_layer_v1 import (
    parse_whatsapp_template_overrides_column,
)
from services.merchant_whatsapp_template_registry_v1 import (
    TEMPLATE_REGISTRY,
    get_registry_entry,
)

# --- Execution stages (max 3 customer recovery messages) ---

STAGE_REASON_RECOVERY = 1
STAGE_GENERAL_FOLLOWUP = 2
STAGE_FINAL_FOLLOWUP = 3
MAX_EXECUTION_STAGES = 3

STAGE_LABEL_AR: Mapping[int, str] = {
    STAGE_REASON_RECOVERY: "رسالة السبب",
    STAGE_GENERAL_FOLLOWUP: "متابعة عامة",
    STAGE_FINAL_FOLLOWUP: "متابعة أخيرة / إغلاق",
}

EXECUTION_STAGE_TO_FOLLOWUP_TEMPLATE: Mapping[int, str] = {
    STAGE_GENERAL_FOLLOWUP: "FOLLOWUP_1_TEMPLATE",
    STAGE_FINAL_FOLLOWUP: "FOLLOWUP_2_TEMPLATE",
}

# --- Hard stop reasons (canonical policy vocabulary) ---

STOP_CUSTOMER_PURCHASED = "customer_purchased"
STOP_CUSTOMER_REPLIED_POSITIVE = "customer_replied_positive"
STOP_CUSTOMER_DECLINED = "customer_declined"
STOP_CUSTOMER_RETURNED = "customer_returned"
STOP_MERCHANT_ARCHIVED = "merchant_archived"
STOP_RECOVERY_EXPIRED = "recovery_expired"
STOP_TEMPLATE_DISABLED = "template_disabled"
STOP_STORE_WHATSAPP_DISABLED = "store_whatsapp_disabled"
STOP_PROVIDER_UNAVAILABLE = "provider_unavailable"
STOP_SEQUENCE_COMPLETE = "sequence_complete"
STOP_VIP_LANE_ISOLATION = "vip_lane_isolation"

HARD_STOP_REASONS: frozenset[str] = frozenset(
    {
        STOP_CUSTOMER_PURCHASED,
        STOP_CUSTOMER_REPLIED_POSITIVE,
        STOP_CUSTOMER_DECLINED,
        STOP_CUSTOMER_RETURNED,
        STOP_MERCHANT_ARCHIVED,
        STOP_RECOVERY_EXPIRED,
        STOP_TEMPLATE_DISABLED,
        STOP_STORE_WHATSAPP_DISABLED,
        STOP_PROVIDER_UNAVAILABLE,
        STOP_SEQUENCE_COMPLETE,
    }
)

# --- Skip reasons (send attempt not made) ---

SKIP_TEMPLATE_DISABLED = "template_disabled"
SKIP_UNKNOWN_FALLBACK_NOT_ALLOWED = "unknown_fallback_not_allowed"
SKIP_DAILY_STORE_SEND_GUARD = "daily_store_send_guard"
SKIP_REPEATED_FAILURE_SUPPRESSION = "repeated_failure_suppression"
SKIP_PROVIDER_UNAVAILABLE = "provider_unavailable"
SKIP_STORE_WHATSAPP_DISABLED = "store_whatsapp_disabled"
SKIP_META_TEMPLATE_NOT_APPROVED = "meta_template_not_approved"

# --- Next actions ---

NEXT_STOP = "stop"
NEXT_SEND_STAGE = "send_stage"
NEXT_FOLLOW_UP = "follow_up"
NEXT_MERCHANT_INTERVENTION = "merchant_intervention"
NEXT_ARCHIVE = "archive"
NEXT_CONTINUATION = "continuation_handoff"
NEXT_WAIT_BEHAVIOR = "wait_for_customer_behavior"

# --- VIP policy constants ---

VIP_ALERT_TEMPLATE_KEY = "VIP_ALERT_TEMPLATE"
VIP_COUNTS_AS_CUSTOMER_RECOVERY = False
VIP_REPLACES_NORMAL_RECOVERY_DEFAULT = False


@dataclass(frozen=True)
class ExecutionPolicyDecision:
    """Read-only policy outcome — does not trigger send or schedule changes."""

    allowed: bool
    stage: int
    template_key: Optional[str]
    stop_reason: Optional[str] = None
    skip_reason: Optional[str] = None
    next_action: Optional[str] = None
    policy_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "stage": self.stage,
            "template_key": self.template_key,
            "stop_reason": self.stop_reason,
            "skip_reason": self.skip_reason,
            "next_action": self.next_action,
            "policy_note": self.policy_note,
        }


def execution_sequence_steps_for_api() -> list[dict[str, str]]:
    """Canonical execution sequence (Part A) — documentation / admin architecture."""
    return [
        {"step": "1", "key": "reason_captured", "label_ar": "التقاط سبب التردد"},
        {"step": "2", "key": "select_template", "label_ar": "اختيار القالب حسب reason_tag"},
        {"step": "3", "key": "apply_merchant_override", "label_ar": "تطبيق تخصيص التاجر إن وُجد"},
        {"step": "4", "key": "apply_timing_policy", "label_ar": "تطبيق سياسة التوقيت"},
        {"step": "5", "key": "send_first_message", "label_ar": "إرسال رسالة الاسترجاع الأولى"},
        {"step": "6", "key": "wait_behavior", "label_ar": "انتظار سلوك العميل"},
        {
            "step": "7",
            "key": "decide_next",
            "label_ar": "قرار: إيقاف / متابعة / تدخل تاجر / أرشفة",
        },
    ]


def resolve_template_key_for_execution_stage(
    stage: int,
    reason_tag: Optional[str],
) -> str:
    """Map execution stage + reason to registry template_key."""
    try:
        n = int(stage)
    except (TypeError, ValueError):
        n = STAGE_REASON_RECOVERY
    if n <= STAGE_REASON_RECOVERY:
        return resolve_template_key_for_reason(reason_tag)
    followup_key = EXECUTION_STAGE_TO_FOLLOWUP_TEMPLATE.get(n)
    if followup_key:
        return followup_key
    slot_key = resolve_template_key_for_followup_slot(n - 1)
    return slot_key or "FOLLOWUP_3_TEMPLATE"


def _reason_template_enabled(store: Any, reason_tag: Optional[str]) -> bool:
    canon = normalize_reason_tag(reason_tag)
    if canon is None:
        return True
    template_key = resolve_template_key_for_reason(reason_tag)
    overrides = parse_whatsapp_template_overrides_column(
        getattr(store, "whatsapp_template_overrides_json", None) if store else None
    )
    ov = overrides.get(template_key)
    if ov and "enabled" in ov:
        return bool(ov.get("enabled"))
    entry = get_registry_entry(template_key)
    return entry.enabled if entry else True


def _store_whatsapp_recovery_enabled(store: Any) -> bool:
    if store is None:
        return True
    raw = getattr(store, "whatsapp_recovery_enabled", None)
    return True if raw is None else bool(raw)


def evaluate_hard_stop_conditions(
    *,
    customer_purchased: bool = False,
    customer_replied_positive: bool = False,
    customer_declined: bool = False,
    customer_returned: bool = False,
    merchant_archived: bool = False,
    recovery_expired: bool = False,
    store_whatsapp_disabled: bool = False,
    provider_unavailable: bool = False,
    sequence_complete: bool = False,
) -> Optional[str]:
    """Return first matching hard stop reason, or None if sequence may continue."""
    checks: list[tuple[bool, str]] = [
        (customer_purchased, STOP_CUSTOMER_PURCHASED),
        (customer_replied_positive, STOP_CUSTOMER_REPLIED_POSITIVE),
        (customer_declined, STOP_CUSTOMER_DECLINED),
        (customer_returned, STOP_CUSTOMER_RETURNED),
        (merchant_archived, STOP_MERCHANT_ARCHIVED),
        (recovery_expired, STOP_RECOVERY_EXPIRED),
        (store_whatsapp_disabled, STOP_STORE_WHATSAPP_DISABLED),
        (provider_unavailable, STOP_PROVIDER_UNAVAILABLE),
        (sequence_complete, STOP_SEQUENCE_COMPLETE),
    ]
    for flag, reason in checks:
        if flag:
            return reason
    return None


def evaluate_template_disabled_policy(
    reason_tag: Optional[str],
    store: Any = None,
    *,
    allow_unknown_fallback: bool = True,
    stage: int = STAGE_REASON_RECOVERY,
) -> ExecutionPolicyDecision:
    """
    Part G — if reason template disabled, skip or fallback to UNKNOWN_REASON_TEMPLATE.
    Read-only; runtime today uses reason_template_recovery.reason_template_blocks_recovery_whatsapp.
    """
    if not _store_whatsapp_recovery_enabled(store):
        return ExecutionPolicyDecision(
            allowed=False,
            stage=stage,
            template_key=None,
            skip_reason=SKIP_STORE_WHATSAPP_DISABLED,
            stop_reason=STOP_STORE_WHATSAPP_DISABLED,
            next_action=NEXT_STOP,
            policy_note="store_whatsapp_recovery_enabled=false",
        )

    if stage > STAGE_REASON_RECOVERY:
        fk = resolve_template_key_for_execution_stage(stage, reason_tag)
        entry = get_registry_entry(fk)
        if entry and not entry.enabled:
            return ExecutionPolicyDecision(
                allowed=False,
                stage=stage,
                template_key=fk,
                skip_reason=SKIP_TEMPLATE_DISABLED,
                stop_reason=STOP_TEMPLATE_DISABLED,
                next_action=NEXT_STOP,
                policy_note="followup_template_disabled",
            )
        return ExecutionPolicyDecision(
            allowed=True,
            stage=stage,
            template_key=fk,
            next_action=NEXT_SEND_STAGE,
            policy_note="followup_stage_allowed",
        )

    if not _reason_template_enabled(store, reason_tag):
        if allow_unknown_fallback:
            return ExecutionPolicyDecision(
                allowed=True,
                stage=stage,
                template_key="UNKNOWN_REASON_TEMPLATE",
                skip_reason=SKIP_TEMPLATE_DISABLED,
                next_action=NEXT_SEND_STAGE,
                policy_note="reason_disabled_fallback_unknown",
            )
        return ExecutionPolicyDecision(
            allowed=False,
            stage=stage,
            template_key=resolve_template_key_for_reason(reason_tag),
            skip_reason=SKIP_UNKNOWN_FALLBACK_NOT_ALLOWED,
            stop_reason=STOP_TEMPLATE_DISABLED,
            next_action=NEXT_STOP,
            policy_note="reason_disabled_no_fallback",
        )

    tk = resolve_template_key_for_reason(reason_tag)
    return ExecutionPolicyDecision(
        allowed=True,
        stage=stage,
        template_key=tk,
        next_action=NEXT_SEND_STAGE,
        policy_note="reason_template_allowed",
    )


def evaluate_follow_up_policy(
    *,
    current_stage: int,
    customer_replied: bool = False,
    customer_returned: bool = False,
    customer_purchased: bool = False,
    no_response: bool = True,
) -> ExecutionPolicyDecision:
    """Part D — follow-up progression after stage 1."""
    stop = evaluate_hard_stop_conditions(
        customer_purchased=customer_purchased,
        customer_returned=customer_returned,
        customer_replied_positive=customer_replied,
        sequence_complete=current_stage >= MAX_EXECUTION_STAGES and no_response,
    )
    if stop:
        next_act = NEXT_CONTINUATION if stop == STOP_CUSTOMER_REPLIED_POSITIVE else NEXT_STOP
        if stop == STOP_CUSTOMER_PURCHASED:
            next_act = NEXT_STOP
        return ExecutionPolicyDecision(
            allowed=False,
            stage=current_stage,
            template_key=None,
            stop_reason=stop,
            next_action=next_act,
            policy_note=f"follow_up_stop:{stop}",
        )

    if customer_replied:
        return ExecutionPolicyDecision(
            allowed=False,
            stage=current_stage,
            template_key=None,
            stop_reason=STOP_CUSTOMER_REPLIED_POSITIVE,
            next_action=NEXT_CONTINUATION,
            policy_note="reply_stops_normal_sequence",
        )

    if customer_returned:
        return ExecutionPolicyDecision(
            allowed=False,
            stage=current_stage,
            template_key=None,
            stop_reason=STOP_CUSTOMER_RETURNED,
            next_action=NEXT_STOP,
            policy_note="return_stops_sequence",
        )

    if no_response and current_stage < MAX_EXECUTION_STAGES:
        nxt = current_stage + 1
        return ExecutionPolicyDecision(
            allowed=True,
            stage=nxt,
            template_key=resolve_template_key_for_execution_stage(nxt, None),
            next_action=NEXT_FOLLOW_UP,
            policy_note="no_response_advance_stage",
        )

    return ExecutionPolicyDecision(
        allowed=False,
        stage=current_stage,
        template_key=None,
        stop_reason=STOP_SEQUENCE_COMPLETE,
        next_action=NEXT_STOP,
        policy_note="max_stages_reached",
    )


def evaluate_vip_execution_policy(
    *,
    is_vip_cart: bool = False,
    vip_notify_enabled: bool = True,
    vip_replaces_recovery: bool = False,
) -> dict[str, Any]:
    """Part E — VIP lane isolation policy (architecture only)."""
    return {
        "vip_alert_template_key": VIP_ALERT_TEMPLATE_KEY,
        "vip_alert_is_merchant_facing": True,
        "vip_counts_as_customer_recovery": VIP_COUNTS_AS_CUSTOMER_RECOVERY,
        "vip_replaces_normal_recovery_default": VIP_REPLACES_NORMAL_RECOVERY_DEFAULT,
        "vip_replaces_normal_recovery_effective": bool(
            is_vip_cart and vip_replaces_recovery
        ),
        "vip_triggers_merchant_intervention": bool(is_vip_cart and vip_notify_enabled),
        "vip_lane_isolated_from_customer_sequence": True,
        "vip_must_not_increment_customer_sent_count": True,
        "policy_note": "VIP alert never shares customer recovery reason tags or stage counters",
    }


def managed_sender_policy_controls() -> dict[str, Any]:
    """Part F — CartFlow Managed internal fair-usage controls (not public quota)."""
    return {
        "architecture_only": True,
        "public_quota_exposed": False,
        "controls": {
            "daily_store_send_guard": {
                "enabled": True,
                "description_ar": "حد داخلي يومي لكل متجر — يمنع الإساءة",
                "skip_reason": SKIP_DAILY_STORE_SEND_GUARD,
            },
            "repeated_failure_suppression": {
                "enabled": True,
                "description_ar": "إيقاف مؤقت بعد فشل متكرر من المزود",
                "skip_reason": SKIP_REPEATED_FAILURE_SUPPRESSION,
            },
            "provider_unavailable_skip": {
                "enabled": True,
                "description_ar": "تخطي الإرسال عند عدم جاهزية المزود",
                "skip_reason": SKIP_PROVIDER_UNAVAILABLE,
            },
            "no_open_ended_retries": {
                "enabled": True,
                "description_ar": "لا إعادة محاولة لا نهائية — ثلاث مراحل كحد أقصى",
            },
            "template_disabled_skip": {
                "enabled": True,
                "description_ar": "تخطي القالب المعطّل مع سبب واضح",
                "skip_reason": SKIP_TEMPLATE_DISABLED,
            },
            "template_unavailable_suppression": {
                "enabled": True,
                "description_ar": "تخطي عند تعطيل القالب أو رفضه — سلسلة احتياط",
                "skip_reason": "template_unavailable",
            },
        },
    }


def admin_execution_visibility_schema() -> list[dict[str, str]]:
    """Part H — fields for future admin ops visibility."""
    return [
        {"field": "selected_template", "label_ar": "القالب المختار"},
        {"field": "execution_stage", "label_ar": "المرحلة"},
        {"field": "stop_reason", "label_ar": "سبب الإيقاف"},
        {"field": "skip_reason", "label_ar": "سبب التخطي"},
        {"field": "provider_status", "label_ar": "حالة المزود"},
        {"field": "next_action", "label_ar": "الإجراء التالي"},
        {"field": "whatsapp_mode", "label_ar": "وضع واتساب"},
        {"field": "future_meta_template_status", "label_ar": "حالة Meta (مستقبل)"},
    ]


def execution_policy_summary_for_api() -> dict[str, Any]:
    """Full policy export for admin architecture endpoint."""
    return {
        "policy_version": "v1",
        "architecture_only": True,
        "runtime_migration_required": False,
        "max_execution_stages": MAX_EXECUTION_STAGES,
        "execution_stages": [
            {
                "stage": STAGE_REASON_RECOVERY,
                "label_ar": STAGE_LABEL_AR[STAGE_REASON_RECOVERY],
                "template_selection": "reason_tag → registry reason template",
            },
            {
                "stage": STAGE_GENERAL_FOLLOWUP,
                "label_ar": STAGE_LABEL_AR[STAGE_GENERAL_FOLLOWUP],
                "template_key": EXECUTION_STAGE_TO_FOLLOWUP_TEMPLATE[
                    STAGE_GENERAL_FOLLOWUP
                ],
            },
            {
                "stage": STAGE_FINAL_FOLLOWUP,
                "label_ar": STAGE_LABEL_AR[STAGE_FINAL_FOLLOWUP],
                "template_key": EXECUTION_STAGE_TO_FOLLOWUP_TEMPLATE[
                    STAGE_FINAL_FOLLOWUP
                ],
            },
        ],
        "execution_sequence": execution_sequence_steps_for_api(),
        "hard_stop_reasons": sorted(HARD_STOP_REASONS),
        "skip_reasons": sorted(
            {
                SKIP_TEMPLATE_DISABLED,
                SKIP_UNKNOWN_FALLBACK_NOT_ALLOWED,
                SKIP_DAILY_STORE_SEND_GUARD,
                SKIP_REPEATED_FAILURE_SUPPRESSION,
                SKIP_PROVIDER_UNAVAILABLE,
                SKIP_STORE_WHATSAPP_DISABLED,
            }
        ),
        "vip_policy": evaluate_vip_execution_policy(is_vip_cart=True),
        "managed_sender_policy": managed_sender_policy_controls(),
        "admin_visibility_schema": admin_execution_visibility_schema(),
        "registry_template_count": len(TEMPLATE_REGISTRY),
    }
