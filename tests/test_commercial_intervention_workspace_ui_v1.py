# -*- coding: utf-8 -*-
"""
Commercial Intervention Intelligence V1 — live Decision Workspace composition.

Proves the merchant workspace paints the already-owned intervention contract and
adds no business logic of its own: no ranking, no eligibility decision, no
re-authored copy, no extra query.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from services.commercial_action_language_v1.workspace_intervention_v1 import (
    GUARDRAIL_FALLBACK_AR,
    attach_intervention_to_summary_v1,
    build_workspace_intervention_v1,
)
from services.commercial_opportunity_layer_v1.contract_v1 import (
    TRUTH_INSUFFICIENT,
    TRUTH_PRODUCTION_READY,
)
from services.mission_catalog_v1.contract_v1 import ROLE_PRIMARY
from services.mission_portfolio_v1.contract_v1 import (
    CONFLICT_CAPACITY_ONLY,
    CONFLICT_DUPLICATE_INTENT,
    CONFLICT_MEASUREMENT_CONTAMINATION,
    CONFLICT_SAFE_TO_COEXIST,
)

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
WORKSPACE_CSS = (ROOT / "static" / "merchant_ui_v2_workspace.css").read_text(encoding="utf-8")

R17_EVIDENCE = {
    "counts": {
        "hesitation_total": 20,
        "top_count": 12,
        "top_share": 0.6,
        "top_reason": "shipping",
    }
}
SHIPPING = "shipping_friction"


def projection(
    *,
    family: str = SHIPPING,
    truth: str = TRUTH_PRODUCTION_READY,
    role: str = ROLE_PRIMARY,
    conflict: str | None = CONFLICT_SAFE_TO_COEXIST,
    phase: str | None = None,
    evidence: dict | None = None,
) -> dict:
    return build_workspace_intervention_v1(
        family=family,
        col_truth_class=truth,
        catalog_role=role,
        portfolio_conflict_type=conflict,
        own_cdc_phase=phase,
        evidence=R17_EVIDENCE if evidence is None else evidence,
    )


def _node_eval(expr: str) -> object:
    script = f"""
