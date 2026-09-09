# -*- coding: utf-8 -*-
"""
Commercial Guidance Economic Safety Closure V1.

CartFlow has no authoritative shipping cost, subsidy, COGS, gross margin, or
margin floor. Merchant-facing guidance must therefore stay at disclosure /
clarification level and must never instruct an economically parameterized
intervention (free shipping, subsidy, discount, monetary threshold).
"""
from __future__ import annotations

import re
from pathlib import Path

from services.decision_composition_engine_v1.merchant_publication_v1 import (
    compose_merchant_publication_v1,
)
from services.decision_composition_engine_v1.store_executive_understanding_v1 import (
    _executive_decision_title_v1,
)
from services.decision_workspace_v2.narrative_v1 import decision_sentence_ar_v1
from services.home_executive_summary_v1.diagnosis_language_v1 import (
    REC_CONTINUE_EVIDENCE_AR,
)
from services.merchant_dashboard_reference_ui import (
    merchant_reason_panel_rows_from_counts,
)
from services.product_data.commercial_guidance_knowledge_registry_v1 import (
    GUIDANCE_INTAKE_POLICIES_V1,
)

_REPO = Path(__file__).resolve().parents[1]

# Modules that compose merchant-facing commercial guidance text.
MERCHANT_GUIDANCE_SOURCES = (
    "services/decision_workspace_v2/narrative_v1.py",
    "services/decision_composition_engine_v1/merchant_publication_v1.py",
    "services/decision_composition_engine_v1/store_executive_understanding_v1.py",
    "services/home_executive_summary_v1/diagnosis_language_v1.py",
    "services/merchant_value_composition_v1.py",
    "services/merchant_dashboard_reference_ui.py",
    "services/finding_decision_engine_v1.py",
    "services/business_reasoning_rules_v1.py",
    "services/commercial_action_language_v1/contract_v1.py",
    "services/operational_guidance_v1/compose_v1.py",
)

# A forbidden phrase is safe when the merchant is told *not* to do it
# ("لا تخفّض السعر", "بلا خصم", "قبل أي خصم"). Only unnegated uses instruct.
_NEGATORS = ("لا ", "دون", "بلا", "بدون", "قبل أي", "غير", "عدم", "لن ")


def _unnegated_hits(text: str, phrase: str) -> int:
    hits = 0
    start = 0
    while True:
        i = text.find(phrase, start)
        if i < 0:
            return hits
        lead = text[max(0, i - 16):i]
        if not any(n in lead for n in _NEGATORS):
            hits += 1
        start = i + len(phrase)

# Economically parameterized instructions — forbidden without economic truth.
FORBIDDEN_ECONOMIC_PHRASES = (
    "عدّل تكلفة الشحن",
    "خفّض تكلفة الشحن",
    "ستعدّل سياسة الشحن",
    # "عرض تكلفة الشحن" reads as a shipping *offer*; disclosure must say وضوح.
    "عرض تكلفة الشحن",
    "شحن مجاني",
    "شحنًا مجانيًا",
    "شحناً مجانياً",
    "دعم الشحن",
    "عروض الخصم",
    "استراتيجية التسعير أو الخصم",
    "خفّض السعر",
    "اخفض السعر",
    "قلّل السعر",
    "قدّم خصماً",
    "اعرض خصماً",
)

# Fabricated product-confidence proof — only authoritative evidence is allowed.
FORBIDDEN_INVENTED_PROOF = (
    "أضف تقييمات",
    "اعرض تقييمات",
    "أضف شهادات",
    "اعرض شهادات",
    "أضف ضماناً",
    "أضف دليلاً اجتماعياً",
)

# Monetary threshold parameterization, e.g. "فوق 199 ر.س".
_THRESHOLD_RE = re.compile(r"(فوق|أكثر من)\s*\d")


def _guidance_text() -> list[tuple[str, str]]:
    return [(rel, (_REPO / rel).read_text(encoding="utf-8")) for rel in MERCHANT_GUIDANCE_SOURCES]


def test_no_economically_parameterized_merchant_guidance() -> None:
    for rel, text in _guidance_text():
        for phrase in FORBIDDEN_ECONOMIC_PHRASES:
            assert not _unnegated_hits(text, phrase), (
                f"{rel} instructs economic guidance: {phrase}"
            )


