# -*- coding: utf-8 -*-
"""
Gate B harness — Visitor Truth Authority (WP-ET-08 / Blueprint §9).

Proves: sole owner; carts never proxy; Unavailable honest when no channel.
Does not authorize Bundle visitor fields, BFSV, or Reality Validation.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.accounting_v1 import (
    get_evidence_accounting_ledger_v1,
    reset_evidence_accounting_ledger_v1,
)
from services.evidence_truth.evidence_dual_write_v1 import shadow_dual_write_evidence_v1
from services.evidence_truth.evidence_store_v1 import (
    get_evidence_truth_store_v1,
    reset_evidence_truth_store_v1,
)
from services.evidence_truth.families_v1 import FAMILY_VISITOR
from services.evidence_truth.flags_v1 import (
    FLAG_VISITOR_BUNDLE_FIELDS,
    evidence_truth_flag_enabled,
)
from services.evidence_truth.kernel_v1 import READINESS_READY, READINESS_UNAVAILABLE
from services.evidence_truth.observation_store_v1 import (
    get_canonical_observation_store_v1,
    reset_canonical_observation_store_v1,
)
from services.evidence_truth.observation_types_v1 import (
    RAW_KIND_CART_EVENT,
    RAW_KIND_TRAFFIC,
)
from services.evidence_truth.ownership_v1 import owner_for_family
from services.evidence_truth.visitor_proxy_detection_v1 import detect_visitor_proxy_v1


def run_gate_b_visitor_truth_v1(*, reset_global: bool = True) -> dict[str, Any]:
    """Execute Gate B synthetic checklist."""
    if reset_global:
        reset_evidence_accounting_ledger_v1()
        reset_canonical_observation_store_v1()
        reset_evidence_truth_store_v1()

    checks: list[dict[str, Any]] = []

    # B1 — sole owner registry
    owner = owner_for_family(FAMILY_VISITOR)
    checks.append(
        {
            "id": "B1_sole_owner",
            "ok": owner == "visitor_truth_authority",
            "detail": {"owner": owner},
        }
    )

    # B2 — honest presence publish
    r_ok = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_TRAFFIC,
        payload={
            "store_slug": "demo",
            "visitor_id": "v-gate-b-1",
            "session_id": "s-gate-b-1",
            "event": "store_visit",
        },
        source_channel="sdk",
        force=True,
        source="gate_b",
    )
    store = get_evidence_truth_store_v1()
    rec = store.get(str(r_ok.get("evidence_id") or ""))
    checks.append(
        {
            "id": "B2_presence_publish",
            "ok": (
                bool(r_ok.get("ok"))
                and not r_ok.get("rejected")
                and rec is not None
                and rec.owner == "visitor_truth_authority"
                and rec.consumable is False
                and rec.envelope.payload.get("bundle_visitor_fields_authorized") is False
                and rec.envelope.payload.get("has_visitor_truth_for_bundle") is False
                and rec.readiness == READINESS_READY
            ),
            "detail": {
                "readiness": getattr(rec, "readiness", None),
                "created": r_ok.get("created"),
            },
        }
    )

    # B3 — Unavailable when channel absent
    r_unavail = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_TRAFFIC,
        payload={
            "store_slug": "demo",
            "session_id": "s-no-channel",
            "event": "store_visit",
            "channel_available": False,
            "channel_status": "unavailable",
        },
        source_channel="unknown",
        force=True,
        source="gate_b",
    )
    urec = store.get(str(r_unavail.get("evidence_id") or ""))
    checks.append(
        {
            "id": "B3_unavailable_no_channel",
            "ok": (
                bool(r_unavail.get("ok"))
                and urec is not None
                and urec.readiness == READINESS_UNAVAILABLE
                and urec.envelope.payload.get("has_visitor_truth_for_bundle") is False
            ),
            "detail": {"readiness": getattr(urec, "readiness", None)},
        }
    )

    # B4 — cart event must not publish as visitor (wrong raw kind path)
    r_cart = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={
            "store_slug": "demo",
            "session_id": "s-cart-proxy",
            "event": "cart_abandoned",
        },
        force=True,
        source="gate_b",
    )
    # Cart publishes Cart Evidence — must not create Visitor Evidence for this subject
    visitor_from_cart = [
        r
        for r in store.list_recent(limit=50, family=FAMILY_VISITOR)
        if "s-cart-proxy" in r.envelope.subject
    ]
    checks.append(
        {
            "id": "B4_cart_not_visitor_evidence",
            "ok": bool(r_cart.get("ok")) and r_cart.get("evidence_family") == "cart"
            and not visitor_from_cart,
        }
    )

    # B5 — proxy detector: cart-shaped traffic payload rejected
    proxy_code = detect_visitor_proxy_v1(
        {"store_slug": "demo", "session_id": "s1", "event": "cart_abandoned"},
        raw_kind=RAW_KIND_TRAFFIC,
    )
    r_proxy = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_TRAFFIC,
        payload={
            "store_slug": "demo",
            "session_id": "s-proxy",
            "event": "cart_abandoned",
        },
        force=True,
        source="gate_b",
    )
    checks.append(
        {
            "id": "B5_proxy_detection",
            "ok": proxy_code == "proxy_cart_event"
            and bool(r_proxy.get("rejected"))
            and r_proxy.get("reason_code") == "conflict_unresolved",
            "detail": {"proxy_code": proxy_code, "result": r_proxy.get("reason_code")},
        }
    )

    # B6 — Bundle visitor fields flag remains OFF
    checks.append(
        {
            "id": "B6_bundle_visitor_flag_off",
            "ok": evidence_truth_flag_enabled(FLAG_VISITOR_BUNDLE_FIELDS, environ={})
            is False,
        }
    )

    # B7 — versions exist under visitor family only from authority path
    checks.append(
        {
            "id": "B7_visitor_versions",
            "ok": store.count(family=FAMILY_VISITOR) >= 2,
            "detail": store.snapshot().get("by_family"),
        }
    )

    passed = all(bool(c.get("ok")) for c in checks)
    return {
        "gate": "B",
        "name": "Visitor Truth",
        "passed": passed,
        "checks": checks,
        "accounting_snapshot": get_evidence_accounting_ledger_v1().snapshot(),
        "evidence_store": store.snapshot(),
        "observation_store": get_canonical_observation_store_v1().snapshot(),
        "bundle_visitor_fields_authorized": False,
        "execution_note": (
            "Synthetic force=True; production flags OFF; "
            "does not authorize Bundle visitor fields or Gate F/G"
        ),
    }
