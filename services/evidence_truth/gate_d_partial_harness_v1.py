# -*- coding: utf-8 -*-
"""
Gate D partial harness — WP-ET-10 Knowledge Composer shadow.

Proves BK invariants against Bundle input. Does not connect Home/Findings.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from services.evidence_truth.accounting_v1 import reset_evidence_accounting_ledger_v1
from services.evidence_truth.bundle_composer_v1 import compose_evidence_bundle_v1
from services.evidence_truth.bundle_store_v1 import reset_evidence_bundle_store_v1
from services.evidence_truth.evidence_dual_write_v1 import shadow_dual_write_evidence_v1
from services.evidence_truth.evidence_store_v1 import reset_evidence_truth_store_v1
from services.evidence_truth.flags_v1 import (
    FLAG_FINDINGS_COMPOSER_INPUT,
    FLAG_KNOWLEDGE_COMPOSER_INPUT,
    FLAG_KNOWLEDGE_COMPOSER_SHADOW,
    evidence_truth_flag_enabled,
)
from services.evidence_truth.knowledge_composer_v1 import (
    compose_knowledge_record_v1,
    knowledge_consume_wired_v1,
)
from services.evidence_truth.bundle_composition_rules_v1 import readiness_rank_v1
from services.evidence_truth.knowledge_composition_rules_v1 import (
    assert_no_evidence_write_imports_in_module_source_v1,
)
from services.evidence_truth.knowledge_model_v1 import (
    KNOWLEDGE_TYPE_FAMILY_PRESENCE,
    KNOWLEDGE_TYPE_READY_FAMILY_SET,
    validate_knowledge_record_constitutional_v1,
)
from services.evidence_truth.knowledge_store_v1 import (
    get_knowledge_record_store_v1,
    reset_knowledge_record_store_v1,
)
from services.evidence_truth.observation_store_v1 import reset_canonical_observation_store_v1
from services.evidence_truth.observation_types_v1 import (
    RAW_KIND_COMMUNICATION,
    RAW_KIND_PURCHASE,
)


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"id": name, "ok": bool(ok), "detail": detail}


def run_gate_d_partial_knowledge_composer_v1() -> dict[str, Any]:
    """
    Synthetic Gate D partial:

    - Knowledge from Bundle only
    - Claims carry evidence_ids (BK-3)
    - Readiness never exceeds supporting Evidence (BK-2)
    - No Evidence write imports (BK-4)
    - Routing / INPUT / Findings flags unauthorized
    - Fail closed without Bundle
    """
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()
    reset_knowledge_record_store_v1()

    checks: list[dict[str, Any]] = []

    checks.append(
        _check(
            "D0_knowledge_shadow_flag_default_off",
            evidence_truth_flag_enabled(FLAG_KNOWLEDGE_COMPOSER_SHADOW, environ={})
            is False,
        )
    )
    checks.append(
        _check(
            "D0_knowledge_input_flag_default_off",
            evidence_truth_flag_enabled(FLAG_KNOWLEDGE_COMPOSER_INPUT, environ={})
            is False,
        )
    )
    checks.append(
        _check(
            "D0_findings_flag_default_off",
            evidence_truth_flag_enabled(FLAG_FINDINGS_COMPOSER_INPUT, environ={})
            is False,
        )
    )
    checks.append(
        _check("D0_consume_unwired", knowledge_consume_wired_v1(environ={}) is False)
    )

    for raw_kind, payload in (
        (
            RAW_KIND_PURCHASE,
            {
                "store_slug": "gated",
                "recovery_key": "gated:cart-1",
                "session_id": "sess-d1",
                "purchase_completed": True,
            },
        ),
        (
            RAW_KIND_COMMUNICATION,
            {
                "store_slug": "gated",
                "message_sid": "SM_gated",
                "status": "delivered",
            },
        ),
    ):
        out = shadow_dual_write_evidence_v1(
            raw_kind=raw_kind, payload=payload, force=True
        )
        checks.append(
            _check(f"D1_seed_{raw_kind}", out.get("ok") is True, str(out.get("reason")))
        )

    bundle = compose_evidence_bundle_v1(
        store_slug="gated",
        as_of="2026-07-24T00:00:00+00:00",
        persist=True,
        environ={},
        provenance="synthetic",
    )
    checks.append(_check("D1_bundle_composed", bool(bundle.bundle_id)))

    rec = compose_knowledge_record_v1(
        store_slug="gated",
        knowledge_type=KNOWLEDGE_TYPE_FAMILY_PRESENCE,
        as_of="2026-07-24T00:00:00+00:00",
        persist=True,
        environ={},
        provenance="synthetic",
    )
    validate_knowledge_record_constitutional_v1(rec)

    checks.append(_check("D2_not_consumable", rec.consumable is False))
    checks.append(_check("D2_has_bundle_refs", len(rec.bundle_refs) >= 1))
    checks.append(_check("D2_has_evidence_refs", len(rec.evidence_refs) >= 1))
    checks.append(_check("D2_has_claims", len(rec.claims) >= 1))
    checks.append(
        _check(
            "D2_bk3_claim_evidence_ids",
            all(bool(c.evidence_ids) for c in rec.claims),
        )
    )

    # BK-2: never more certain than supporting evidence
    evid_ranks = [readiness_rank_v1(e.readiness) for e in rec.evidence_refs]
    min_evid = min(evid_ranks) if evid_ranks else 0
    certainty_ok = readiness_rank_v1(rec.readiness) <= min_evid
    for claim in rec.claims:
        for eid in claim.evidence_ids:
            src = next((e for e in rec.evidence_refs if e.evidence_id == eid), None)
            if src is not None and readiness_rank_v1(claim.readiness) > readiness_rank_v1(
                src.readiness
            ):
                certainty_ok = False
                break
    checks.append(_check("D3_bk2_never_more_certain", certainty_ok))

    stored = get_knowledge_record_store_v1().get(rec.knowledge_id)
    checks.append(_check("D4_persisted_shadow", stored is not None))

    # ready-family pattern also composes
    ready_rec = compose_knowledge_record_v1(
        store_slug="gated",
        knowledge_type=KNOWLEDGE_TYPE_READY_FAMILY_SET,
        as_of="2026-07-24T00:05:00+00:00",
        persist=True,
        environ={},
        provenance="synthetic",
    )
    checks.append(
        _check(
            "D5_ready_family_pattern",
            ready_rec.knowledge_type == KNOWLEDGE_TYPE_READY_FAMILY_SET
            and ready_rec.consumable is False,
        )
    )

    # BK-4 import scan
    et_dir = Path(__file__).resolve().parent
    offenders: list[str] = []
    for name in (
        "knowledge_composer_v1.py",
        "knowledge_shadow_compose_v1.py",
        "knowledge_model_v1.py",
    ):
        src = (et_dir / name).read_text(encoding="utf-8")
        bad = assert_no_evidence_write_imports_in_module_source_v1(src)
        for b in bad:
            offenders.append(f"{name}:{b}")
    checks.append(_check("D6_bk4_no_evidence_write", not offenders, ",".join(offenders)))

    # Fail closed without Bundle
    reset_evidence_bundle_store_v1()
    reset_knowledge_record_store_v1()
    fail_closed = False
    try:
        compose_knowledge_record_v1(store_slug="empty-kn", persist=False, environ={})
    except Exception as exc:  # noqa: BLE001
        fail_closed = "no_evidence_bundle_for_store" in str(exc)
    checks.append(_check("D7_fail_closed_without_bundle", fail_closed))

    # No Findings / Home connection markers
    checks.append(
        _check(
            "D8_no_downstream",
            rec.composition_notes.get("findings_connected") is False
            and rec.composition_notes.get("home_connected") is False
            and rec.composition_notes.get("routing_authorized") is False,
        )
    )

    passed = all(c["ok"] for c in checks)
    return {
        "gate": "D",
        "mode": "partial_shadow",
        "ok": passed,
        "checks": checks,
        "knowledge_id": rec.knowledge_id,
        "bundle_id": bundle.bundle_id,
        "consume_authorized": False,
        "routing_authorized": False,
        "findings_connected": False,
        "home_connected": False,
        "note": (
            "Synthetic force compose; production "
            "CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW remains OFF; "
            "full Gate D KL consumer parity deferred"
        ),
    }