def test_negation_is_required_to_keep_a_forbidden_phrase() -> None:
    """The gate must not be satisfied by wording alone."""
    assert _unnegated_hits("لا تخفّض السعر الآن.", "خفّض السعر") == 0
    assert _unnegated_hits("وضّح القيمة قبل أي خصم مباشر.", "خصم مباشر") == 0
    assert _unnegated_hits("خفّض السعر هذا الأسبوع.", "خفّض السعر") == 1


def test_no_invented_product_confidence_proof() -> None:
    for rel, text in _guidance_text():
        for phrase in FORBIDDEN_INVENTED_PROOF:
            assert not _unnegated_hits(text, phrase), f"{rel} invents proof: {phrase}"


def test_no_monetary_threshold_in_merchant_guidance() -> None:
    for rel, text in _guidance_text():
        assert not _THRESHOLD_RE.search(text), f"{rel} emits a monetary threshold"


def test_no_merchant_facing_cross_sell_term() -> None:
    """Internal ids may keep cross_sell; merchant Arabic term is reserved."""
    for folder in ("services", "static", "templates"):
        for path in (_REPO / folder).rglob("*"):
            if path.suffix not in {".py", ".js", ".html"} or not path.is_file():
                continue
            assert "البيع المتقاطع" not in path.read_text(
                encoding="utf-8", errors="ignore"
            ), f"{path} paints البيع المتقاطع"


def test_shipping_action_stays_disclosure_level() -> None:
    ship = {
        "diagnosis_status": "supported",
        "business_domain": "shipping",
        "observation_ar": "مغادرة عند الشحن.",
        "has_decision": True,
        "subject_ar": "Nano 20W",
    }
    sentence = decision_sentence_ar_v1(ship)
    assert "تكلفة الشحن" in sentence
    assert "مدة التوصيل" in sentence
    assert "عدّل تكلفة الشحن" not in sentence


def test_shipping_situation_action_stays_disclosure_level() -> None:
    pub = compose_merchant_publication_v1(
        {"ok": True, "portfolio": []},
        situations_pkg={
            "ok": True,
            "published_situations": [
                {
                    "situation_id": "cs:shipping_friction|p:r17",
                    "situation_kind": "shipping_friction",
                    "title_ar": "احتكاك الشحن",
                    "executive_summary_ar": "الشحن يضعف الإتمام.",
                    "priority": 72,
                    "admitted": True,
                    "subject": {"name_ar": "R17 — سماعة"},
                }
            ],
        },
    )
    action = pub["primary_action"]
    assert "تكلفة الشحن" in action and "مدة التوصيل" in action
    for phrase in FORBIDDEN_ECONOMIC_PHRASES:
        assert phrase not in action


def test_price_title_clarifies_value_before_discount() -> None:
    title = _executive_decision_title_v1({"business_domain": "pricing"})
    assert "الخصم" not in title
    assert "مقابل السعر" in title


def test_wait_state_prefers_no_action() -> None:
    waiting = {
        "diagnosis_status": "insufficient_evidence",
        "business_domain": "shipping",
        "observation_ar": "يغادر العملاء بعد خطوة الشحن.",
        "confidence_level": "low",
    }
    assert decision_sentence_ar_v1(waiting) == "لا تغيّر سياسة الشحن حتى تتضح الأدلة."
    assert REC_CONTINUE_EVIDENCE_AR == "واصل جمع الأدلة."


def test_reason_insight_is_share_not_cause_and_not_discount() -> None:
    _rows, insight = merchant_reason_panel_rows_from_counts(
        {"price_high": 8, "shipping": 12}
    )
    assert "أسباب التردد المسجّلة" in insight
    assert "يسببان" not in insight
    assert "عروض الخصم" not in insight


def test_ogl_still_forbids_economic_actions() -> None:
    forbidden: set[str] = set()
    for policy in GUIDANCE_INTAKE_POLICIES_V1:
        forbidden.update(policy["forbidden_actions"])
    for action in (
        "reduce_shipping_cost",
        "offer_shipping_discount",
        "lower_the_price",
        "force_discount_campaign",
    ):
        assert action in forbidden
