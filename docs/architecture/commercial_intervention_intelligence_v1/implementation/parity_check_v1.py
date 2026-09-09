# -*- coding: utf-8 -*-
"""
Simulation <-> runtime parity check (non-production).

Imports the simulation prototype and the real runtime side by side and compares
the 8 governed projections. Fails if any governed field diverges.

Run from repo root:
    python docs/architecture/commercial_intervention_intelligence_v1/implementation/parity_check_v1.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

SIM_PATH = REPO_ROOT / "docs/architecture/commercial_intervention_intelligence_v1/simulation_v1.py"
_spec = importlib.util.spec_from_file_location("cii_simulation_v1", SIM_PATH)
sim = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sim)  # type: ignore[union-attr]

from services.commercial_action_language_v1.intervention_v1 import (  # noqa: E402
    compose_merchant_intervention_card_v1,
    economic_manifest_v1,
    intervention_contract_v1,
    validate_intervention_card_v1,
)

SPECS = [
    ("1. R17 shipping Level 2", sim.FAM_SHIPPING, (20, 12), sim.TRUTH_PRODUCTION_READY,
     None, sim.CONFLICT_SAFE_TO_COEXIST, sim.ROLE_PRIMARY, "", None),
    ("2. price Level 2", sim.FAM_PRICE, (20, 11), sim.TRUTH_PRODUCTION_READY,
     None, sim.CONFLICT_SAFE_TO_COEXIST, sim.ROLE_PRIMARY, "", None),
    ("3. product confidence Level 2", sim.FAM_CONFIDENCE, (18, 10), sim.TRUTH_PRODUCTION_READY,
     None, sim.CONFLICT_SAFE_TO_COEXIST, sim.ROLE_PRIMARY, "جودة المنتج", None),
    ("4. complementary products Level 1", sim.FAM_COMPLEMENTARY, (20, 9),
     sim.TRUTH_PRODUCTION_READY, None, sim.CONFLICT_SAFE_TO_COEXIST, sim.ROLE_SECONDARY, "", None),
    ("5. insufficient evidence", sim.FAM_WAIT, (4, 2), sim.TRUTH_INSUFFICIENT,
     None, sim.CONFLICT_SAFE_TO_COEXIST, sim.ROLE_PRIMARY, "", None),
    ("6. conflicting signals", sim.FAM_PRICE, (20, 11), sim.TRUTH_PRODUCTION_READY,
     None, sim.CONFLICT_MEASUREMENT_CONTAMINATION, sim.ROLE_SECONDARY, "", None),
    ("7. already under measurement", sim.FAM_SHIPPING, (20, 12), sim.TRUTH_PRODUCTION_READY,
     sim.PHASE_UNDER_MEASUREMENT, sim.CONFLICT_SAFE_TO_COEXIST, sim.ROLE_PRIMARY, "", None),
    ("8. Level 3 blocked by economics", sim.FAM_SHIPPING, (20, 12), sim.TRUTH_PRODUCTION_READY,
     None, sim.CONFLICT_SAFE_TO_COEXIST, sim.ROLE_PRIMARY, "", 3),
]

SECTIONS_SIM = ["what_we_see_ar", "what_we_suggest_ar", "why_this_is_safe_ar",
                "blocked_candidates", "dont_do_ar", "measure_block",
                "recheck_condition", "mind_change_condition"]
SECTIONS_RT = ["what_we_see_ar", "what_we_suggest_ar", "why_this_is_safe_ar",
               "blocked_candidates", "dont_do_ar", "primary_metric",
               "recheck_condition", "mind_change_condition"]


def main() -> int:
    rows: list[str] = []
    failures = 0
    print("Simulation <-> runtime parity")
    for (label, family, counts, truth, phase, conflict, role, reason, requested) in SPECS:
        total, top = counts
        share = top / total if total else 0.0
        evidence = {"counts": {"hesitation_total": total, "top_count": top, "top_share": share}}

        s = sim.build_projection(
            family=family, counts=counts, col_truth_class=truth, own_cdc_phase=phase,
            portfolio_conflict_type=conflict, catalog_role=role,
            manifest=sim.MANIFEST_TODAY, reason_label_ar=reason, requested_level=requested,
        )
        intervention = intervention_contract_v1(
            family=family, col_truth_class=truth, catalog_role=role,
            portfolio_conflict_type=conflict, own_cdc_phase=phase,
            manifest=economic_manifest_v1(), requested_level=requested,
        )
        r = compose_merchant_intervention_card_v1(
            family=family, intervention=intervention, evidence=evidence, reason_label_ar=reason,
        )

        diffs: list[str] = []
        if s["recommendation_level"] != r["recommendation_level"]:
            diffs.append(f"level {s['recommendation_level']}!={r['recommendation_level']}")
        if s["eligibility_state"] != r["eligibility_state"]:
            diffs.append(f"state {s['eligibility_state']}!={r['eligibility_state']}")
        if bool(s["cta_ar"]) != bool(r["cta_ar"]):
            diffs.append("cta presence")
        if s["blocked_candidates"][0]["blocked_reason"] != r["blocked_candidates"][0]["blocked_reason"]:
            diffs.append("blocked_reason")
        sim_sections = sum(1 for k in SECTIONS_SIM if s.get(k) not in (None, "", []))
        rt_sections = sum(1 for k in SECTIONS_RT if r.get(k) not in (None, "", []))
        if sim_sections != 8 or rt_sections != 8:
            diffs.append(f"sections {sim_sections}/{rt_sections}")
        errors = validate_intervention_card_v1(r)
        if errors:
            diffs.append(f"runtime_validation={errors}")

        ok = not diffs
        failures += 0 if ok else 1
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label} | L{r['recommendation_level']} "
              f"{r['eligibility_state']} cta={bool(r['cta_ar'])} sections={rt_sections}/8"
              + ("" if ok else f" | DIFF: {diffs}"))
        rows.append(
            f"| {label} | {s['recommendation_level']} / {r['recommendation_level']} | "
            f"{s['eligibility_state']} / {r['eligibility_state']} | "
            f"{bool(s['cta_ar'])} / {bool(r['cta_ar'])} | {sim_sections} / {rt_sections} | {status} |"
        )

    out = Path(__file__).with_name("PARITY.md")
    out.write_text(
        "# Simulation <-> Runtime Parity\n\n"
        "Generated by `parity_check_v1.py`. Left value = `simulation_v1.py`, "
        "right value = real runtime (`commercial_action_language_v1.intervention_v1`).\n\n"
        "| Projection | Level sim/rt | Eligibility sim/rt | CTA sim/rt | Sections sim/rt | Parity |\n"
        "|---|---|---|---|---|---|\n" + "\n".join(rows) +
        f"\n\n**Result: {len(SPECS) - failures}/{len(SPECS)} projections in parity.**\n",
        encoding="utf-8",
    )
    print(f"\n{len(SPECS) - failures}/{len(SPECS)} projections in parity")
    print(f"report: {out}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
