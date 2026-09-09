# -*- coding: utf-8 -*-
"""
Commercial Intervention Intelligence V1 — runtime regression gate.

Converts the simulation invariants (docs/architecture/
commercial_intervention_intelligence_v1/simulation_v1.py) into tests that run
against the REAL runtime owners. No mocks.
"""
from __future__ import annotations

import json

import pytest

from services.commercial_action_language_v1.contract_v1 import (
    CTA_ACCEPT_MISSION_AR,
    FAMILY_PRICE,
    FAMILY_PRODUCT,
    FAMILY_SHIPPING,
    FAMILY_WAIT,
)
from services.commercial_action_language_v1.intervention_v1 import (
    ALREADY_UNDER_MEASUREMENT,
    CONFLICTING_SIGNALS,
    ECONOMIC_INPUTS_REQUIRED,
    ELIGIBILITY_STATES,
    ELIGIBLE,
    ERROR_CTA_ON_BLOCKED_CARD,
    FAMILY_COMPLEMENTARY,
    INSUFFICIENT_EVIDENCE,
    INTERVENTION_NOT_JUSTIFIED,
    WAIT_AND_RECHECK,
    compose_merchant_intervention_card_v1,
    derive_eligibility_v1,
    economic_manifest_v1,
    effective_level_v1,
    intervention_contract_v1,
    missing_economic_inputs_v1,
    validate_intervention_card_v1,
)
from services.commercial_decision_commitment_v1.contract_v1 import (
    PHASE_ACTION_CHOSEN,
    PHASE_RECHECK_DUE,
    PHASE_UNDER_MEASUREMENT,
    SNAPSHOT_MAX_BYTES,
)
from services.commercial_decision_commitment_v1.snapshots_v1 import (
    SnapshotContractError,
    build_decision_snapshot,
    parse_and_validate_decision_snapshot,
)
from services.commercial_opportunity_layer_v1.contract_v1 import (
    TRUTH_INSUFFICIENT,
    TRUTH_PRODUCTION_PARTIAL,
    TRUTH_PRODUCTION_READY,
)
from services.commercial_opportunity_layer_v1.truth_gate_v1 import (
    classify_hesitation_truth_v1,
)
from services.mission_catalog_v1.contract_v1 import ROLE_PRIMARY, ROLE_SECONDARY
from services.mission_portfolio_v1.conflict_v1 import evaluate_conflict_v1
from services.mission_portfolio_v1.contract_v1 import (
    CONFLICT_CAPACITY_ONLY,
    CONFLICT_DUPLICATE_INTENT,
    CONFLICT_MEASUREMENT_CONTAMINATION,
    CONFLICT_SAFE_TO_COEXIST,
)

R17_EVIDENCE = {"counts": {"hesitation_total": 20, "top_count": 12, "top_share": 0.60}}


def _card(family, *, evidence=None, truth=TRUTH_PRODUCTION_READY, role=ROLE_PRIMARY,
          conflict=CONFLICT_SAFE_TO_COEXIST, phase=None, manifest=None,
          requested_level=None, reason_label_ar=""):
    intervention = intervention_contract_v1(
        family=family,
        col_truth_class=truth,
        catalog_role=role,
        portfolio_conflict_type=conflict,
        own_cdc_phase=phase,
        manifest=manifest,
        requested_level=requested_level,
    )
    card = compose_merchant_intervention_card_v1(
        family=family,
        intervention=intervention,
        evidence=evidence,
        reason_label_ar=reason_label_ar,
    )
    return intervention, card


