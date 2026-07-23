# -*- coding: utf-8 -*-
"""
Evidence Truth Platform — WP-ET-00…10.

WP-ET-10: C-18 Knowledge Composer shadow foundation
(CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW default OFF).
No Home / Findings consumer cutover. Knowledge INPUT unwired.
"""
from __future__ import annotations

from services.evidence_truth.accounting_v1 import (
    PIPELINE_STAGES_V1,
    EvidenceAccountingLedgerV1,
    evidence_accounting_snapshot_v1,
    get_evidence_accounting_ledger_v1,
    reset_evidence_accounting_ledger_v1,
)
from services.evidence_truth.bfsv_exp1_class_check_v1 import (
    run_bfsv_exp1_class_check_persist_to_evidence_v1,
)
from services.evidence_truth.bundle_composer_v1 import (
    assert_bundle_consume_unauthorized_v1,
    bundle_consume_wired_v1,
    compose_evidence_bundle_v1,
)
from services.evidence_truth.bundle_model_v1 import (
    BUNDLE_SCHEMA_VERSION_V1,
    BundleEvidenceRefV1,
    BundleFamilySliceV1,
    EvidenceBundleRecordV1,
    validate_evidence_bundle_constitutional_v1,
)
from services.evidence_truth.bundle_shadow_compose_v1 import (
    bundle_composer_shadow_enabled,
    maybe_compose_evidence_bundle_v1,
    shadow_compose_evidence_bundle_v1,
)
from services.evidence_truth.bundle_store_v1 import (
    get_evidence_bundle_store_v1,
    reset_evidence_bundle_store_v1,
)
from services.evidence_truth.consumer_eligibility_v1 import (
    CONSUMER_ELIGIBILITY_MATRIX_V1,
    list_consumer_eligibility_v1,
)
from services.evidence_truth.contracts_v1 import (
    CONTRACT_RULE_IDS_V1,
    is_known_contract_rule_id,
)
from services.evidence_truth.eligibility_freshness_v1 import (
    EvidenceStampCandidateV1,
    EvidenceStampResultV1,
    apply_stamp_to_envelope_v1,
    assert_never_fabricate_ready_when_stale_v1,
    compute_freshness_v1,
    register_family_eligibility_predicate_v1,
    stamp_evidence_eligibility_v1,
)
from services.evidence_truth.evidence_dual_write_v1 import (
    evidence_dual_write_enabled,
    maybe_publish_behaviour_evidence_v1,
    maybe_publish_cart_evidence_v1,
    maybe_publish_communication_evidence_v1,
    maybe_publish_product_evidence_v1,
    maybe_publish_purchase_evidence_v1,
    maybe_publish_recovery_evidence_v1,
    maybe_publish_visitor_evidence_v1,
    maybe_shadow_dual_write_evidence_v1,
    shadow_dual_write_evidence_v1,
)
from services.evidence_truth.gate_b_visitor_truth_harness_v1 import (
    run_gate_b_visitor_truth_v1,
)
from services.evidence_truth.gate_c_partial_harness_v1 import (
    run_gate_c_partial_bundle_composer_v1,
)
from services.evidence_truth.gate_d_partial_harness_v1 import (
    run_gate_d_partial_knowledge_composer_v1,
)
from services.evidence_truth.knowledge_composer_v1 import (
    assert_knowledge_consume_unauthorized_v1,
    compose_knowledge_record_v1,
    knowledge_consume_wired_v1,
)
from services.evidence_truth.knowledge_model_v1 import (
    KNOWLEDGE_SCHEMA_VERSION_V1,
    KnowledgeRecordV1,
    validate_knowledge_record_constitutional_v1,
)
from services.evidence_truth.knowledge_shadow_compose_v1 import (
    knowledge_composer_shadow_enabled,
    maybe_compose_knowledge_record_v1,
    shadow_compose_knowledge_record_v1,
)
from services.evidence_truth.knowledge_store_v1 import (
    get_knowledge_record_store_v1,
    reset_knowledge_record_store_v1,
)
from services.evidence_truth.executive_knowledge_preview_v1 import (
    FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW,
    build_executive_knowledge_preview_v1,
    executive_knowledge_preview_enabled,
)
from services.evidence_truth.evidence_model_v1 import (
    EvidenceTruthRecordV1,
    validate_evidence_constitutional_metadata_v1,
)
from services.evidence_truth.evidence_store_v1 import (
    get_evidence_truth_store_v1,
    reset_evidence_truth_store_v1,
)
from services.evidence_truth.families_v1 import (
    EVIDENCE_FAMILIES_V1,
    EvidenceFamily,
    get_evidence_family,
    list_evidence_families,
)
from services.evidence_truth.flags_v1 import (
    FLAG_BUNDLE_COMPOSER_CONSUME,
    FLAG_BUNDLE_COMPOSER_SHADOW,
    FLAG_EVIDENCE_DUAL_WRITE,
    FLAG_FINDINGS_COMPOSER_INPUT,
    FLAG_KNOWLEDGE_COMPOSER_INPUT,
    FLAG_KNOWLEDGE_COMPOSER_SHADOW,
    FLAG_OBSERVATION_DUAL_WRITE,
    FLAG_VISITOR_BUNDLE_FIELDS,
    EVIDENCE_TRUTH_FLAGS_V1,
    evidence_truth_flag_enabled,
    evidence_truth_flags_snapshot,
)
from services.evidence_truth.gate_a_evidence_partial_harness_v1 import (
    run_gate_a_partial_observation_evidence_v1,
)
from services.evidence_truth.gate_a_harness_v1 import run_gate_a_harness_v1
from services.evidence_truth.gate_a_partial_harness_v1 import (
    run_gate_a_partial_raw_observation_v1,
)
from services.evidence_truth.gates_v1 import (
    EVIDENCE_TRUTH_GATES_V1,
    EvidenceTruthGate,
    get_evidence_truth_gate,
)
from services.evidence_truth.kernel_v1 import (
    CONFIDENCE_GRADES_V1,
    CONFIDENCE_UNKNOWN,
    EVIDENCE_KERNEL_SCHEMA_VERSION,
    EVIDENCE_PLATFORM_VERSION,
    READINESS_STATES_V1,
    READINESS_UNKNOWN,
    REJECT_REASON_CODES_V1,
    ConfidenceGrade,
    EvidenceEnvelopeV1,
    EvidenceFreshnessV1,
    EvidenceSourceRefV1,
    EvidenceValidationError,
    ObservedPeriodV1,
    ReadinessState,
    RejectReasonCode,
)
from services.evidence_truth.observation_model_v1 import (
    CanonicalObservationV1,
    validate_observation_constitutional_metadata_v1,
)
from services.evidence_truth.observation_shadow_dual_write_v1 import (
    maybe_shadow_dual_write_observation_v1,
    observation_dual_write_enabled,
    shadow_dual_write_observation_v1,
)
from services.evidence_truth.observation_store_v1 import (
    get_canonical_observation_store_v1,
    reset_canonical_observation_store_v1,
)
from services.evidence_truth.observability_v1 import (
    build_evidence_observability_snapshot_v1,
    get_evidence_truth_admin_diagnostics_v1,
)
from services.evidence_truth.ownership_v1 import (
    EVIDENCE_OWNERSHIP_V1,
    EvidenceOwner,
    EvidenceQuestion,
    get_evidence_owner,
    list_evidence_ownership,
)
from services.evidence_truth.schema_registry_v1 import (
    EVIDENCE_SCHEMA_REGISTRY_V1,
    EvidenceSchemaEntryV1,
    get_evidence_schema,
    list_evidence_schemas,
    require_evidence_schema,
)
from services.evidence_truth.type_registry_v1 import (
    EvidenceTypeEntryV1,
    get_evidence_type,
    list_evidence_types,
    register_evidence_type_v1,
    require_evidence_type,
    require_evidence_type_for_publish_v1,
)
from services.evidence_truth.validation_v1 import (
    EvidenceValidationResultV1,
    validate_evidence_envelope_v1,
    validate_observed_at_in_period_v1,
    validate_readiness_transition_v1,
)
from services.evidence_truth.versioning_v1 import (
    build_evidence_id_v1,
    content_integrity_hash_v1,
    next_evidence_version_v1,
)

