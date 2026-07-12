# -*- coding: utf-8 -*-
"""P3 Workspace Projection — merchant read model; does not mutate ownership/admission."""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Optional

from services.cart_workspace.contracts_v1 import (
    CompletedOutcomeRollup,
    DecisionRecord,
    WorkspaceProjection,
    ZoneSummary,
    _utc_now_iso,
)
from services.cart_workspace.shadow_store_v1 import ShadowStoreV1

QUIET_SUMMARY = "لا يوجد ما يحتاج قرارك الآن. CartFlow يتابع عمليات الاسترداد تلقائيًا."
WORKING_SUMMARY = "CartFlow يعمل الآن على استرداد السلال — لا تحتاج أن تراقب كل سلة."

ZONE_LABELS_AR = {
    "A": "أولوية قصوى (VIP)",
    "B": "ما يحتاج قرارك",
    "C": "CartFlow يعمل الآن",
    "D": "النتائج المكتملة",
    "E": "الصحة التشغيلية",
}

MISSION_QUESTION_AR = "ما الذي يحتاج قرارك الآن؟"

ACTION_LABELS_AR = {
    "approve_discount": "قبول الخصم",
    "reject_exception": "رفض الاستثناء",
    "provide_information": "تزويد المعلومة المطلوبة",
    "fix_channel_configuration": "إصلاح إعدادات القناة",
    "take_over_conversation": "متابعة المحادثة يدوياً",
    "dismiss_with_reason": "إغلاق مع سبب",
    "return_to_cartflow": "إعادة المتابعة لـ CartFlow",
    "approve_next_step": "اعتماد الخطوة التالية",
    "approve_or_deny_discount": "البت في طلب الخصم",
    "override_decision_action": "اتخذ قراراً لهذا العميل المهم",
    "provide_confirm_phone": "تأكيد رقم الجوال",
    "judgment_action": "اتخذ قرارك",
    "recovery_action": "متابعة الاسترداد",
}


def _card_from_decision(d: DecisionRecord) -> dict[str, Any]:
    action = d.required_action or ""
    return {
        "decision_id": d.decision_id,
        "recovery_key": d.recovery_key,
        "store_slug": d.store_slug,
        "decision_class": d.decision_class,
        "required_action": action,
        "action_label_ar": ACTION_LABELS_AR.get(action, action),
        "governing_reason": d.governing_reason,
        "admission_rule_id": d.admission_rule_id,
        "explanation": d.explanation.to_dict() if hasattr(d.explanation, "to_dict") else d.explanation,
        "evidence_refs": list(d.evidence_refs),
        "evidence_fingerprint": d.evidence_fingerprint,
        "admitted_at": d.admitted_at,
        "order_key": d.order_key or d.admitted_at,
        "execution_owner": d.execution_owner,
        "decision_owner": d.decision_owner,
        "override_mode": d.override_mode,
        "status": d.status,
    }


def _workspace_phase(zone_a: list, zone_b: list) -> str:
    if zone_a:
        return "WL-2"
    if zone_b:
        return "WL-3"
    return "WL-1"


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_workspace_projection(
    store_slug: str,
    store: ShadowStoreV1,
    *,
    freshness: str = "final",
    zone_e: Optional[dict[str, Any]] = None,
) -> WorkspaceProjection:
    open_rows = store.open_decisions(store_slug)
    zone_a_cards = sorted(
        [_card_from_decision(d) for d in open_rows if d.decision_class == "override"],
        key=lambda c: c.get("order_key") or c.get("admitted_at") or "",
    )
    zone_b_cards = sorted(
        [_card_from_decision(d) for d in open_rows if d.decision_class != "override"],
        key=lambda c: c.get("order_key") or c.get("admitted_at") or "",
    )

    quiet = not zone_a_cards and not zone_b_cards
    completions = store.completions(store_slug)
    recent = completions[-5:]
    rollup = CompletedOutcomeRollup(
        window="recent",
        completed_count=len(completions),
        recent_items=list(reversed(recent)),
        rollup_version=max(1, len(completions)),
        updated_at=_utc_now_iso(),
    )
    zone_c = ZoneSummary(
        visible=True,
        kind="reassurance",
        summary=QUIET_SUMMARY if quiet else WORKING_SUMMARY,
        active_recovery_indicator=True,
    )

    attention = None
    if zone_a_cards:
        attention = zone_a_cards[0]["decision_id"]
    elif zone_b_cards:
        attention = zone_b_cards[0]["decision_id"]

    version = store.next_projection_version(store_slug)
    phase = _workspace_phase(zone_a_cards, zone_b_cards)
    fp_payload = {
        "zone_a_ids": [c["decision_id"] for c in zone_a_cards],
        "zone_b_ids": [c["decision_id"] for c in zone_b_cards],
        "quiet": quiet,
        "rollup_version": rollup.rollup_version,
        "zone_e": (zone_e or {}).get("exception_id") if zone_e else None,
        "version": version,
    }
    proj = WorkspaceProjection(
        store_slug=store_slug,
        projection_id=str(uuid.uuid4()),
        projection_version=version,
        projection_fingerprint=_fingerprint(fp_payload),
        built_at=_utc_now_iso(),
        freshness=freshness,  # type: ignore[arg-type]
        workspace_phase=phase,
        zone_a=zone_a_cards,
        zone_b=zone_b_cards,
        zone_c=zone_c.to_dict(),
        zone_d=rollup.to_dict(),
        zone_e=zone_e,
        quiet=quiet,
        attention_focus_decision_id=attention,
        last_good_retained=False,
        zone_labels=dict(ZONE_LABELS_AR),
        mission_question=MISSION_QUESTION_AR,
    )
    store.save_projection(store_slug, proj.to_dict())
    return proj