# --------------------------------------------------------------------------
# R17 shipping Level 2
# --------------------------------------------------------------------------
def test_r17_shipping_level_2_eligible():
    assert classify_hesitation_truth_v1(total=20, top_count=12, share=0.60) == (
        TRUTH_PRODUCTION_READY
    )
    intervention, card = _card(FAMILY_SHIPPING, evidence=R17_EVIDENCE)

    assert intervention["recommendation_level"] == 2
    assert intervention["eligibility_state"] == ELIGIBLE
    assert validate_intervention_card_v1(card) == []
    # diagnosis untouched
    assert "12" in card["what_we_see_ar"] and "20" in card["what_we_see_ar"]
    # suggestion clarifies cost vs duration, changes no economics
    assert "تكلفة الشحن" in card["what_we_suggest_ar"]
    assert "مدة التوصيل" in card["what_we_suggest_ar"]
    # why-safe names the untouched lever
    assert "لا يغيّر سعرك" in card["why_this_is_safe_ar"]
    # dont_do forbids reduction + free shipping
    assert "لا تخفّض الشحن" in card["dont_do_ar"]
    assert "مجانياً" in card["dont_do_ar"]


def test_r17_blocked_candidates_are_economic():
    _, card = _card(FAMILY_SHIPPING, evidence=R17_EVIDENCE)
    blocked = card["blocked_candidates"]
    assert len(blocked) == 1
    assert blocked[0]["level"] == 3
    assert blocked[0]["blocked_reason"] == ECONOMIC_INPUTS_REQUIRED
    assert {"shipping_cost", "shipping_subsidy"} <= set(blocked[0]["missing_inputs"])
    assert "شحن مجاني" in blocked[0]["class_ar"]


# --------------------------------------------------------------------------
# price / product confidence / complementary products
# --------------------------------------------------------------------------
def test_price_level_2_clarifies_value_without_discount():
    intervention, card = _card(
        FAMILY_PRICE,
        evidence={"counts": {"hesitation_total": 20, "top_count": 11, "top_share": 0.55}},
    )
    assert intervention["recommendation_level"] == 2
    assert validate_intervention_card_v1(card) == []
    assert card["blocked_candidates"][0]["level"] == 3
    assert "خصم" in card["blocked_candidates"][0]["class_ar"]


def test_product_confidence_level_2_no_invented_proof():
    intervention, card = _card(
        FAMILY_PRODUCT,
        evidence={"counts": {"hesitation_total": 18, "top_count": 10, "top_share": 0.55}},
        reason_label_ar="جودة المنتج",
    )
    assert intervention["recommendation_level"] == 2
    assert validate_intervention_card_v1(card) == []
    assert "تختلق إثباتات ثقة" in card["dont_do_ar"]
    assert "بلا تقييمات أو شهادات" in card["what_we_suggest_ar"]
    # no stronger level defined for this family
    assert card["blocked_candidates"][0]["level"] is None


def test_complementary_products_level_1_names_no_product():
    intervention, card = _card(FAMILY_COMPLEMENTARY, role=ROLE_SECONDARY)
    assert intervention["recommendation_level"] == 1
    assert validate_intervention_card_v1(card) == []
    assert "منتج مكمل" in card["what_we_suggest_ar"]
    assert "المنتج B" not in card["what_we_suggest_ar"]
    assert card["blocked_candidates"][0]["level"] == 4


def test_no_merchant_facing_cross_sell_term():
    for family in (FAMILY_SHIPPING, FAMILY_PRICE, FAMILY_PRODUCT, FAMILY_COMPLEMENTARY):
        _, card = _card(family, evidence=R17_EVIDENCE, role=ROLE_SECONDARY)
        blob = json.dumps(card, ensure_ascii=False)
        assert "البيع المتقاطع" not in blob
        assert "بيع متقاطع" not in blob


# --------------------------------------------------------------------------
# eligibility precedence
# --------------------------------------------------------------------------
def test_insufficient_evidence_gives_explanatory_no_action():
    intervention, card = _card(
        FAMILY_WAIT,
        evidence={"counts": {"hesitation_total": 4, "top_count": 2, "top_share": 0.5}},
        truth=TRUTH_INSUFFICIENT,
    )
    assert intervention["eligibility_state"] == INSUFFICIENT_EVIDENCE
    assert validate_intervention_card_v1(card) == []
    assert card["blocked_candidates"][0]["blocked_reason"] == INSUFFICIENT_EVIDENCE
    assert card["what_we_suggest_ar"].startswith("لا نقترح تدخلاً الآن")


