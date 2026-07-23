# -*- coding: utf-8 -*-
"""WP-ET-00 Evidence Truth foundation spine — library tests only."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from services.evidence_truth import (
    EVIDENCE_FAMILIES_V1,
    EVIDENCE_KERNEL_SCHEMA_VERSION,
    EVIDENCE_OWNERSHIP_V1,
    EVIDENCE_TRUTH_FLAGS_V1,
    EVIDENCE_TRUTH_GATES_V1,
    READINESS_STATES_V1,
    ConfidenceGrade,
    EvidenceEnvelopeV1,
    EvidenceFreshnessV1,
    EvidenceSourceRefV1,
    ObservedPeriodV1,
    build_evidence_id_v1,
    content_integrity_hash_v1,
    evidence_truth_flag_enabled,
    evidence_truth_flags_snapshot,
    get_evidence_owner,
    get_evidence_type,
    list_evidence_families,
    list_evidence_types,
    next_evidence_version_v1,
    validate_evidence_envelope_v1,
    validate_readiness_transition_v1,
)
from services.evidence_truth.families_v1 import FAMILY_PURCHASE, FAMILY_VISITOR
from services.evidence_truth.kernel_v1 import (
    CONFIDENCE_HIGH,
    READINESS_READY,
    READINESS_TRUSTED,
    READINESS_UNKNOWN,
    REJECT_GUIDANCE_FIELD_FORBIDDEN,
    REJECT_MISSING_SOURCES,
)
from services.evidence_truth.ownership_v1 import (
    QUESTION_TRAFFIC_TRUTH,
    QUESTION_VISITOR_TRUTH,
    owner_for_family,
)


def _valid_envelope(**overrides):
    base = dict(
        evidence_family=FAMILY_PURCHASE,
        evidence_type="purchase_confirmed_v1",
        evidence_id=build_evidence_id_v1(
            evidence_family=FAMILY_PURCHASE,
            evidence_type="purchase_confirmed_v1",
            store_slug="demo",
            subject="cart:1",
        ),
        evidence_version=1,
        store_slug="demo",
        subject="cart:1",
        observed_period=ObservedPeriodV1(start="2026-07-23T00:00:00+00:00"),
        as_of="2026-07-23T12:00:00+00:00",
        readiness=READINESS_READY,
        confidence=CONFIDENCE_HIGH,
        freshness=EvidenceFreshnessV1(observed_at="2026-07-23T11:00:00+00:00"),
        sources=(EvidenceSourceRefV1(observation_ref="obs:purchase:1", channel="api"),),
        schema_version=EVIDENCE_KERNEL_SCHEMA_VERSION,
        payload={"amount": 10},
        provenance="test",
    )
    base.update(overrides)
    return EvidenceEnvelopeV1(**base)


def test_seven_canonical_families_registered():
    assert len(EVIDENCE_FAMILIES_V1) == 7
    assert len(list_evidence_families()) == 7
    assert FAMILY_VISITOR in EVIDENCE_FAMILIES_V1


def test_ownership_visitor_and_traffic_same_owner():
    v = get_evidence_owner(QUESTION_VISITOR_TRUTH)
    t = get_evidence_owner(QUESTION_TRAFFIC_TRUTH)
    assert v is not None and t is not None
    assert v.owner == t.owner == "visitor_truth_authority"
    assert len(EVIDENCE_OWNERSHIP_V1) >= 12


def test_type_registry_one_declared_type_per_family():
    types = list_evidence_types()
    assert len(types) == 7
    families = {t.evidence_family for t in types}
    assert families == set(EVIDENCE_FAMILIES_V1)
    for t in types:
        assert t.status == "declared"
        assert t.owner_module == owner_for_family(t.evidence_family)


def test_readiness_vocabulary_complete():
    assert READINESS_STATES_V1 == frozenset(
        {"unknown", "unavailable", "insufficient", "conflicting", "ready", "trusted"}
    )


def test_readiness_transition_rules():
    assert validate_readiness_transition_v1(READINESS_UNKNOWN, READINESS_READY).ok
    assert validate_readiness_transition_v1(READINESS_READY, READINESS_TRUSTED).ok
    assert not validate_readiness_transition_v1(READINESS_TRUSTED, READINESS_READY).ok
    assert validate_readiness_transition_v1(READINESS_READY, READINESS_READY).ok


def test_envelope_validation_ok():
    result = validate_evidence_envelope_v1(_valid_envelope())
    assert result.ok, result.errors


def test_envelope_rejects_missing_sources():
    env = _valid_envelope(sources=())
    result = validate_evidence_envelope_v1(env)
    assert not result.ok
    assert REJECT_MISSING_SOURCES in result.reason_codes


def test_envelope_rejects_guidance_payload_keys():
    env = _valid_envelope(payload={"guidance": "buy now", "amount": 1})
    result = validate_evidence_envelope_v1(env)
    assert not result.ok
    assert REJECT_GUIDANCE_FIELD_FORBIDDEN in result.reason_codes


def test_envelope_rejects_unknown_type():
    env = _valid_envelope(evidence_type="not_a_real_type")
    result = validate_evidence_envelope_v1(env)
    assert not result.ok


def test_versioning_primitives():
    eid = build_evidence_id_v1(
        evidence_family=FAMILY_VISITOR,
        evidence_type="store_visitor_window_v1",
        store_slug="Demo",
        subject="store",
        window_key="2026-07-23",
    )
    assert eid.startswith("visitor|store_visitor_window_v1|demo|store|")
    assert next_evidence_version_v1(None) == 1
    assert next_evidence_version_v1(1) == 2
    assert next_evidence_version_v1(supersedes=3) == 4
    h1 = content_integrity_hash_v1({"a": 1, "b": 2})
    h2 = content_integrity_hash_v1({"b": 2, "a": 1})
    assert h1 == h2
    assert len(h1) == 64


def test_flags_default_off_and_unknown_fail_closed():
    snap = evidence_truth_flags_snapshot(environ={})
    assert set(snap) == set(EVIDENCE_TRUTH_FLAGS_V1)
    assert all(v is False for v in snap.values())
    assert evidence_truth_flag_enabled("CARTFLOW_EVIDENCE_DUAL_WRITE", environ={}) is False
    assert (
        evidence_truth_flag_enabled(
            "CARTFLOW_EVIDENCE_DUAL_WRITE",
            environ={"CARTFLOW_EVIDENCE_DUAL_WRITE": "1"},
        )
        is True
    )
    assert evidence_truth_flag_enabled("CARTFLOW_NOT_A_FLAG", environ={"CARTFLOW_NOT_A_FLAG": "1"}) is False


def test_gates_a_through_g_declared_f_g_not_authorized():
    assert set(EVIDENCE_TRUTH_GATES_V1) == {"A", "B", "C", "D", "E", "F", "G"}
    assert EVIDENCE_TRUTH_GATES_V1["F"].execution_authorized is False
    assert EVIDENCE_TRUTH_GATES_V1["G"].execution_authorized is False


def test_package_has_no_forbidden_runtime_imports():
    """Spine must not import Findings/Knowledge/Bundle loaders/main (DAG safety)."""
    root = Path(__file__).resolve().parents[1] / "services" / "evidence_truth"
    forbidden_prefixes = (
        "services.business_findings",
        "services.knowledge_",
        "services.merchant_daily_brief",
        "services.merchant_decision",
        "main",
    )
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for bad in forbidden_prefixes:
                        assert not alias.name.startswith(bad), f"{path.name} imports {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                for bad in forbidden_prefixes:
                    assert not node.module.startswith(bad), f"{path.name} imports {node.module}"


def test_get_evidence_type_lookup():
    entry = get_evidence_type(FAMILY_PURCHASE, "purchase_confirmed_v1")
    assert entry is not None
    assert entry.schema_version == "purchase_evidence_v1"


def test_confidence_grade_type_alias_exported():
    # Smoke: typing alias remains importable for future publishers.
    assert ConfidenceGrade is str or isinstance("high", ConfidenceGrade)
