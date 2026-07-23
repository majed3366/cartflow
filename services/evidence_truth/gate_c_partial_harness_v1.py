# -*- coding: utf-8 -*-
"""
Gate C partial harness — WP-ET-09 Bundle Composer shadow.

Proves composition invariants against Evidence Truth (not full legacy field parity).
Does not connect Knowledge/Findings. Does not authorize consume.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from services.evidence_truth.bundle_composer_v1 import compose_evidence_bundle_v1
from services.evidence_truth.bundle_composition_rules_v1 import (
    assert_no_raw_authority_imports_in_module_source_v1,
    has_ready_flag_v1,
    readiness_rank_v1,
)
from services.evidence_truth.bundle_model_v1 import validate_evidence_bundle_constitutional_v1
from services.evidence_truth.bundle_store_v1 import (
    get_evidence_bundle_store_v1,
    reset_evidence_bundle_store_v1,
)
from services.evidence_truth.evidence_dual_write_v1 import shadow_dual_write_evidence_v1
from services.evidence_truth.evidence_store_v1 import (
    get_evidence_truth_store_v1,
    reset_evidence_truth_store_v1,
)
from services.evidence_truth.flags_v1 import (
    FLAG_BUNDLE_COMPOSER_CONSUME,
    FLAG_BUNDLE_COMPOSER_SHADOW,
    FLAG_VISITOR_BUNDLE_FIELDS,
    evidence_truth_flag_enabled,
)
from services.evidence_truth.observation_store_v1 import reset_canonical_observation_store_v1
from services.evidence_truth.observation_types_v1 import (
    RAW_KIND_CART_EVENT,
    RAW_KIND_COMMUNICATION,
    RAW_KIND_PURCHASE,
)
from services.evidence_truth.accounting_v1 import reset_evidence_accounting_ledger_v1


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"id": name, "ok": bool(ok), "detail": detail}


def run_gate_c_partial_bundle_composer_v1() -> dict[str, Any]:
    """
    Synthetic Gate C partial:

    - Compose Bundle from Evidence Truth only
    - Every present slice has evidence_refs / observation trace
    - Never more certain than source Evidence
    - Visitor fields unauthorized (flag OFF)
    - CONSUME / SHADOW flags default OFF
    - Composer modules do not import Raw authority
    - Dual-read posture: Composer may be stricter than empty legacy visitor proxy
    """
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()

    checks: list[dict[str, Any]] = []

    # Flags default OFF
    checks.append(
        _check(
            "C0_shadow_flag_default_off",
            evidence_truth_flag_enabled(FLAG_BUNDLE_COMPOSER_SHADOW, environ={})
            is False,
        )
    )
    checks.append(
        _check(
            "C0_consume_flag_default_off",
            evidence_truth_flag_enabled(FLAG_BUNDLE_COMPOSER_CONSUME, environ={})
            is False,
        )
    )
    checks.append(
        _check(
            "C0_visitor_bundle_fields_off",
            evidence_truth_flag_enabled(FLAG_VISITOR_BUNDLE_FIELDS, environ={})
            is False,
        )
    )

    # Seed Evidence via force dual-write (not production path)
    for raw_kind, payload in (
        (
            RAW_KIND_PURCHASE,
            {
                "store_slug": "gatec",
                "recovery_key": "gatec:cart-1",
                "session_id": "sess-c1",
                "purchase_completed": True,
            },
        ),
        (
            RAW_KIND_COMMUNICATION,
            {
                "store_slug": "gatec",
                "message_sid": "SM_gatec",
                "status": "delivered",
            },
        ),
        (
            RAW_KIND_CART_EVENT,
            {
                "store_slug": "gatec",
                "session_id": "sess-c1",
                "event_type": "cart_updated",
                "cart_total": 120,
            },
        ),
    ):
        out = shadow_dual_write_evidence_v1(
            raw_kind=raw_kind, payload=payload, force=True
        )
        checks.append(
            _check(f"C1_seed_{raw_kind}", out.get("ok") is True, str(out.get("reason")))
        )

    bundle = compose_evidence_bundle_v1(
        store_slug="gatec",
        as_of="2026-07-23T12:00:00+00:00",
        persist=True,
        environ={},
        provenance="synthetic",
    )
    validate_evidence_bundle_constitutional_v1(bundle)

    checks.append(_check("C2_bundle_not_consumable", bundle.consumable is False))
    checks.append(
        _check("C2_has_evidence_refs", len(bundle.evidence_refs) >= 1)
    )
    checks.append(
        _check(
            "C2_visitor_truth_false",
            bundle.has_visitor_truth is False and bundle.visitor_total is None,
        )
    )
    checks.append(
        _check(
            "C2_visitor_fields_unauthorized",
            bundle.visitor_bundle_fields_authorized is False,
        )
    )

    # Never more certain than source
    certainty_ok = True
    for ref in bundle.evidence_refs:
        slice_ = bundle.families.get(ref.family)
        if slice_ is None:
            certainty_ok = False
            break
        if readiness_rank_v1(slice_.readiness) > readiness_rank_v1(ref.readiness):
            certainty_ok = False
            break
        if slice_.has_ready and not has_ready_flag_v1(ref.readiness):
            certainty_ok = False
            break
    checks.append(_check("C3_never_more_certain", certainty_ok))

    # Traceability
    trace_ok = all(
        (r.source_observations or r.observation_refs) for r in bundle.evidence_refs
    )
    checks.append(_check("C4_trace_to_observation", trace_ok))

    # Stored
    stored = get_evidence_bundle_store_v1().get(bundle.bundle_id)
    checks.append(_check("C5_persisted_shadow", stored is not None))

    # EB-7: composer sources must not import Raw authority
    et_dir = Path(__file__).resolve().parent
    offenders: list[str] = []
    for name in (
        "bundle_composer_v1.py",
        "bundle_shadow_compose_v1.py",
        "bundle_model_v1.py",
        "bundle_composition_rules_v1.py",
    ):
        src = (et_dir / name).read_text(encoding="utf-8")
        bad = assert_no_raw_authority_imports_in_module_source_v1(src)
        for b in bad:
            offenders.append(f"{name}:{b}")
    checks.append(
        _check("C6_eb7_no_raw_authority", not offenders, ",".join(offenders))
    )

    # Dual-read posture vs legacy visitor proxy (Composer stricter / honest)
    legacy_shaped = {
        "has_visitor_truth": False,
        "visitor_total": None,  # honest legacy must already be None — not 0
        "source": "legacy_baseline_stub",
    }
    composer_visitor = {
        "has_visitor_truth": bundle.has_visitor_truth,
        "visitor_total": bundle.visitor_total,
    }
    parity_visitor_ok = (
        composer_visitor["has_visitor_truth"] == legacy_shaped["has_visitor_truth"]
        and composer_visitor["visitor_total"] is None
    )
    checks.append(
        _check(
            "C7_dual_read_visitor_stricter_or_equal",
            parity_visitor_ok,
            "composer_must_not_invent_visitor_total",
        )
    )

    # No Evidence → fail closed
    reset_evidence_truth_store_v1()
    fail_closed = False
    try:
        compose_evidence_bundle_v1(store_slug="empty-store", persist=False, environ={})
    except Exception as exc:  # noqa: BLE001 — harness asserts fail-closed
        fail_closed = "no_evidence_truth_for_store" in str(exc)
    checks.append(_check("C8_fail_closed_without_evidence", fail_closed))

    # Restore was cleared — evidence count for report
    evidence_count = get_evidence_truth_store_v1().count()

    passed = all(c["ok"] for c in checks)
    return {
        "gate": "C",
        "mode": "partial_shadow",
        "ok": passed,
        "checks": checks,
        "bundle_id": bundle.bundle_id,
        "evidence_ref_count": len(bundle.evidence_refs),
        "evidence_store_count_after_reset": evidence_count,
        "consume_authorized": False,
        "knowledge_connected": False,
        "findings_connected": False,
        "note": (
            "Synthetic force compose; production "
            "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW remains OFF; "
            "full Gate C legacy field parity deferred"
        ),
    }