def test_capacity_only_defers_not_rejects():
    state = derive_eligibility_v1(
        col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
        portfolio_conflict_type=CONFLICT_CAPACITY_ONLY, catalog_role=ROLE_SECONDARY,
        family=FAMILY_PRICE, requested_level=2, missing_inputs=[],
    )
    assert state == WAIT_AND_RECHECK


def test_duplicate_intent_is_not_justified():
    state = derive_eligibility_v1(
        col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
        portfolio_conflict_type=CONFLICT_DUPLICATE_INTENT, catalog_role=ROLE_SECONDARY,
        family=FAMILY_SHIPPING, requested_level=2, missing_inputs=[],
    )
    assert state == INTERVENTION_NOT_JUSTIFIED


def test_conflicting_signals_from_real_portfolio():
    verdict = evaluate_conflict_v1(
        active={"family": FAMILY_SHIPPING, "cdc_phase": PHASE_UNDER_MEASUREMENT,
                "opportunity_id": "col:shipping:s1"},
        candidate={"family": FAMILY_PRICE, "opportunity_id": "col:price:s1"},
    )
    assert verdict["conflict_type"] == CONFLICT_MEASUREMENT_CONTAMINATION
    assert verdict["may_execute"] is False
    state = derive_eligibility_v1(
        col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
        portfolio_conflict_type=verdict["conflict_type"], catalog_role=ROLE_SECONDARY,
        family=FAMILY_PRICE, requested_level=2, missing_inputs=[],
    )
    assert state == CONFLICTING_SIGNALS


def test_already_under_measurement_blocks_parallel_intervention():
    for phase in (PHASE_ACTION_CHOSEN, PHASE_UNDER_MEASUREMENT):
        state = derive_eligibility_v1(
            col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=phase,
            portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
            family=FAMILY_SHIPPING, requested_level=2, missing_inputs=[],
        )
        assert state == ALREADY_UNDER_MEASUREMENT


def test_recheck_due_remains_eligible():
    state = derive_eligibility_v1(
        col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=PHASE_RECHECK_DUE,
        portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
        family=FAMILY_SHIPPING, requested_level=2, missing_inputs=[],
    )
    assert state == ELIGIBLE


@pytest.mark.parametrize(
    "kwargs",
    [
        {"col_truth_class": "GARBAGE"},
        {"catalog_role": "weird_role"},
        {"portfolio_conflict_type": None},
        {"own_cdc_phase": "STALE_PHASE"},
        {"family": "made_up_family"},
        {"col_truth_class": TRUTH_PRODUCTION_PARTIAL},
    ],
)
def test_unknown_input_falls_through_to_wait(kwargs):
    base = dict(
        col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
        portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
        family=FAMILY_SHIPPING, requested_level=2, missing_inputs=[],
    )
    base.update(kwargs)
    assert derive_eligibility_v1(**base) == WAIT_AND_RECHECK


def test_eligibility_vocabulary_is_exactly_seven():
    assert len(ELIGIBILITY_STATES) == 7


# --------------------------------------------------------------------------
# level model
# --------------------------------------------------------------------------
def test_current_family_ceilings():
    assert effective_level_v1(FAMILY_SHIPPING) == 2
    assert effective_level_v1(FAMILY_PRICE) == 2
    assert effective_level_v1(FAMILY_PRODUCT) == 2
    assert effective_level_v1(FAMILY_COMPLEMENTARY) == 1


def test_explicit_level_3_request_blocked_by_economics():
    intervention = intervention_contract_v1(
        family=FAMILY_SHIPPING, col_truth_class=TRUTH_PRODUCTION_READY,
        catalog_role=ROLE_PRIMARY, portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST,
        requested_level=3,
    )
    requested = intervention["requested_candidate"]
    assert requested["eligibility_state"] == ECONOMIC_INPUTS_REQUIRED
    assert requested["offered_level_instead"] == 2
    assert len(requested["missing_inputs"]) == 8


