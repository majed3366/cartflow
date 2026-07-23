# -*- coding: utf-8 -*-
"""
Evidence Truth Consumer Eligibility Matrix — WP-ET-03…09 governance.

Declares who may consume Observations, Evidence Truth, and shadow Bundles.
Code-level registry + WP-ET-09 Composer shadow producer row.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConsumerEligibilityRowV1:
    producer: str
    artifact: str
    permitted_consumers: tuple[str, ...]
    prohibited_consumers: tuple[str, ...]
    activation_condition: str
    justification: str


_PROHIBITED_DOWNSTREAM = (
    "evidence_bundle_loader_legacy",
    "evidence_bundle_composer",  # general cutover role — still unauthorized
    "evidence_bundle_composer_consume",  # CONSUME flag unwired in WP-ET-09
    "knowledge_layer",
    "business_findings_engine",
    "guidance_decision_home",
    "merchant_dashboard_ui",
    "merchant_evidence_registry",
    "bfsv_harness",
    "reality_validation",
    "recovery_terminal_stop",  # still driven by legacy Purchase Truth
)

_SHADOW_COMPOSER = "evidence_bundle_composer_shadow"
_GATE_C = "gate_c_harness"


def _family_permitted() -> tuple[str, ...]:
    return (
        "evidence_accounting_v1",
        "gate_a_harness",
        "gate_b_harness",
        "ops_admin_diagnostics_read",
        _SHADOW_COMPOSER,
        _GATE_C,
    )


# Produced artifacts: Observations + family Evidence + Bundle shadow
CONSUMER_ELIGIBILITY_MATRIX_V1: tuple[ConsumerEligibilityRowV1, ...] = (
    ConsumerEligibilityRowV1(
        producer="observation_shadow_dual_write_v1 / C-07 Observation Normalizer",
        artifact="CanonicalObservationV1",
        permitted_consumers=(
            "purchase_truth_authority",
            "communication_truth_authority",
            "family_authorities_future",
            "evidence_accounting_v1",
            "gate_a_harness",
            "ops_admin_diagnostics_read",
        ),
        prohibited_consumers=_PROHIBITED_DOWNSTREAM
        + ("evidence_bundle_composer_consume",),
        activation_condition=(
            "CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE=ON for produce; "
            "C-13/C-14 may also materialize observations when "
            "CARTFLOW_EVIDENCE_DUAL_WRITE=ON"
        ),
        justification=(
            "Architecture: Authorities read observations only; Bundle/Knowledge/Findings "
            "must not treat Raw or Observations as Findings authority."
        ),
    ),
    ConsumerEligibilityRowV1(
        producer="purchase_evidence_publisher_v1 / C-13 Purchase Truth Authority",
        artifact="EvidenceTruthRecordV1 (purchase_confirmed_v1)",
        permitted_consumers=_family_permitted(),
        prohibited_consumers=_PROHIBITED_DOWNSTREAM,
        activation_condition=(
            "CARTFLOW_EVIDENCE_DUAL_WRITE=ON for Evidence produce; "
            "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW=ON for Composer shadow read"
        ),
        justification=(
            "Truth Before Consumption: Evidence may be Eligible but not Consumable. "
            "Composer shadow may project; KL/Findings consume remains prohibited."
        ),
    ),
    ConsumerEligibilityRowV1(
        producer="communication_evidence_publisher_v1 / C-14 Communication Truth Authority",
        artifact="EvidenceTruthRecordV1 (message_lifecycle_v1)",
        permitted_consumers=_family_permitted(),
        prohibited_consumers=_PROHIBITED_DOWNSTREAM,
        activation_condition=(
            "CARTFLOW_EVIDENCE_DUAL_WRITE=ON for Evidence produce; "
            "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW=ON for Composer shadow read"
        ),
        justification=(
            "Sent ≠ Delivered enforced in Evidence payload; KL/Findings must not consume."
        ),
    ),
    ConsumerEligibilityRowV1(
        producer="cart_evidence_publisher_v1 / C-11 Cart Truth Authority",
        artifact="EvidenceTruthRecordV1 (cart_state_v1)",
        permitted_consumers=_family_permitted(),
        prohibited_consumers=_PROHIBITED_DOWNSTREAM,
        activation_condition=(
            "CARTFLOW_EVIDENCE_DUAL_WRITE=ON for Evidence produce; "
            "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW=ON for Composer shadow read"
        ),
        justification="Cart Evidence shadow; Composer may project; KL/Findings prohibited.",
    ),
    ConsumerEligibilityRowV1(
        producer="recovery_evidence_publisher_v1 / C-12 Recovery Truth Authority",
        artifact="EvidenceTruthRecordV1 (recovery_progression_v1)",
        permitted_consumers=_family_permitted(),
        prohibited_consumers=_PROHIBITED_DOWNSTREAM,
        activation_condition=(
            "CARTFLOW_EVIDENCE_DUAL_WRITE=ON for Evidence produce; "
            "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW=ON for Composer shadow read"
        ),
        justification=(
            "Lifecycle Truth Contract aligned; must not weaken purchase stop; "
            "KL/Findings prohibited."
        ),
    ),
    ConsumerEligibilityRowV1(
        producer="product_evidence_publisher_v1 / C-10 Product Truth Authority",
        artifact="EvidenceTruthRecordV1 (product_interest_window_v1)",
        permitted_consumers=_family_permitted() + ("bfsv_exp1_class_check_synthetic",),
        prohibited_consumers=_PROHIBITED_DOWNSTREAM + ("bfsv_harness",),
        activation_condition=(
            "CARTFLOW_EVIDENCE_DUAL_WRITE=ON for Evidence produce; "
            "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW=ON for Composer shadow read"
        ),
        justification=(
            "ATC is not a view; BFSV not resumed — synthetic class check only."
        ),
    ),
    ConsumerEligibilityRowV1(
        producer="behaviour_evidence_publisher_v1 / C-15 Behaviour Truth Authority",
        artifact="EvidenceTruthRecordV1 (hesitation_reason_v1)",
        permitted_consumers=_family_permitted(),
        prohibited_consumers=_PROHIBITED_DOWNSTREAM,
        activation_condition=(
            "CARTFLOW_EVIDENCE_DUAL_WRITE=ON for Evidence produce; "
            "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW=ON for Composer shadow read"
        ),
        justification="No confirmed-cause invention; KL/Findings prohibited.",
    ),
    ConsumerEligibilityRowV1(
        producer="visitor_evidence_publisher_v1 / C-09 Visitor Truth Authority",
        artifact="EvidenceTruthRecordV1 (store_visitor_window_v1)",
        permitted_consumers=_family_permitted(),
        prohibited_consumers=_PROHIBITED_DOWNSTREAM
        + ("bundle_visitor_fields", "bundle_visitor_fields_consume"),
        activation_condition=(
            "CARTFLOW_EVIDENCE_DUAL_WRITE=ON for Evidence produce; "
            "CARTFLOW_EVIDENCE_VISITOR_BUNDLE_FIELDS remains OFF for has_visitor_truth; "
            "Composer may hold Visitor Evidence refs without enabling visitor Bundle fields"
        ),
        justification=(
            "Closes INV-008 ownership; carts never proxy; Bundle visitor_* stay "
            "Unavailable/None until VISITOR_BUNDLE_FIELDS authorized."
        ),
    ),
    ConsumerEligibilityRowV1(
        producer="bundle_composer_v1 / C-16 Evidence Bundle Composer",
        artifact="EvidenceBundleRecordV1 (evidence_bundle_v1)",
        permitted_consumers=(
            "evidence_accounting_v1",
            "gate_c_harness",
            "gate_d_harness",
            "ops_admin_diagnostics_read",
            "knowledge_composer_shadow",
        ),
        prohibited_consumers=_PROHIBITED_DOWNSTREAM
        + (
            "knowledge_layer",
            "business_findings_engine",
            "merchant_dashboard_ui",
            "guidance_decision_home",
            "knowledge_composer_input",
        ),
        activation_condition=(
            "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW=ON for shadow compose/store; "
            "CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW=ON for Knowledge shadow read; "
            "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_CONSUME / KNOWLEDGE_COMPOSER_INPUT remain OFF"
        ),
        justification=(
            "EC-4: Bundle is the sole composition layer. Knowledge Composer shadow may "
            "read Bundles; production KL/Findings/UI remain prohibited."
        ),
    ),
    ConsumerEligibilityRowV1(
        producer="knowledge_composer_v1 / C-18 Knowledge Composer",
        artifact="KnowledgeRecordV1 (knowledge_record_v1)",
        permitted_consumers=(
            "evidence_accounting_v1",
            "gate_d_harness",
            "ops_admin_diagnostics_read",
            "executive_knowledge_preview",  # WP-ET-10.5 validation surface only
        ),
        prohibited_consumers=_PROHIBITED_DOWNSTREAM
        + (
            "knowledge_layer",
            "business_findings_engine",
            "merchant_dashboard_ui",
            "guidance_decision_home",
            "knowledge_composer_input",
            "home_daily_brief",
        ),
        activation_condition=(
            "CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW=ON for shadow compose/store; "
            "CARTFLOW_EXECUTIVE_KNOWLEDGE_PREVIEW=ON for validation read-only preview; "
            "CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT remains OFF and unwired; "
            "no Home / Findings connection"
        ),
        justification=(
            "Knowledge is pattern composition from Evidence Bundle only — not Findings, "
            "Guidance, or merchant-facing intelligence. Preview is temporary validation only."
        ),
    ),
)


def list_consumer_eligibility_v1() -> list[ConsumerEligibilityRowV1]:
    return list(CONSUMER_ELIGIBILITY_MATRIX_V1)


def composer_may_read_evidence_family_v1(family: str) -> bool:
    """Runtime helper: shadow Composer may read all V1 family Evidence."""
    _ = family
    return True