__all__ = [
    "BUNDLE_SCHEMA_VERSION_V1",
    "CONFIDENCE_GRADES_V1",
    "CONFIDENCE_UNKNOWN",
    "CONSUMER_ELIGIBILITY_MATRIX_V1",
    "CONTRACT_RULE_IDS_V1",
    "EVIDENCE_FAMILIES_V1",
    "EVIDENCE_KERNEL_SCHEMA_VERSION",
    "EVIDENCE_OWNERSHIP_V1",
    "EVIDENCE_PLATFORM_VERSION",
    "EVIDENCE_SCHEMA_REGISTRY_V1",
    "EVIDENCE_TRUTH_FLAGS_V1",
    "EVIDENCE_TRUTH_GATES_V1",
    "FLAG_BUNDLE_COMPOSER_CONSUME",
    "FLAG_BUNDLE_COMPOSER_SHADOW",
    "FLAG_EVIDENCE_DUAL_WRITE",
    "FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW",
    "FLAG_FINDINGS_COMPOSER_INPUT",
    "FLAG_KNOWLEDGE_COMPOSER_INPUT",
    "FLAG_KNOWLEDGE_COMPOSER_SHADOW",
    "FLAG_OBSERVATION_DUAL_WRITE",
    "FLAG_VISITOR_BUNDLE_FIELDS",
    "KNOWLEDGE_SCHEMA_VERSION_V1",
    "PIPELINE_STAGES_V1",
    "READINESS_STATES_V1",
    "READINESS_UNKNOWN",
    "REJECT_REASON_CODES_V1",
    "BundleEvidenceRefV1",
    "BundleFamilySliceV1",
    "CanonicalObservationV1",
    "ConfidenceGrade",
    "EvidenceAccountingLedgerV1",
    "EvidenceBundleRecordV1",
    "EvidenceEnvelopeV1",
    "EvidenceFamily",
    "EvidenceFreshnessV1",
    "EvidenceOwner",
    "EvidenceQuestion",
    "EvidenceSchemaEntryV1",
    "EvidenceSourceRefV1",
    "EvidenceStampCandidateV1",
    "EvidenceStampResultV1",
    "EvidenceTruthGate",
    "EvidenceTruthRecordV1",
    "EvidenceTypeEntryV1",
    "EvidenceValidationError",
    "EvidenceValidationResultV1",
    "KnowledgeRecordV1",
    "ObservedPeriodV1",
    "ReadinessState",
    "RejectReasonCode",
    "apply_stamp_to_envelope_v1",
    "assert_bundle_consume_unauthorized_v1",
    "assert_knowledge_consume_unauthorized_v1",
    "assert_never_fabricate_ready_when_stale_v1",
    "build_evidence_id_v1",
    "build_evidence_observability_snapshot_v1",
    "build_executive_knowledge_preview_v1",
    "bundle_composer_shadow_enabled",
    "bundle_consume_wired_v1",
    "compose_evidence_bundle_v1",
    "compose_knowledge_record_v1",
    "executive_knowledge_preview_enabled",
    "compute_freshness_v1",
    "content_integrity_hash_v1",
    "evidence_accounting_snapshot_v1",
    "evidence_dual_write_enabled",
    "evidence_truth_flag_enabled",
    "evidence_truth_flags_snapshot",
    "get_canonical_observation_store_v1",
    "get_evidence_accounting_ledger_v1",
    "get_evidence_bundle_store_v1",
    "get_evidence_family",
    "get_evidence_owner",
    "get_evidence_schema",
    "get_evidence_truth_admin_diagnostics_v1",
    "get_evidence_truth_gate",
    "get_evidence_truth_store_v1",
    "get_evidence_type",
    "get_knowledge_record_store_v1",
    "is_known_contract_rule_id",
    "knowledge_composer_shadow_enabled",
    "knowledge_consume_wired_v1",
    "list_consumer_eligibility_v1",
    "list_evidence_families",
    "list_evidence_ownership",
    "list_evidence_schemas",
    "list_evidence_types",
    "maybe_compose_evidence_bundle_v1",
    "maybe_compose_knowledge_record_v1",
    "maybe_publish_behaviour_evidence_v1",
    "maybe_publish_cart_evidence_v1",
    "maybe_publish_communication_evidence_v1",
    "maybe_publish_product_evidence_v1",
    "maybe_publish_purchase_evidence_v1",
    "maybe_publish_recovery_evidence_v1",
    "maybe_publish_visitor_evidence_v1",
    "maybe_shadow_dual_write_evidence_v1",
    "maybe_shadow_dual_write_observation_v1",
    "next_evidence_version_v1",
    "observation_dual_write_enabled",
    "register_evidence_type_v1",
    "register_family_eligibility_predicate_v1",
    "require_evidence_schema",
    "require_evidence_type",
    "require_evidence_type_for_publish_v1",
    "reset_canonical_observation_store_v1",
    "reset_evidence_accounting_ledger_v1",
    "reset_evidence_bundle_store_v1",
    "reset_evidence_truth_store_v1",
    "reset_knowledge_record_store_v1",
    "run_bfsv_exp1_class_check_persist_to_evidence_v1",
    "run_gate_a_harness_v1",
    "run_gate_a_partial_observation_evidence_v1",
    "run_gate_a_partial_raw_observation_v1",
    "run_gate_b_visitor_truth_v1",
    "run_gate_c_partial_bundle_composer_v1",
    "run_gate_d_partial_knowledge_composer_v1",
    "shadow_compose_evidence_bundle_v1",
    "shadow_compose_knowledge_record_v1",
    "shadow_dual_write_evidence_v1",
    "shadow_dual_write_observation_v1",
    "stamp_evidence_eligibility_v1",
    "validate_evidence_bundle_constitutional_v1",
    "validate_evidence_constitutional_metadata_v1",
    "validate_evidence_envelope_v1",
    "validate_knowledge_record_constitutional_v1",
    "validate_observation_constitutional_metadata_v1",
    "validate_observed_at_in_period_v1",
    "validate_readiness_transition_v1",
]