@pytest.mark.parametrize(
    "field",
    ["shipping_cost", "shipping_subsidy", "product_cost", "gross_margin",
     "margin_floor", "payment_fees", "platform_commission", "AOV"],
)
def test_each_missing_economic_input_blocks_level_3(field):
    manifest = economic_manifest_v1({f: "present" for f in economic_manifest_v1()})
    manifest[field] = None
    assert missing_economic_inputs_v1(FAMILY_SHIPPING, 3, manifest) == [field]
    assert effective_level_v1(FAMILY_SHIPPING, manifest) == 2
    state = derive_eligibility_v1(
        col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
        portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
        family=FAMILY_SHIPPING, requested_level=3,
        missing_inputs=missing_economic_inputs_v1(FAMILY_SHIPPING, 3, manifest),
    )
    assert state == ECONOMIC_INPUTS_REQUIRED


def test_complete_economics_unlocks_level_3():
    manifest = economic_manifest_v1({f: "present" for f in economic_manifest_v1()})
    assert missing_economic_inputs_v1(FAMILY_SHIPPING, 3, manifest) == []
    assert effective_level_v1(FAMILY_SHIPPING, manifest) == 3


def test_no_level_skipping_for_complementary_even_with_full_manifest():
    manifest = economic_manifest_v1({f: "present" for f in economic_manifest_v1()})
    # levels 2-3 are undefined for this family, so the ladder stops at 1
    assert effective_level_v1(FAMILY_COMPLEMENTARY, manifest) == 1


def test_level_2_economic_instruction_is_rejected():
    _, card = _card(FAMILY_SHIPPING, evidence=R17_EVIDENCE)
    card["what_we_suggest_ar"] = "اختبر الشحن المجاني فوق 199 ر.س."
    errors = validate_intervention_card_v1(card)
    assert any(e.startswith("level2_invariant_violation") for e in errors)


def test_level_jump_is_rejected():
    _, card = _card(FAMILY_PRODUCT, evidence=R17_EVIDENCE)
    card["recommendation_level"] = 4
    assert "level_jump" in validate_intervention_card_v1(card)


# --------------------------------------------------------------------------
# CTA safety
# --------------------------------------------------------------------------
def test_cta_renders_only_when_eligible():
    _, card = _card(FAMILY_SHIPPING, evidence=R17_EVIDENCE)
    assert card["eligibility_state"] == ELIGIBLE
    assert card["cta_ar"] == CTA_ACCEPT_MISSION_AR


@pytest.mark.parametrize(
    "kwargs",
    [
        {"truth": TRUTH_INSUFFICIENT},
        {"phase": PHASE_UNDER_MEASUREMENT},
        {"conflict": CONFLICT_MEASUREMENT_CONTAMINATION},
        {"conflict": CONFLICT_DUPLICATE_INTENT},
        {"conflict": CONFLICT_CAPACITY_ONLY},
    ],
)
def test_blocked_cards_have_no_executable_cta(kwargs):
    _, card = _card(FAMILY_SHIPPING, evidence=R17_EVIDENCE, **kwargs)
    assert card["eligibility_state"] != ELIGIBLE
    assert card["cta_ar"] is None
    assert validate_intervention_card_v1(card) == []


def test_cta_on_blocked_card_is_a_hard_error():
    _, card = _card(FAMILY_SHIPPING, evidence=R17_EVIDENCE,
                    conflict=CONFLICT_MEASUREMENT_CONTAMINATION)
    card["cta_ar"] = CTA_ACCEPT_MISSION_AR
    assert ERROR_CTA_ON_BLOCKED_CARD in validate_intervention_card_v1(card)


