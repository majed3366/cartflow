# -*- coding: utf-8 -*-
"""
Cart Workspace Golden Scenarios V1 — constitutional engineering scenarios.

Every future sprint must pass GS-01…GS-10.
Scenarios feed the shadow pipeline only; they do not activate merchant UI.
"""
from __future__ import annotations

from typing import Any, Optional

from services.cart_workspace.admission_v1 import candidate_from_dict
from services.cart_workspace.shadow_pipeline_v1 import evaluate_candidate, shadow_snapshot
from services.cart_workspace.shadow_store_v1 import ShadowStoreV1

GOLDEN_SCENARIOS_VERSION = "v1"

# Expected projection assertions (no UI — structural truth only)
GOLDEN_SCENARIOS: dict[str, dict[str, Any]] = {
    "GS-01": {
        "title": "Normal hesitation",
        "parity_topic": "Waiting",
        "steps": [
            {
                "store_slug": "demo",
                "recovery_key": "gs01-hesitation",
                "signal_class": "hesitation",
                "proof_class": "weak",
                "evidence_ids": ["gs01-ev-weak"],
                "proof_sufficient": False,
                "automation_capable": True,
                "human_gain_exceeds_cost": False,
            }
        ],
        "expect": {
            "quiet": True,
            "zone_a_count": 0,
            "zone_b_count": 0,
            "admission_outcomes": ["do_not_admit"],
            "matrix_rows": ["R01"],
            "decision_owner": "cartflow",
        },
    },
    "GS-02": {
        "title": "Customer reply",
        "parity_topic": "Customer Reply",
        "steps": [
            {
                "store_slug": "demo",
                "recovery_key": "gs02-reply",
                "signal_class": "customer_reply",
                "proof_class": "automation_can_answer",
                "evidence_ids": ["gs02-ev-reply"],
                "proof_sufficient": True,
                "automation_capable": True,
                "human_gain_exceeds_cost": False,
            }
        ],
        "expect": {
            "quiet": True,
            "zone_a_count": 0,
            "zone_b_count": 0,
            "admission_outcomes": ["do_not_admit"],
            "matrix_rows": ["R04"],
            "decision_owner": "cartflow",
        },
    },
    "GS-03": {
        "title": "VIP / Priority Override",
        "parity_topic": "VIP",
        "steps": [
            {
                "store_slug": "demo",
                "recovery_key": "gs03-vip",
                "signal_class": "vip_detect",
                "proof_class": "override_eligible",
                "evidence_ids": ["gs03-ev-vip"],
                "proof_sufficient": True,
                "override_eligible": True,
                "expected_action": "override_decision_action",
            }
        ],
        "expect": {
            "quiet": False,
            "zone_a_count": 1,
            "zone_b_count": 0,
            "admission_outcomes": ["admit"],
            "matrix_rows": ["R07"],
            "decision_owner": "merchant",
            "override_mode": "active",
            "decision_class": "override",
        },
    },
    "GS-04": {
        "title": "Discount request",
        "parity_topic": "Customer Reply",
        "steps": [
            {
                "store_slug": "demo",
                "recovery_key": "gs04-discount",
                "signal_class": "discount_request",
                "proof_class": "approve_deny_required",
                "evidence_ids": ["gs04-ev-disc"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "approve_or_deny_discount",
            }
        ],
        "expect": {
            "quiet": False,
            "zone_a_count": 0,
            "zone_b_count": 1,
            "admission_outcomes": ["admit"],
            "matrix_rows": ["R06"],
            "decision_owner": "merchant",
            "required_action": "approve_or_deny_discount",
        },
    },
    "GS-05": {
        "title": "Purchase completed",
        "parity_topic": "Purchase",
        "steps": [
            {
                "store_slug": "demo",
                "recovery_key": "gs05-purchase",
                "signal_class": "purchase_completed",
                "proof_class": "terminal_completion",
                "evidence_ids": ["gs05-ev-buy"],
                "proof_sufficient": True,
                "journey_completed": True,
            }
        ],
        "expect": {
            "quiet": True,
            "zone_a_count": 0,
            "zone_b_count": 0,
            "admission_outcomes": ["do_not_admit"],
            "matrix_rows": ["R11"],
            "zone_d_min_completed": 1,
            "journey_phase": "completed",
        },
    },
    "GS-06": {
        "title": "Missing phone (automation can wait)",
        "parity_topic": "Missing Phone",
        "steps": [
            {
                "store_slug": "demo",
                "recovery_key": "gs06-phone",
                "signal_class": "phone_missing",
                "proof_class": "phone_status",
                "evidence_ids": ["gs06-ev-phone"],
                "proof_sufficient": False,
                "automation_capable": True,
                "is_status_only": False,
            }
        ],
        "expect": {
            "quiet": True,
            "zone_a_count": 0,
            "zone_b_count": 0,
            "admission_outcomes": ["do_not_admit"],
            "matrix_rows": ["R09", "R01"],  # R09 preferred; R01 if classified weak
            "decision_owner": "cartflow",
        },
    },
    "GS-07": {
        "title": "Duplicate webhook / same fingerprint",
        "parity_topic": "Duplicate Event",
        "steps": [
            {
                "store_slug": "demo",
                "recovery_key": "gs07-dup",
                "signal_class": "hesitation",
                "proof_class": "automation_exhausted",
                "evidence_ids": ["gs07-ev"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "approve_next_step",
            },
            {
                "store_slug": "demo",
                "recovery_key": "gs07-dup",
                "signal_class": "refresh",
                "proof_class": "automation_exhausted",
                "evidence_ids": ["gs07-ev"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "is_refresh_same_fingerprint": True,
                "expected_action": "approve_next_step",
            },
        ],
        "expect": {
            "quiet": False,
            "zone_a_count": 0,
            "zone_b_count": 1,
            "admission_outcomes": ["admit", "do_not_admit"],
            "open_decision_count": 1,
        },
    },
    "GS-08": {
        "title": "Provider outage (retryable)",
        "parity_topic": "Provider Failure",
        "steps": [
            {
                "store_slug": "demo",
                "recovery_key": "gs08-provider",
                "signal_class": "provider_failure",
                "proof_class": "retry_allowed",
                "evidence_ids": ["gs08-ev"],
                "proof_sufficient": True,
                "automation_capable": True,
                "human_gain_exceeds_cost": False,
            }
        ],
        "expect": {
            "quiet": True,
            "zone_a_count": 0,
            "zone_b_count": 0,
            "admission_outcomes": ["do_not_admit"],
            "matrix_rows": ["R12"],
            "decision_owner": "cartflow",
        },
    },
    "GS-09": {
        "title": "Merchant inactive (Decision already open)",
        "parity_topic": "Merchant Inactivity",
        "steps": [
            {
                "store_slug": "demo",
                "recovery_key": "gs09-inactive",
                "signal_class": "discount_request",
                "proof_class": "approve_deny_required",
                "evidence_ids": ["gs09-ev"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "approve_or_deny_discount",
            },
            {
                "store_slug": "demo",
                "recovery_key": "gs09-inactive",
                "signal_class": "merchant_inactive",
                "proof_class": "prior_admission",
                "evidence_ids": ["gs09-ev"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
            },
        ],
        "expect": {
            "quiet": False,
            "zone_b_count": 1,
            "open_decision_count": 1,
            "admission_outcomes": ["admit", "do_not_admit"],
            "no_re_admit": True,
        },
    },
    "GS-10": {
        "title": "Recovery completed",
        "parity_topic": "Recovery Completed",
        "steps": [
            {
                "store_slug": "demo",
                "recovery_key": "gs10-recover",
                "signal_class": "hesitation",
                "proof_class": "automation_exhausted",
                "evidence_ids": ["gs10-ev-a"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "approve_next_step",
            },
            {
                "store_slug": "demo",
                "recovery_key": "gs10-recover",
                "signal_class": "purchase_completed",
                "proof_class": "terminal_completion",
                "evidence_ids": ["gs10-ev-buy"],
                "proof_sufficient": True,
                "journey_completed": True,
            },
        ],
        "expect": {
            "quiet": True,
            "zone_a_count": 0,
            "zone_b_count": 0,
            "open_decision_count": 0,
            "zone_d_min_completed": 1,
            "journey_phase": "completed",
        },
    },
}


def list_golden_ids() -> list[str]:
    return sorted(GOLDEN_SCENARIOS.keys())


def run_golden(
    scenario_id: str,
    *,
    store: Optional[ShadowStoreV1] = None,
    reset: bool = True,
) -> dict[str, Any]:
    """Execute one golden scenario and return snapshot + assertion report."""
    meta = GOLDEN_SCENARIOS.get(scenario_id)
    if not meta:
        return {
            "ok": False,
            "error": f"unknown_golden:{scenario_id}",
            "known": list_golden_ids(),
        }

    store = store or ShadowStoreV1()
    if reset:
        store.reset()

    step_results = []
    store_slug = "demo"
    for step in meta["steps"]:
        store_slug = str(step.get("store_slug") or store_slug)
        step_results.append(evaluate_candidate(candidate_from_dict(step), store=store))

    snap = shadow_snapshot(store_slug, store=store)
    proj = snap["projection"]
    expect = meta["expect"]
    failures: list[str] = []

    def _check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    if "quiet" in expect:
        _check(bool(proj.get("quiet")) is bool(expect["quiet"]), f"quiet expected {expect['quiet']}")
    if "zone_a_count" in expect:
        _check(len(proj.get("zone_a") or []) == expect["zone_a_count"], "zone_a_count mismatch")
    if "zone_b_count" in expect:
        _check(len(proj.get("zone_b") or []) == expect["zone_b_count"], "zone_b_count mismatch")
    if "open_decision_count" in expect:
        open_n = len(snap.get("open_decision_ids") or [])
        _check(open_n == expect["open_decision_count"], f"open_decision_count {open_n}")
    if "zone_d_min_completed" in expect:
        cc = int((proj.get("zone_d") or {}).get("completed_count") or 0)
        _check(cc >= expect["zone_d_min_completed"], "zone_d completed_count low")
    if "admission_outcomes" in expect:
        got = [s["admission"]["outcome"] for s in step_results]
        _check(got == expect["admission_outcomes"], f"admission_outcomes {got}")
    if "matrix_rows" in expect:
        got_rows = [s["admission"]["matrix_row_id"] for s in step_results]
        allowed = expect["matrix_rows"]
        # Each step's row must be in allowed set (order-sensitive when len matches)
        if len(allowed) == len(got_rows) and all(isinstance(x, str) for x in allowed):
            # If first element looks like alternatives list for GS-06 style — handle union for step0
            if scenario_id == "GS-06":
                _check(got_rows[0] in allowed, f"matrix_rows {got_rows}")
            else:
                _check(got_rows == allowed, f"matrix_rows {got_rows}")
        else:
            _check(got_rows[0] in allowed, f"matrix_rows {got_rows}")
    if "decision_owner" in expect and snap.get("ownership"):
        # last ownership for subject
        owners = {o["recovery_key"]: o for o in snap["ownership"]}
        rk = meta["steps"][-1]["recovery_key"]
        own = owners.get(rk) or (snap["ownership"][-1] if snap["ownership"] else {})
        _check(own.get("decision_owner") == expect["decision_owner"], "decision_owner mismatch")
    if "override_mode" in expect and snap.get("ownership"):
        rk = meta["steps"][-1]["recovery_key"]
        owners = {o["recovery_key"]: o for o in snap["ownership"]}
        own = owners.get(rk) or {}
        _check(own.get("override_mode") == expect["override_mode"], "override_mode mismatch")
    if "journey_phase" in expect and snap.get("ownership"):
        rk = meta["steps"][-1]["recovery_key"]
        owners = {o["recovery_key"]: o for o in snap["ownership"]}
        own = owners.get(rk) or {}
        _check(own.get("journey_phase") == expect["journey_phase"], "journey_phase mismatch")
    if "decision_class" in expect and (proj.get("zone_a") or proj.get("zone_b")):
        cards = list(proj.get("zone_a") or []) + list(proj.get("zone_b") or [])
        _check(
            any(c.get("decision_class") == expect["decision_class"] for c in cards),
            "decision_class mismatch",
        )
    if "required_action" in expect:
        cards = list(proj.get("zone_b") or [])
        _check(
            any(c.get("required_action") == expect["required_action"] for c in cards),
            "required_action mismatch",
        )
    if expect.get("no_re_admit"):
        _check(len(snap.get("open_decision_ids") or []) == 1, "re-admit created duplicate")

    return {
        "ok": len(failures) == 0,
        "scenario_id": scenario_id,
        "title": meta["title"],
        "parity_topic": meta["parity_topic"],
        "failures": failures,
        "step_results": step_results,
        "snapshot": snap,
        "golden_version": GOLDEN_SCENARIOS_VERSION,
    }


def run_all_goldens(*, store: Optional[ShadowStoreV1] = None) -> dict[str, Any]:
    results = []
    for sid in list_golden_ids():
        # fresh store per scenario
        results.append(run_golden(sid, store=ShadowStoreV1(), reset=True))
    passed = sum(1 for r in results if r.get("ok"))
    return {
        "ok": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "golden_version": GOLDEN_SCENARIOS_VERSION,
    }
