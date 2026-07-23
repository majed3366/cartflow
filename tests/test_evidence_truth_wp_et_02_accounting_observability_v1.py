# -*- coding: utf-8 -*-
"""WP-ET-02 — Accounting + Observability stubs + Gate A harness (synthetic)."""
from __future__ import annotations

import ast
from pathlib import Path

from services.evidence_truth import (
    EVIDENCE_TRUTH_FLAGS_V1,
    EVIDENCE_TRUTH_GATES_V1,
    EvidenceAccountingLedgerV1,
    evidence_truth_flags_snapshot,
    get_evidence_truth_admin_diagnostics_v1,
    reset_evidence_accounting_ledger_v1,
    run_gate_a_harness_v1,
)
from services.evidence_truth.accounting_v1 import (
    STAGE_OBSERVATION_OUT,
    STAGE_RAW_IN,
    evidence_accounting_snapshot_v1,
    get_evidence_accounting_ledger_v1,
)
from services.evidence_truth.kernel_v1 import REJECT_MISSING_SOURCES
from services.evidence_truth.observability_v1 import build_evidence_observability_snapshot_v1


def setup_function() -> None:
    reset_evidence_accounting_ledger_v1()


def teardown_function() -> None:
    reset_evidence_accounting_ledger_v1()


def test_global_ledger_zero_traffic_baseline():
    snap = evidence_accounting_snapshot_v1()
    assert snap["stage_counts"][STAGE_RAW_IN] == 0
    assert snap["rejected_total"] == 0
    assert snap["silent_loss_trips"] == 0
    admin = get_evidence_truth_admin_diagnostics_v1()
    assert admin["zero_traffic"] is True


def test_synthetic_increment_and_reject_reason_codes():
    led = EvidenceAccountingLedgerV1()
    led.increment_stage(STAGE_RAW_IN, n=5)
    led.increment_stage(STAGE_OBSERVATION_OUT, n=4)
    led.record_reject(REJECT_MISSING_SOURCES)
    inv = led.check_invariants()
    assert inv["ok"] is True
    assert inv["raw_in"] == 5
    assert inv["observation_out"] == 4
    assert inv["rejected"] == 1
    assert led.snapshot()["rejected_by_reason"][REJECT_MISSING_SOURCES] == 1


def test_silent_loss_detector_p0():
    led = EvidenceAccountingLedgerV1()
    led.increment_stage(STAGE_RAW_IN, n=1)
    led.increment_stage(STAGE_OBSERVATION_OUT, n=5)
    loss = led.detect_silent_loss()
    assert loss["tripped"] is True
    assert loss["alert_class"] == "P0"
    assert loss["silent_loss_trips"] == 1


def test_observability_stub_signals_present():
    obs = build_evidence_observability_snapshot_v1(ledger=EvidenceAccountingLedgerV1())
    for key in (
        "health",
        "freshness",
        "coverage",
        "latency",
        "volume",
        "contract_violations",
        "rejected_evidence",
        "missing_ownership",
        "evidence_accounting",
    ):
        assert key in obs
    assert obs["merchant_visible"] is False
    assert obs["freshness"]["status"] == "stub"
    assert obs["latency"]["status"] == "stub"


def test_gate_a_harness_passes_synthetically():
    report = run_gate_a_harness_v1()
    assert report["gate"] == "A"
    assert report["passed"] is True, report
    assert all(c["ok"] for c in report["checks"])
    # Global ledger must remain zero (harness uses isolated ledger)
    assert get_evidence_accounting_ledger_v1().snapshot()["stage_counts"][STAGE_RAW_IN] == 0


def test_flags_unchanged_default_off_and_gates_f_g_unauthorized():
    snap = evidence_truth_flags_snapshot(environ={})
    assert set(snap) == set(EVIDENCE_TRUTH_FLAGS_V1)
    assert all(v is False for v in snap.values())
    assert EVIDENCE_TRUTH_GATES_V1["F"].execution_authorized is False
    assert EVIDENCE_TRUTH_GATES_V1["G"].execution_authorized is False


def test_no_unapproved_production_path_imports_evidence_truth():
    """WP-ET-03/10.5: only listed shadow dual-write + Executive Knowledge Preview routes."""
    allowed = {
        "main.py",
        "services/purchase_truth.py",
        "services/whatsapp_delivery_truth_v1.py",
        "services/product_data/product_data_line_snapshots_hook_v1.py",
        "services/product_data/product_hesitation_hook_v1.py",
        "services/recovery_truth_timeline_v1.py",
        "routes/executive_knowledge_preview_v1.py",
    }
    repo = Path(__file__).resolve().parents[1]
    offenders: list[str] = []
    for path in repo.joinpath("services").rglob("*.py"):
        if "evidence_truth" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "services.evidence_truth" in text:
            rel = str(path.relative_to(repo)).replace("\\", "/")
            if rel not in allowed:
                offenders.append(rel)
    main = repo / "main.py"
    if main.exists() and "evidence_truth" in main.read_text(encoding="utf-8", errors="ignore"):
        # allowed
        pass
    for path in (repo / "routes").rglob("*.py") if (repo / "routes").exists() else []:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "evidence_truth" in text:
            rel = str(path.relative_to(repo)).replace("\\", "/")
            if rel not in allowed:
                offenders.append(rel)
    assert offenders == []


def test_package_has_no_forbidden_upward_imports():
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