def test_blocked_card_copy_explains_instead_of_instructing():
    _, card = _card(FAMILY_SHIPPING, evidence=R17_EVIDENCE,
                    conflict=CONFLICT_MEASUREMENT_CONTAMINATION)
    assert card["what_we_suggest_ar"].startswith("مؤجّل الآن")
    assert "ما ننتظره" in card["what_we_suggest_ar"]


# --------------------------------------------------------------------------
# CDC snapshot allowlist
# --------------------------------------------------------------------------
def test_cdc_snapshot_accepts_intervention_keys():
    intervention, _ = _card(FAMILY_SHIPPING, evidence=R17_EVIDENCE)
    blob = build_decision_snapshot(
        opportunity_key="col:shipping_friction:shipping:cf_live_reality_lab",
        opportunity_family=FAMILY_SHIPPING,
        opportunity_reason="shipping",
        truth_class=TRUTH_PRODUCTION_READY,
        accepted_at="2026-09-09T20:00:00Z",
        action_code="clarify_cost_vs_duration",
        proposed_metric_key="shipping_hesitation_share",
        signal_counts={"hesitation_total": 20, "top_count": 12, "top_share": 0.6},
        intervention_id=intervention["intervention_id"],
        recommendation_level=intervention["recommendation_level"],
        eligibility_state=intervention["eligibility_state"],
        conflict_group=intervention["conflict_group"],
        economic_inputs_state=intervention["economic_inputs_state"],
    )
    parsed = parse_and_validate_decision_snapshot(blob)
    assert parsed["intervention_id"] == intervention["intervention_id"]
    assert parsed["recommendation_level"] == 2
    assert parsed["eligibility_state"] == ELIGIBLE
    assert len(blob.encode("utf-8")) <= SNAPSHOT_MAX_BYTES


def test_cdc_snapshot_stays_within_budget():
    blob = build_decision_snapshot(
        opportunity_key="col:shipping_friction:shipping:" + "s" * 180,
        opportunity_family=FAMILY_SHIPPING,
        opportunity_reason="shipping",
        truth_class=TRUTH_PRODUCTION_READY,
        accepted_at="2026-09-09T20:00:00Z",
        action_code="clarify_cost_vs_duration",
        proposed_metric_key="shipping_hesitation_share",
        signal_counts={f"k{i}": i for i in range(16)},
        intervention_id="civ1:shipping_friction:2:act",
        recommendation_level=2,
        eligibility_state=ELIGIBLE,
        conflict_group="disclosure_only",
        economic_inputs_state="none_required",
    )
    assert len(blob.encode("utf-8")) <= SNAPSHOT_MAX_BYTES


def test_cdc_snapshot_still_rejects_unknown_keys():
    payload = {
        "schema_version": "cdc_decision_snapshot_v1",
        "opportunity_key": "k",
        "opportunity_family": FAMILY_SHIPPING,
        "opportunity_reason": "shipping",
        "truth_class": TRUTH_PRODUCTION_READY,
        "accepted_at": "2026-09-09T20:00:00Z",
        "causal_verdict": "intervention_caused_improvement",
    }
    with pytest.raises(SnapshotContractError) as exc:
        parse_and_validate_decision_snapshot(json.dumps(payload))
    assert "decision_snapshot_unknown_keys" in str(exc.value)


def test_cdc_snapshot_rejects_bad_recommendation_level():
    payload = {
        "schema_version": "cdc_decision_snapshot_v1",
        "opportunity_key": "k",
        "opportunity_family": FAMILY_SHIPPING,
        "opportunity_reason": "shipping",
        "truth_class": TRUTH_PRODUCTION_READY,
        "accepted_at": "2026-09-09T20:00:00Z",
        "recommendation_level": 9,
    }
    with pytest.raises(SnapshotContractError):
        parse_and_validate_decision_snapshot(json.dumps(payload))


def test_legacy_snapshot_without_new_keys_still_parses():
    blob = build_decision_snapshot(
        opportunity_key="k", opportunity_family=FAMILY_SHIPPING,
        opportunity_reason="shipping", truth_class=TRUTH_PRODUCTION_READY,
        accepted_at="2026-09-09T20:00:00Z",
    )
    parsed = parse_and_validate_decision_snapshot(blob)
    assert "intervention_id" not in parsed


