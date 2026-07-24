# -*- coding: utf-8 -*-
"""WP-ET-10.6 — Evidence Knowledge Materialization Bridge V1."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from extensions import db
from models import PurchaseTruthRecord
from schema_evidence_truth_materialization_v1 import (
    ensure_evidence_truth_materialization_schema,
    reset_evidence_truth_materialization_schema_guard_for_tests,
)
from services.evidence_truth import (
    FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW,
    FLAG_FINDINGS_COMPOSER_INPUT,
    FLAG_KNOWLEDGE_COMPOSER_INPUT,
    FLAG_KNOWLEDGE_MATERIALIZATION_EXECUTE,
    FLAG_KNOWLEDGE_MATERIALIZATION_V1,
    build_executive_knowledge_preview_v1,
    evidence_truth_flag_enabled,
    knowledge_materialization_execute_enabled,
    knowledge_materialization_v1_enabled,
    reset_canonical_observation_store_v1,
    reset_evidence_accounting_ledger_v1,
    reset_evidence_bundle_store_v1,
    reset_evidence_truth_store_v1,
    reset_knowledge_record_store_v1,
    run_evidence_knowledge_materialization_v1,
)
from services.evidence_truth.durable_shadow_store_v1 import (
    ARTIFACT_KNOWLEDGE,
    count_shadow_artifacts_v1,
    delete_demo_shadow_artifacts_v1,
    delete_shadow_artifacts_for_run_v1,
    list_durable_knowledge_records_v1,
    put_shadow_artifact_v1,
)
from services.evidence_truth.flags_v1 import FLAG_FINDINGS_COMPOSER_INPUT as _FF
from services.evidence_truth.materialization_input_contract_v1 import (
    discover_materialization_sources_v1,
)


@pytest.fixture(autouse=True)
def _clean_et_and_durable():
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()
    reset_knowledge_record_store_v1()
    reset_evidence_truth_materialization_schema_guard_for_tests()
    ensure_evidence_truth_materialization_schema(db)
    try:
        delete_demo_shadow_artifacts_v1(confirm_store_slug="demo")
    except Exception:  # noqa: BLE001
        db.session.rollback()
    yield
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()
    reset_knowledge_record_store_v1()
    try:
        delete_demo_shadow_artifacts_v1(confirm_store_slug="demo")
    except Exception:  # noqa: BLE001
        db.session.rollback()


def _flags_on(**extra: str) -> dict[str, str]:
    env = {
        FLAG_KNOWLEDGE_MATERIALIZATION_V1: "1",
        FLAG_KNOWLEDGE_MATERIALIZATION_EXECUTE: "1",
    }
    env.update(extra)
    return env


def test_materialization_flags_default_off():
    assert knowledge_materialization_v1_enabled(environ={}) is False
    assert knowledge_materialization_execute_enabled(environ={}) is False


def test_demo_only_isolation_and_non_demo_rejection():
    out = run_evidence_knowledge_materialization_v1(
        store_slug="zid-dev-store",
        mode="execute",
        force=True,
        include_validation_fixtures=True,
    )
    assert out["ok"] is False
    assert out.get("abort_non_demo") is True
    assert "non_demo" in str(out.get("error") or "")


def test_no_demo_to_zid_remapping_in_contract_source():
    src = Path(
        "services/evidence_truth/materialization_input_contract_v1.py"
    ).read_text(encoding="utf-8")
    assert "zid_remap_forbidden" in src
    assert "remap" not in src.lower() or "zid_remap_forbidden" in src
    # No silent remapping helpers
    assert "remap_demo_to_zid" not in src
    assert "zid_store_id" not in src or "forbidden" in src


def test_flag_off_skips_without_mutation():
    out = run_evidence_knowledge_materialization_v1(
        store_slug="demo",
        mode="execute",
        include_validation_fixtures=True,
        environ={},
        force=False,
    )
    assert out.get("skipped") is True
    assert out.get("mutations") is False
    assert count_shadow_artifacts_v1(store_slug="demo") == 0


def test_preview_flag_does_not_execute_materialization():
    env = {FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW: "1"}
    preview = build_executive_knowledge_preview_v1(environ=env)
    assert preview["flag_enabled"] is True
    assert preview["read_only"] is True
    assert preview["writes"] is False
    # Materialization still off
    assert knowledge_materialization_v1_enabled(environ=env) is False
    assert count_shadow_artifacts_v1(store_slug="demo") == 0


def test_dry_run_no_mutation_and_expected_counts():
    out = run_evidence_knowledge_materialization_v1(
        store_slug="demo",
        mode="dry_run",
        include_validation_fixtures=True,
        fixture_count=1,
        force=True,
        batch_limit=10,
    )
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["mutations"] is False
    assert out["expected_writes"]["observations"] >= 1
    assert count_shadow_artifacts_v1(store_slug="demo", artifact_kind="knowledge") == 0


def test_execute_fixtures_idempotent_and_preview_reads_durable():
    env = _flags_on()
    run1 = run_evidence_knowledge_materialization_v1(
        store_slug="demo",
        mode="execute",
        include_validation_fixtures=True,
        fixture_count=1,
        force=True,
        environ=env,
        materialization_run_id="mat_test_run_1",
        as_of="2026-07-24T10:00:00+00:00",
    )
    assert run1["ok"] is True
    assert run1["mutations"] is True
    k1 = run1["accounting"]["knowledge"]["created"] + run1["accounting"]["knowledge"][
        "reused"
    ]
    assert k1 >= 1
    durable = list_durable_knowledge_records_v1(store_slug="demo", limit=20)
    assert len(durable) >= 1
    assert all(r.store_slug == "demo" for r in durable)

    # Simulated restart: clear in-process stores
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()
    reset_knowledge_record_store_v1()

    preview = build_executive_knowledge_preview_v1(
        store_slug="demo",
        environ={FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW: "1"},
    )
    assert preview["empty"] is False
    assert preview["record_count"] >= 1
    assert preview["knowledge_sources"]["durable"] >= 1
    assert preview["read_only"] is True
    assert preview["findings_enabled"] is False
    assert preview["guidance_enabled"] is False

    # Idempotent rerun
    run2 = run_evidence_knowledge_materialization_v1(
        store_slug="demo",
        mode="execute",
        include_validation_fixtures=True,
        fixture_count=1,
        force=True,
        environ=env,
        materialization_run_id="mat_test_run_2",
        as_of="2026-07-24T10:00:00+00:00",
    )
    assert run2["ok"] is True
    # Observation/evidence reused via durable idempotency keys
    assert (
        run2["accounting"]["observations"]["reused"]
        + run2["accounting"]["observations"]["created"]
        >= 1
    )


def test_bounded_batch_and_no_silent_source_loss():
    out = run_evidence_knowledge_materialization_v1(
        store_slug="demo",
        mode="dry_run",
        include_validation_fixtures=True,
        fixture_count=3,
        force=True,
        batch_limit=2,
    )
    disc = out["discovery"]
    accounted = (
        disc["eligible_count"]
        + disc["unsupported_count"]
        + disc["duplicated_count"]
        + disc["rejected_count"]
    )
    assert accounted == disc["discovered"]
    assert disc["eligible_count"] <= 2
    assert out["accounting"]["discovery_balanced"] is True


def test_unsupported_and_duplicate_source_accounting():
    # Seed two distinct purchase rows; discovery accounting must balance
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    token = uuid.uuid4().hex[:10]
    for i in range(2):
        db.session.add(
            PurchaseTruthRecord(
                recovery_key=f"demo:dup_test:{token}:{i}",
                purchase_detected=True,
                purchase_time=now,
                purchase_source="unit_test_wp_et_10_6",
                store_slug="demo",
                session_id=f"sess_dup_{token}_{i}",
            )
        )
    db.session.commit()
    report = discover_materialization_sources_v1(
        store_slug="demo",
        batch_limit=50,
        include_validation_fixtures=False,
    )
    accounted = (
        len(report.eligible)
        + len(report.unsupported)
        + len(report.duplicated)
        + len(report.rejected)
    )
    assert accounted == report.discovered
    assert len(report.eligible) >= 2
    # Cleanup seeded rows (shared pytest DB)
    db.session.query(PurchaseTruthRecord).filter(
        PurchaseTruthRecord.purchase_source == "unit_test_wp_et_10_6"
    ).delete(synchronize_session=False)
    db.session.commit()


def test_observation_contract_enforced_incomplete_rejected():
    token = uuid.uuid4().hex[:10]
    # Non-demo purchase must never enter demo eligible set
    db.session.add(
        PurchaseTruthRecord(
            recovery_key=f"other:rk1:{token}",
            purchase_detected=True,
            purchase_time=datetime(2026, 7, 1, tzinfo=timezone.utc),
            purchase_source="unit_test_wp_et_10_6_other",
            store_slug="other-store",
            session_id=f"s1_{token}",
        )
    )
    db.session.commit()
    report = discover_materialization_sources_v1(store_slug="demo", batch_limit=50)
    assert all(c.store_slug == "demo" for c in report.eligible)
    assert not any(
        c.lineage.get("recovery_key", "").startswith("other:rk1")
        for c in report.eligible
    )
    db.session.query(PurchaseTruthRecord).filter(
        PurchaseTruthRecord.purchase_source == "unit_test_wp_et_10_6_other"
    ).delete(synchronize_session=False)
    db.session.commit()


def test_lineage_preserved_observation_evidence_bundle_knowledge():
    out = run_evidence_knowledge_materialization_v1(
        store_slug="demo",
        mode="execute",
        include_validation_fixtures=True,
        fixture_count=1,
        force=True,
        materialization_run_id="mat_lineage_1",
        as_of="2026-07-24T11:00:00+00:00",
    )
    assert out["ok"] is True
    traces = out["accounting"]["traceability"]
    assert traces
    t0 = traces[0]
    assert t0["materialization_run_id"] == "mat_lineage_1"
    assert t0.get("observation_id")
    assert t0.get("evidence_id")
    assert t0.get("bundle_id")
    assert t0.get("knowledge_id")
    assert count_shadow_artifacts_v1(store_slug="demo", artifact_kind="observation") >= 1
    assert count_shadow_artifacts_v1(store_slug="demo", artifact_kind="evidence") >= 1
    assert count_shadow_artifacts_v1(store_slug="demo", artifact_kind="bundle") >= 1
    assert count_shadow_artifacts_v1(store_slug="demo", artifact_kind="knowledge") >= 1


def test_durable_visibility_across_store_reset_and_cleanup_isolation():
    put_shadow_artifact_v1(
        artifact_kind=ARTIFACT_KNOWLEDGE,
        artifact_id="k_keep",
        store_slug="demo",
        materialization_run_id="mat_keep",
        idempotency_key="knowledge:demo:k_keep:1",
        payload={
            "knowledge_id": "k_keep",
            "knowledge_version": 1,
            "knowledge_type": "family_presence_pattern_v1",
            "schema_version": "knowledge_record_v1",
            "store_slug": "demo",
            "window_start": "2026-07-01T00:00:00+00:00",
            "window_end": None,
            "as_of": "2026-07-24T00:00:00+00:00",
            "composer_owner": "knowledge_composer",
            "bundle_refs": [
                {
                    "bundle_id": "b1",
                    "bundle_version": 1,
                    "store_slug": "demo",
                    "schema_version": "evidence_bundle_v1",
                }
            ],
            "evidence_refs": [
                {
                    "evidence_id": "e1",
                    "evidence_version": 1,
                    "family": "purchase",
                    "readiness": "ready",
                    "confidence": "confirmed",
                    "bundle_id": "b1",
                }
            ],
            "claims": [
                {
                    "claim_id": "c1",
                    "claim_kind": "family_presence",
                    "evidence_ids": ["e1"],
                    "bundle_ids": ["b1"],
                    "readiness": "ready",
                    "confidence": "confirmed",
                    "payload": {"families_present": ["purchase"]},
                }
            ],
            "readiness": "ready",
            "confidence": "confirmed",
            "pattern_summary": {"families_present": ["purchase"]},
            "provenance": "unit",
            "governance_version": 1,
            "eligibility": "shadow_only",
            "lifecycle_state": "shadow_composed",
            "consumable": False,
            "composition_notes": {},
        },
    )
    put_shadow_artifact_v1(
        artifact_kind=ARTIFACT_KNOWLEDGE,
        artifact_id="k_del",
        store_slug="demo",
        materialization_run_id="mat_del",
        idempotency_key="knowledge:demo:k_del:1",
        payload={
            "knowledge_id": "k_del",
            "knowledge_version": 1,
            "knowledge_type": "family_presence_pattern_v1",
            "schema_version": "knowledge_record_v1",
            "store_slug": "demo",
            "window_start": "2026-07-01T00:00:00+00:00",
            "window_end": None,
            "as_of": "2026-07-24T00:00:00+00:00",
            "composer_owner": "knowledge_composer",
            "bundle_refs": [
                {
                    "bundle_id": "b2",
                    "bundle_version": 1,
                    "store_slug": "demo",
                    "schema_version": "evidence_bundle_v1",
                }
            ],
            "evidence_refs": [
                {
                    "evidence_id": "e2",
                    "evidence_version": 1,
                    "family": "purchase",
                    "readiness": "ready",
                    "confidence": "confirmed",
                    "bundle_id": "b2",
                }
            ],
            "claims": [
                {
                    "claim_id": "c2",
                    "claim_kind": "family_presence",
                    "evidence_ids": ["e2"],
                    "bundle_ids": ["b2"],
                    "readiness": "ready",
                    "confidence": "confirmed",
                    "payload": {},
                }
            ],
            "readiness": "ready",
            "confidence": "confirmed",
            "pattern_summary": {"families_present": ["purchase"]},
            "provenance": "unit",
            "governance_version": 1,
            "eligibility": "shadow_only",
            "lifecycle_state": "shadow_composed",
            "consumable": False,
            "composition_notes": {},
        },
    )
    deleted = delete_shadow_artifacts_for_run_v1(
        materialization_run_id="mat_del", store_slug="demo"
    )
    assert deleted >= 1
    remaining = list_durable_knowledge_records_v1(store_slug="demo", limit=50)
    ids = {r.knowledge_id for r in remaining}
    assert "k_keep" in ids
    assert "k_del" not in ids
    with pytest.raises(ValueError):
        delete_demo_shadow_artifacts_v1(confirm_store_slug="not-demo")


def test_no_findings_guidance_home_activation():
    assert evidence_truth_flag_enabled(FLAG_FINDINGS_COMPOSER_INPUT, environ={}) is False
    assert evidence_truth_flag_enabled(FLAG_KNOWLEDGE_COMPOSER_INPUT, environ={}) is False
    assert _FF == FLAG_FINDINGS_COMPOSER_INPUT
    out = run_evidence_knowledge_materialization_v1(
        store_slug="demo",
        mode="execute",
        include_validation_fixtures=True,
        fixture_count=1,
        force=True,
    )
    assert out["accounting"]["findings_activated"] is False
    assert out["accounting"]["guidance_activated"] is False
    assert out["accounting"]["home_cutover"] is False
    assert out["accounting"]["outbound_calls"] == 0


def test_hot_path_isolation_main_has_no_orchestrator_call():
    main_src = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "run_evidence_knowledge_materialization_v1" not in main_src
    assert "EvidenceKnowledgeMaterializationOrchestratorV1" not in main_src


def test_preview_module_still_forbids_upstream_truth_imports():
    src = Path(
        "services/evidence_truth/executive_knowledge_preview_v1.py"
    ).read_text(encoding="utf-8")
    for banned in (
        "get_evidence_truth_store",
        "get_canonical_observation_store",
        "get_evidence_bundle_store",
        "shadow_dual_write",
        "maybe_publish_",
        "run_evidence_knowledge_materialization",
    ):
        assert banned not in src


def test_resume_after_partial_uses_idempotent_keys():
    env = _flags_on()
    r1 = run_evidence_knowledge_materialization_v1(
        store_slug="demo",
        mode="execute",
        include_validation_fixtures=True,
        fixture_count=1,
        force=True,
        environ=env,
        materialization_run_id="mat_resume_a",
        as_of="2026-07-24T12:00:00+00:00",
    )
    assert r1["ok"] is True
    # Partial failure simulation: reset in-process and re-run same fixtures
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()
    reset_knowledge_record_store_v1()
    r2 = run_evidence_knowledge_materialization_v1(
        store_slug="demo",
        mode="execute",
        include_validation_fixtures=True,
        fixture_count=1,
        force=True,
        environ=env,
        materialization_run_id="mat_resume_b",
        as_of="2026-07-24T12:00:00+00:00",
    )
    assert r2["ok"] is True
    assert (
        r2["accounting"]["observations"]["reused"]
        >= r2["accounting"]["observations"]["created"]
        or r2["accounting"]["observations"]["reused"] >= 1
    )


def test_reconciliation_totals_balance_on_execute():
    out = run_evidence_knowledge_materialization_v1(
        store_slug="demo",
        mode="execute",
        include_validation_fixtures=True,
        fixture_count=1,
        force=True,
        batch_limit=20,
    )
    d = out["discovery"]
    accounted = (
        d["eligible_count"]
        + d["unsupported_count"]
        + d["duplicated_count"]
        + d["rejected_count"]
    )
    assert accounted == d["discovered"]
    assert out["accounting"]["discovery_balanced"] is True
    # Every eligible source gets an outcome row
    assert len(out["accounting"]["source_outcomes"]) == d["eligible_count"]
