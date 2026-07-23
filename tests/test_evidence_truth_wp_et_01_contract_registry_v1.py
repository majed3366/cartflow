# -*- coding: utf-8 -*-
"""WP-ET-01 — Contract Kernel + Type Registry (Blueprint enum/schema verification)."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from services.evidence_truth import (
    CONTRACT_RULE_IDS_V1,
    EVIDENCE_KERNEL_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_REGISTRY_V1,
    EVIDENCE_TRUTH_FLAGS_V1,
    EVIDENCE_TRUTH_GATES_V1,
    READINESS_STATES_V1,
    EvidenceValidationError,
    evidence_truth_flags_snapshot,
    get_evidence_schema,
    is_known_contract_rule_id,
    list_evidence_schemas,
    list_evidence_types,
    register_evidence_type_v1,
    require_evidence_type_for_publish_v1,
    validate_observed_at_in_period_v1,
)
from services.evidence_truth.families_v1 import FAMILY_PURCHASE
from services.evidence_truth.type_registry_v1 import STATUS_DECLARED


def test_contract_rule_vocabulary_complete():
    # Blueprint §5: OE(7) + EB(8) + BK(5) + KF(5) + FG(4) = 29
    assert len(CONTRACT_RULE_IDS_V1) == 29
    assert is_known_contract_rule_id("OE-1")
    assert is_known_contract_rule_id("FG-4")
    assert not is_known_contract_rule_id("ZZ-1")


def test_schema_registry_documents_envelope_and_families():
    assert EVIDENCE_KERNEL_SCHEMA_VERSION in EVIDENCE_SCHEMA_REGISTRY_V1
    schemas = list_evidence_schemas()
    assert any(s.kind == "envelope" for s in schemas)
    family_schemas = list_evidence_schemas(kind="family_evidence")
    assert len(family_schemas) == 7
    for t in list_evidence_types():
        assert get_evidence_schema(t.schema_version) is not None


def test_register_evidence_type_idempotent_and_owner_guard():
    entry = register_evidence_type_v1(
        evidence_family=FAMILY_PURCHASE,
        evidence_type="purchase_confirmed_v1",
        schema_version="purchase_evidence_v1",
        dedupe_key_template="{store}:{type}:{subject}",
        status=STATUS_DECLARED,
        description="Proven purchase / conversion (authority not publishing yet)",
    )
    again = register_evidence_type_v1(
        evidence_family=FAMILY_PURCHASE,
        evidence_type="purchase_confirmed_v1",
        schema_version="purchase_evidence_v1",
        dedupe_key_template="{store}:{type}:{subject}",
        status=STATUS_DECLARED,
        description="Proven purchase / conversion (authority not publishing yet)",
    )
    assert entry == again

    with pytest.raises(EvidenceValidationError) as exc:
        register_evidence_type_v1(
            evidence_family=FAMILY_PURCHASE,
            evidence_type="purchase_extra_v1",
            schema_version="purchase_evidence_v1",
            dedupe_key_template="{store}:{type}:{subject}",
            owner_module="wrong_owner",
        )
    assert exc.value.reason_code == "owner_missing"


def test_register_rejects_unknown_schema():
    with pytest.raises(KeyError):
        register_evidence_type_v1(
            evidence_family=FAMILY_PURCHASE,
            evidence_type="purchase_bad_schema_v1",
            schema_version="not_a_schema_v1",
            dedupe_key_template="{store}:{type}:{subject}",
        )


def test_publish_guard_fail_closed_unknown_type():
    with pytest.raises(EvidenceValidationError) as exc:
        require_evidence_type_for_publish_v1(FAMILY_PURCHASE, "does_not_exist_v1")
    assert exc.value.reason_code == "unknown_type"

    ok = require_evidence_type_for_publish_v1(FAMILY_PURCHASE, "purchase_confirmed_v1")
    assert ok.evidence_type == "purchase_confirmed_v1"


def test_oe2_period_containment_helper():
    assert validate_observed_at_in_period_v1(
        "2026-07-23T12:00:00+00:00",
        "2026-07-23T00:00:00+00:00",
        "2026-07-24T00:00:00+00:00",
    ).ok
    assert not validate_observed_at_in_period_v1(
        "2026-07-22T12:00:00+00:00",
        "2026-07-23T00:00:00+00:00",
        "2026-07-24T00:00:00+00:00",
    ).ok


def test_readiness_enum_unchanged():
    assert READINESS_STATES_V1 == frozenset(
        {"unknown", "unavailable", "insufficient", "conflicting", "ready", "trusted"}
    )


def test_flags_still_default_off_and_gates_f_g_unauthorized():
    snap = evidence_truth_flags_snapshot(environ={})
    assert set(snap) == set(EVIDENCE_TRUTH_FLAGS_V1)
    assert all(v is False for v in snap.values())
    assert EVIDENCE_TRUTH_GATES_V1["F"].execution_authorized is False
    assert EVIDENCE_TRUTH_GATES_V1["G"].execution_authorized is False


def test_no_circular_imports_in_package():
    """Each module's import graph stays acyclic relative to forbidden upward deps."""
    root = Path(__file__).resolve().parents[1] / "services" / "evidence_truth"
    forbidden = (
        "services.business_findings",
        "services.knowledge_",
        "services.merchant_daily_brief",
        "services.merchant_decision",
        "main",
    )
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for bad in forbidden:
                    assert not node.module.startswith(bad), f"{path.name}->{node.module}"


def test_no_unapproved_production_path_imports_evidence_truth():
    """
    WP-ET-03 authorizes shadow dual-write call sites only.
    Other production modules must not import evidence_truth.
    """
    allowed = {
        "main.py",
        "services/purchase_truth.py",
        "services/whatsapp_delivery_truth_v1.py",
        "services/product_data/product_data_line_snapshots_hook_v1.py",
        "services/product_data/product_hesitation_hook_v1.py",
        "services/recovery_truth_timeline_v1.py",
    }
    repo = Path(__file__).resolve().parents[1]
    offenders: list[str] = []
    for path in repo.joinpath("services").rglob("*.py"):
        if "evidence_truth" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "services.evidence_truth" in text or "from services import evidence_truth" in text:
            rel = str(path.relative_to(repo)).replace("\\", "/")
            if rel not in allowed:
                offenders.append(rel)
    main = repo / "main.py"
    if main.exists():
        text = main.read_text(encoding="utf-8", errors="ignore")
        if "evidence_truth" in text and "main.py" not in allowed:
            offenders.append("main.py")
    assert offenders == []