# --------------------------------------------------------------------------
# revenue safety
# --------------------------------------------------------------------------
def test_purchase_truth_has_no_monetary_amount():
    from models import PurchaseTruthRecord

    money_markers = ("amount", "value", "total", "price", "revenue", "sar")
    columns = [c.name.lower() for c in PurchaseTruthRecord.__table__.columns]
    assert [c for c in columns if any(m in c for m in money_markers)] == []


def test_no_revenue_claim_in_merchant_language():
    claims = ("زاد الإيراد", "تحسن الإيراد", "استرددنا", "الإيراد ارتفع")
    for family in (FAMILY_SHIPPING, FAMILY_PRICE, FAMILY_PRODUCT, FAMILY_COMPLEMENTARY):
        _, card = _card(family, evidence=R17_EVIDENCE, role=ROLE_SECONDARY)
        blob = json.dumps(card, ensure_ascii=False)
        for claim in claims:
            assert claim not in blob


# --------------------------------------------------------------------------
# cost / ownership
# --------------------------------------------------------------------------
def test_eligibility_is_pure_and_takes_no_session():
    varnames = derive_eligibility_v1.__code__.co_varnames
    assert "session" not in varnames
    assert "db" not in varnames


def test_manifest_reads_nothing_and_defaults_to_missing():
    manifest = economic_manifest_v1()
    assert manifest and all(value is None for value in manifest.values())


def test_guidance_eligibility_table_is_not_reused():
    import services.commercial_action_language_v1.intervention_v1 as module

    source = module.__file__
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    assert "guidance_eligibility" not in text
    assert "GuidanceEligibilityEvaluation" not in text
    # and no DB access at all in the intervention layer
    assert "session" not in text and "query(" not in text


# --------------------------------------------------------------------------
# simulation parity — the 8 projections
# --------------------------------------------------------------------------
def test_simulation_parity_eight_projections():
    expected = [
        (FAMILY_SHIPPING, dict(evidence=R17_EVIDENCE), 2, ELIGIBLE),
        (FAMILY_PRICE, dict(evidence={"counts": {"hesitation_total": 20, "top_count": 11,
                                                 "top_share": 0.55}}), 2, ELIGIBLE),
        (FAMILY_PRODUCT, dict(evidence={"counts": {"hesitation_total": 18, "top_count": 10,
                                                   "top_share": 0.55}}), 2, ELIGIBLE),
        (FAMILY_COMPLEMENTARY, dict(role=ROLE_SECONDARY), 1, ELIGIBLE),
        (FAMILY_WAIT, dict(truth=TRUTH_INSUFFICIENT), 0, INSUFFICIENT_EVIDENCE),
        (FAMILY_PRICE, dict(conflict=CONFLICT_MEASUREMENT_CONTAMINATION,
                            role=ROLE_SECONDARY), 2, CONFLICTING_SIGNALS),
        (FAMILY_SHIPPING, dict(phase=PHASE_UNDER_MEASUREMENT), 2, ALREADY_UNDER_MEASUREMENT),
        (FAMILY_SHIPPING, dict(evidence=R17_EVIDENCE, requested_level=3), 2, ELIGIBLE),
    ]
    sections = ("what_we_see_ar", "what_we_suggest_ar", "why_this_is_safe_ar",
                "blocked_candidates", "dont_do_ar", "primary_metric",
                "recheck_condition", "mind_change_condition")
    for family, kwargs, level, state in expected:
        intervention, card = _card(family, **kwargs)
        assert intervention["recommendation_level"] == level, family
        assert intervention["eligibility_state"] == state, family
        assert validate_intervention_card_v1(card) == [], family
        for key in sections:
            assert card.get(key), f"{family}:{key}"
        assert bool(card["cta_ar"]) is (state == ELIGIBLE), family