var fs = require('fs');
var vm = require('vm');
var g = {{ window: {{}}, globalThis: {{}}, document: null, location: {{ search: '' }} }};
g.window = g; g.globalThis = g;
function load(p) {{ vm.runInNewContext(fs.readFileSync(p, 'utf8'), g); }}
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_semantic_model.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_language.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_home.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_workspace.js"))});
var out = {expr};
console.log(JSON.stringify(out));
"""
    # Arabic copy is the assertion surface, so the pipe must be UTF-8 decoded
    # rather than left to the Windows console codepage.
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout.strip().splitlines()[-1])


def paint(proj: dict, *, phase: str | None = None) -> str:
    """Render the commercial lane exactly as the browser would."""
    opp = {
        "opportunity_id": "opp-1",
        "family": proj.get("family") or SHIPPING,
        "title_ar": "أقوى تردد مسجّل الآن مرتبط بالشحن.",
        "mission_ready": True,
        "intervention": proj,
        "commitment": {"phase": phase} if phase else None,
        "cdc_phase": phase,
    }
    return _node_eval(
        "g.CartFlowUiV2Workspace.renderColDecision(" + json.dumps(opp, ensure_ascii=False) + ")"
    )


class R17LiveTargetTests(unittest.TestCase):
    """R17: shipping 12/20, Level 2, ELIGIBLE, all eight answers present."""

    def setUp(self) -> None:
        self.p = projection()

    def test_eligible_level_2(self) -> None:
        self.assertEqual(self.p["eligibility_state"], "ELIGIBLE")
        self.assertEqual(self.p["recommendation_level"], 2)

    def test_diagnosis_and_evidence_preserved(self) -> None:
        self.assertIn("الشحن", self.p["situation_ar"])
        self.assertIn("12 من 20", self.p["evidence_ar"])
        self.assertIn("60", self.p["evidence_ar"])

    def test_intervention_direction_is_clarification(self) -> None:
        suggest = self.p["what_we_suggest_ar"]
        self.assertTrue(suggest)
        self.assertIn("تكلفة الشحن", suggest)
        self.assertIn("مدة التوصيل", suggest)

    def test_why_safe_present(self) -> None:
        self.assertIn("لا يغيّر سعرك", self.p["why_this_is_safe_ar"])

    def test_blocked_stronger_actions_present(self) -> None:
        blocked = self.p["blocked_candidates"]
        self.assertEqual(len(blocked), 1)
        self.assertIn("شحن", blocked[0]["class_ar"])
        self.assertIn("لا نعرف تكلفة الشحن", blocked[0]["merchant_ar"])
        self.assertEqual(blocked[0]["missing_input_count"], 8)

    def test_blocked_reason_never_leaks_field_names(self) -> None:
        blob = json.dumps(self.p, ensure_ascii=False)
        for raw in ("gross_margin", "margin_floor", "product_cost", "platform_commission"):
            self.assertNotIn(raw, blob)

    def test_dont_do_preserved(self) -> None:
        dont = self.p["dont_do_ar"]
        self.assertIn("لا تخفّض", dont)
        self.assertIn("مجانياً", dont)

    def test_measurement_and_guardrail(self) -> None:
        self.assertIn("حصة أسباب الشحن", self.p["primary_metric"])
        self.assertEqual(self.p["guardrail_metric"], "لا تراجع في تحوّل السلة إلى شراء")

    def test_recheck_and_mind_change(self) -> None:
        self.assertTrue(self.p["recheck_condition"])
        self.assertTrue(self.p["mind_change_condition"])

    def test_cta_present(self) -> None:
        self.assertEqual(self.p["cta_ar"], "اعتمد هذه المهمة")

    def test_no_revenue_success_claim(self) -> None:
        blob = json.dumps(self.p, ensure_ascii=False)
        for claim in ("إيراد", "أرباح", "ربح إضافي", "زيادة المبيعات", "revenue"):
            self.assertNotIn(claim, blob)


class BlockedStateTests(unittest.TestCase):
    """Every blocked state explains itself and offers no executable control."""

    def test_capacity_only_is_wait_not_rejection(self) -> None:
        p = projection(conflict=CONFLICT_CAPACITY_ONLY)
        self.assertEqual(p["eligibility_state"], "WAIT_AND_RECHECK")
        self.assertIsNone(p["cta_ar"])
        self.assertNotIn("غير مبرر", p["what_we_suggest_ar"])
        self.assertIn("ننتظر", p["what_we_suggest_ar"])

    def test_duplicate_intent_is_not_justified(self) -> None:
        p = projection(conflict=CONFLICT_DUPLICATE_INTENT)
        self.assertEqual(p["eligibility_state"], "INTERVENTION_NOT_JUSTIFIED")
        self.assertIsNone(p["cta_ar"])
        self.assertIn("مهمة قائمة", p["what_we_suggest_ar"])

    def test_conflicting_signals(self) -> None:
        p = projection(conflict=CONFLICT_MEASUREMENT_CONTAMINATION)
        self.assertEqual(p["eligibility_state"], "CONFLICTING_SIGNALS")
        self.assertIsNone(p["cta_ar"])
        self.assertIn("مؤجّل", p["what_we_suggest_ar"])

    def test_already_under_measurement(self) -> None:
        p = projection(phase="UNDER_MEASUREMENT")
        self.assertEqual(p["eligibility_state"], "ALREADY_UNDER_MEASUREMENT")
        self.assertIsNone(p["cta_ar"])
        self.assertIn("قيد القياس", p["what_we_suggest_ar"])

    def test_insufficient_evidence(self) -> None:
        p = projection(
            family="wait_insufficient_evidence",
            truth=TRUTH_INSUFFICIENT,
            evidence={"counts": {"hesitation_total": 4, "top_count": 2, "top_share": 0.5}},
        )
        self.assertEqual(p["eligibility_state"], "INSUFFICIENT_EVIDENCE")
        self.assertIsNone(p["cta_ar"])

    def test_unknown_conflict_fails_closed_to_wait(self) -> None:
        p = projection(conflict=None)
        self.assertEqual(p["eligibility_state"], "WAIT_AND_RECHECK")
        self.assertIsNone(p["cta_ar"])

    def test_every_blocked_state_still_answers_the_merchant(self) -> None:
        for label, p in (
            ("capacity", projection(conflict=CONFLICT_CAPACITY_ONLY)),
            ("duplicate", projection(conflict=CONFLICT_DUPLICATE_INTENT)),
            ("conflict", projection(conflict=CONFLICT_MEASUREMENT_CONTAMINATION)),
            ("measuring", projection(phase="UNDER_MEASUREMENT")),
        ):
            with self.subTest(label):
                self.assertTrue(p["what_we_suggest_ar"], "no empty state")
                self.assertTrue(p["why_this_is_safe_ar"])
                self.assertTrue(p["blocked_candidates"])
                self.assertTrue(p["mind_change_condition"])


class GuardrailFallbackTests(unittest.TestCase):
    def test_level_1_family_gets_safe_fallback_never_null(self) -> None:
        p = projection(family="product_opportunity_focus", evidence={})
        self.assertEqual(p["recommendation_level"], 1)
        self.assertEqual(p["guardrail_metric"], GUARDRAIL_FALLBACK_AR)
        self.assertNotIn("None", json.dumps(p, ensure_ascii=False))

    def test_complementary_uses_merchant_terminology(self) -> None:
        p = projection(family="product_opportunity_focus", evidence={})
        blob = json.dumps(p, ensure_ascii=False)
        self.assertIn("مكمل", blob)
        self.assertNotIn("البيع المتقاطع", blob)


class SummaryAttachTests(unittest.TestCase):
    """Attachment reads owners already on the summary — no new query."""

    def _summary(self, *, conflict_bucket: str | None = None, conflict: str | None = None) -> dict:
        portfolio: dict = {
            "ok": True,
            "active_mission": {"opportunity_id": "opp-1"},
            "deferred": [],
            "suppressed": [],
            "safe_secondaries": [],
        }
        if conflict_bucket:
            portfolio["active_mission"] = None
            portfolio[conflict_bucket] = [
                {"opportunity_id": "opp-1", "conflict_type": conflict}
            ]
        return {
            "mission_catalog_v1": {
                "ok": True,
                "primary": {
                    "opportunity_id": "opp-1",
                    "family": SHIPPING,
                    "role": ROLE_PRIMARY,
                    "truth_class": TRUTH_PRODUCTION_READY,
                    "cdc_phase": None,
                    "mission_ready": True,
                    "evidence": R17_EVIDENCE,
                },
            },
            "mission_portfolio_v1": portfolio,
        }

    def test_attaches_to_catalog_primary(self) -> None:
        body = attach_intervention_to_summary_v1(self._summary())
        iv = body["mission_catalog_v1"]["primary"]["intervention_v1"]
        self.assertTrue(iv["ok"])
        self.assertEqual(iv["eligibility_state"], "ELIGIBLE")
        self.assertEqual(iv["recommendation_level"], 2)

    def test_deferred_conflict_is_read_from_portfolio(self) -> None:
        body = attach_intervention_to_summary_v1(
            self._summary(conflict_bucket="deferred", conflict=CONFLICT_CAPACITY_ONLY)
        )
        iv = body["mission_catalog_v1"]["primary"]["intervention_v1"]
        self.assertEqual(iv["eligibility_state"], "WAIT_AND_RECHECK")
        self.assertIsNone(iv["cta_ar"])

    def test_missing_catalog_is_a_no_op(self) -> None:
        for body in ({}, {"mission_catalog_v1": {"ok": False}}, {"mission_catalog_v1": {}}):
            self.assertIsInstance(attach_intervention_to_summary_v1(dict(body)), dict)

    def test_full_cal_projection_carries_col_evidence_share(self) -> None:
        """End to end through CAL: R17 keeps 12 من 20 (60٪) on the workspace."""
        from services.commercial_action_language_v1 import (
            project_commercial_action_language_v1,
        )

        body = self._summary()
        body["commercial_opportunity_layer_v1"] = {
            "ok": True,
            "primary": {
                "opportunity_id": "opp-1",
                "family": SHIPPING,
                "truth_class": TRUTH_PRODUCTION_READY,
                "evidence": R17_EVIDENCE,
            },
            "secondaries": [],
        }
        out = project_commercial_action_language_v1(body)
        iv = out["mission_catalog_v1"]["primary"]["intervention_v1"]
        self.assertIn("12 من 20", iv["evidence_ar"])
        self.assertIn("60", iv["evidence_ar"])
        self.assertIn("الشحن", iv["situation_ar"])
        self.assertIn("60", iv["primary_metric"])
        self.assertEqual(iv["eligibility_state"], "ELIGIBLE")
        self.assertEqual(iv["recommendation_level"], 2)

    def test_projection_does_not_touch_the_database(self) -> None:
        src = (
            ROOT / "services/commercial_action_language_v1/workspace_intervention_v1.py"
        ).read_text(encoding="utf-8")
        for token in ("db.session", "session.query", "sqlalchemy", "import models", "requests."):
            self.assertNotIn(token, src)


class PaintedWorkspaceTests(unittest.TestCase):
    """The browser paints contract truth; the DOM proves it."""

    def test_r17_paints_all_eight_answers(self) -> None:
        html = paint(projection())
        for label in (
            "ما الذي نراه؟",
            "ما التدخل المقترح الآن؟",
            "لماذا هذا آمن الآن؟",
            "لماذا لا نقترح تدخلاً أقوى؟",
            "لا تفعل الآن",
            "ماذا سنقيس؟",
            "متى نراجع؟",
            "ما الذي سيجعلنا نغيّر رأينا؟",
        ):
            self.assertIn(label, html)

    def test_r17_markers_and_cta(self) -> None:
        html = paint(projection())
        self.assertIn('data-cf-intervention-level="2"', html)
        self.assertIn('data-cf-intervention-eligibility="ELIGIBLE"', html)
        self.assertIn('data-cf-intervention-cta="1"', html)
        self.assertIn('data-cf-intervention-blocked-count="1"', html)
        self.assertIn("اعتمد هذه المهمة", html)

    def test_reading_order_is_evidence_intervention_limit_action_measurement(self) -> None:
        html = paint(projection())
        see = html.index('data-cf2-civ-block="see"')
        suggest = html.index('data-cf2-civ-block="suggest"')
        limit = html.index('data-cf2-civ-block="limit"')
        action = html.index('data-cf2-mission-act="accept"')
        measurement = html.index('data-cf2-civ-block="measurement"')
        self.assertLess(see, suggest)
        self.assertLess(suggest, limit)
        self.assertLess(limit, action)
        self.assertLess(action, measurement)

    def test_decision_body_is_painted_once(self) -> None:
        """The arc organism must not repeat the intervention body."""
        html = paint(projection())
        self.assertEqual(html.count("ما التدخل المقترح الآن؟"), 1)
        self.assertEqual(html.count("اعتمد هذه المهمة"), 1)
        self.assertNotIn('data-cf2-col-ws-unit="decision"', html)

    def test_blocked_states_paint_no_executable_cta(self) -> None:
        for label, proj in (
            ("CONFLICTING_SIGNALS", projection(conflict=CONFLICT_MEASUREMENT_CONTAMINATION)),
            ("CAPACITY_ONLY", projection(conflict=CONFLICT_CAPACITY_ONLY)),
            ("DUPLICATE_INTENT", projection(conflict=CONFLICT_DUPLICATE_INTENT)),
            ("WAIT_AND_RECHECK", projection(conflict=None)),
        ):
            with self.subTest(label):
                html = paint(proj)
                self.assertIn('data-cf-intervention-cta="0"', html)
                self.assertNotIn("اعتمد هذه المهمة", html)
                self.assertNotIn("disabled", html)

    def test_under_measurement_paints_status_without_accept(self) -> None:
        html = paint(projection(phase="UNDER_MEASUREMENT"), phase="UNDER_MEASUREMENT")
        self.assertIn('data-cf-intervention-eligibility="ALREADY_UNDER_MEASUREMENT"', html)
        self.assertNotIn("اعتمد هذه المهمة", html)

    def test_no_merchant_visible_technical_identifiers(self) -> None:
        html = paint(projection())
        for token in ("civ1:", "shipping_friction", "PRODUCTION_TRUTH_READY", "disclosure_only"):
            self.assertNotIn(">" + token, html)
        self.assertNotIn("ECONOMIC_INPUTS_REQUIRED<", html)


class LiveDecisionHierarchyPathTests(unittest.TestCase):
    """The lab layout must show the same one decision, not a second copy."""

    LDH = {
        "enabled": True,
        "commercial_status_owner": "catalog_cdc_portfolio",
        "workspace": {
            "title_ar": "أقوى تردد مسجّل الآن مرتبط بالشحن.",
            "why_now_ar": "لأن الشحن يمثل 12 من 20 سبب تردد مسجّل.",
            "evidence_ar": "12 من 20 (60٪)",
            "decision_ar": "حدّد هل التردد مرتبط بتكلفة الشحن أم مدة التوصيل.",
            "dont_ar": "لا تخفّض الشحن.",
            "execution_ar": "افتح أسباب التردد في سياسة الاسترجاع.",
            "journey": {
                "current_step": "accept",
                "steps": [
                    {"id": "accept", "label_ar": "اعتمد هذه المهمة"},
                    {"id": "measure", "label_ar": "يبدأ القياس"},
                ],
            },
            "monitoring": [
                {"family": "price_hesitation", "body_ar": "السعر يتكرر في 5 من 20 سبباً (25٪)."}
            ],
            "recheck_ar": "بعد بلوغ حد الكفاية.",
        },
    }

    def paint_ldh(self, proj: dict, *, phase: str | None = None) -> str:
        opp = {
            "opportunity_id": "opp-1",
            "family": proj.get("family") or SHIPPING,
            "title_ar": "أقوى تردد مسجّل الآن مرتبط بالشحن.",
            "mission_ready": True,
            "intervention": proj,
            "commitment": {"phase": phase} if phase else None,
            "cdc_phase": phase,
        }
        return _node_eval(
            "g.CartFlowUiV2Workspace.renderHierarchyWorkspace("
            + json.dumps(self.LDH, ensure_ascii=False)
            + ","
            + json.dumps(opp, ensure_ascii=False)
            + ")"
        )

    def test_lab_layout_paints_the_intervention(self) -> None:
        html = self.paint_ldh(projection())
        self.assertIn('data-cf2-civ="v1"', html)
        for label in ("ما التدخل المقترح الآن؟", "لماذا هذا آمن الآن؟", "لماذا لا نقترح تدخلاً أقوى؟"):
            self.assertIn(label, html)

    def test_lab_layout_does_not_duplicate_the_decision(self) -> None:
        html = self.paint_ldh(projection())
        self.assertNotIn("cf2-ldh__title", html)
        self.assertNotIn('data-cf2-ldh-flow="decision"', html)
        self.assertNotIn('data-cf2-ldh-flow="dont"', html)
        self.assertNotIn('data-cf2-ldh-flow="recheck"', html)
        self.assertEqual(html.count("اعتمد هذه المهمة"), 2)  # journey step + CTA

    def test_lab_layout_keeps_lifecycle_and_monitoring_owners(self) -> None:
        html = self.paint_ldh(projection())
        self.assertIn('data-cf2-ldh-journey="1"', html)
        self.assertIn('data-cf2-ldh-secondary="price_hesitation"', html)

    def test_lab_layout_withholds_cta_when_blocked(self) -> None:
        html = self.paint_ldh(projection(conflict=CONFLICT_DUPLICATE_INTENT))
        self.assertIn('data-cf-intervention-cta="0"', html)
        self.assertNotIn('data-cf2-mission-act="accept"', html)

    def test_lab_layout_falls_back_when_no_contract(self) -> None:
        html = self.paint_ldh({})
        self.assertIn("cf2-ldh__title", html)
        self.assertNotIn('data-cf2-civ="v1"', html)


class NoFrontendBusinessLogicTests(unittest.TestCase):
    def test_frontend_does_not_rank_or_decide_eligibility(self) -> None:
        start = WORKSPACE_JS.index("function renderInterventionDecision")
        end = WORKSPACE_JS.index("function renderColDecision")
        body = WORKSPACE_JS[start:end]
        for token in ("sort(", "ELIGIBLE", "recommendation_level >", "level >=", "if (level"):
            self.assertNotIn(token, body)

    def test_cta_gate_reads_server_truth_only(self) -> None:
        self.assertIn("var interventionBlocks = !!(iv && iv.ok === true && !iv.cta_ar);", WORKSPACE_JS)

    def test_merchant_js_has_no_cross_sell_term(self) -> None:
        self.assertNotIn("البيع المتقاطع", WORKSPACE_JS)

    def test_styling_exists_and_is_mobile_aware(self) -> None:
        self.assertIn(".cf2-civ__act-text", WORKSPACE_CSS)
        civ = WORKSPACE_CSS[WORKSPACE_CSS.index(".cf2-civ {"):]
        self.assertIn("@media (max-width: 1023px)", civ)


if __name__ == "__main__":
    unittest.main()
