# -*- coding: utf-8 -*-
"""
Commercial Intervention Intelligence V1.1 — state-aware composition and the
CartFlow mission lifecycle action family.

Presentation only. The heading follows CDC's phase, the controls follow CDC's
phase, and nothing here decides a lifecycle or an eligibility.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

from services.commercial_action_language_v1.workspace_intervention_v1 import (
    HEADINGS_AR,
    STATE_ACTION_CHOSEN,
    STATE_READY,
    STATE_RECHECK_DUE,
    STATE_UNDER_MEASUREMENT,
    STATE_WAIT,
)
from services.commercial_decision_commitment_v1.contract_v1 import (
    PHASE_ACTION_CHOSEN,
    PHASE_RECHECK_DUE,
    PHASE_UNDER_MEASUREMENT,
)
from services.mission_portfolio_v1.contract_v1 import (
    CONFLICT_CAPACITY_ONLY,
    CONFLICT_MEASUREMENT_CONTAMINATION,
)
from tests.test_commercial_intervention_workspace_ui_v1 import (
    SHIPPING,
    WORKSPACE_CSS,
    WORKSPACE_JS,
    _node_eval,
    projection,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECTION_SRC = (
    ROOT / "services" / "commercial_action_language_v1" / "workspace_intervention_v1.py"
).read_text(encoding="utf-8")

ACCEPT_AR = "اعتمد هذه المهمة"
CONFIRM_AR = "أكد إتمام الضبط"  # frozen product copy; V1.1 restyles it only
REVERSE_AR = "تراجع عن المهمة"


def paint(proj: dict, *, phase: str | None = None) -> str:
    """Render the commercial lane the way the browser does, with a commitment."""
    opp = {
        "opportunity_id": "opp-1",
        "family": proj.get("family") or SHIPPING,
        "title_ar": "أقوى تردد مسجّل الآن مرتبط بالشحن.",
        "mission_ready": True,
        "intervention": proj,
        "commitment": {"phase": phase, "commitment_id": "cmt-1"} if phase else None,
        "cdc_phase": phase,
    }
    import json

    return _node_eval(
        "g.CartFlowUiV2Workspace.renderColDecision(" + json.dumps(opp, ensure_ascii=False) + ")"
    )


class StateAwareHeadingTests(unittest.TestCase):
    """The primary question matches the lifecycle the merchant is actually in."""

    def test_ready_asks_what_to_do(self) -> None:
        p = projection()
        self.assertEqual(p["heading_state"], STATE_READY)
        self.assertEqual(p["labels_ar"]["suggest"], "ما التدخل المقترح الآن؟")
        self.assertTrue(p["is_new_recommendation"])

    def test_action_chosen_asks_what_was_accepted(self) -> None:
        p = projection(phase=PHASE_ACTION_CHOSEN)
        self.assertEqual(p["heading_state"], STATE_ACTION_CHOSEN)
        self.assertEqual(p["labels_ar"]["suggest"], "ما الذي اعتمدته الآن؟")
        self.assertFalse(p["is_new_recommendation"])

    def test_under_measurement_asks_what_is_measured(self) -> None:
        p = projection(phase=PHASE_UNDER_MEASUREMENT)
        self.assertEqual(p["heading_state"], STATE_UNDER_MEASUREMENT)
        self.assertEqual(p["labels_ar"]["suggest"], "ما الذي نقيسه الآن؟")
        self.assertFalse(p["is_new_recommendation"])

    def test_recheck_due_asks_what_the_review_showed(self) -> None:
        p = projection(phase=PHASE_RECHECK_DUE)
        self.assertEqual(p["heading_state"], STATE_RECHECK_DUE)
        self.assertEqual(p["labels_ar"]["suggest"], "ماذا أظهرت إعادة المراجعة؟")

    def test_blocked_asks_why_we_wait(self) -> None:
        p = projection(conflict=CONFLICT_CAPACITY_ONLY)
        self.assertEqual(p["eligibility_state"], "WAIT_AND_RECHECK")
        self.assertEqual(p["heading_state"], STATE_WAIT)
        self.assertEqual(p["labels_ar"]["suggest"], "لماذا ننتظر الآن؟")

    def test_conflicting_signals_also_asks_why_we_wait(self) -> None:
        p = projection(conflict=CONFLICT_MEASUREMENT_CONTAMINATION)
        self.assertEqual(p["eligibility_state"], "CONFLICTING_SIGNALS")
        self.assertEqual(p["heading_state"], STATE_WAIT)

    def test_every_state_has_a_distinct_heading(self) -> None:
        self.assertEqual(len(set(HEADINGS_AR.values())), len(HEADINGS_AR))

    def test_heading_is_painted_and_marked(self) -> None:
        html = paint(projection(phase=PHASE_UNDER_MEASUREMENT), phase=PHASE_UNDER_MEASUREMENT)
        self.assertIn('data-cf-intervention-state="UNDER_MEASUREMENT"', html)
        self.assertIn("ما الذي نقيسه الآن؟", html)
        self.assertNotIn("ما التدخل المقترح الآن؟", html)


class UnderMeasurementCompositionTests(unittest.TestCase):
    """A running mission is context, never a fresh proposal."""

    def setUp(self) -> None:
        self.p = projection(phase=PHASE_UNDER_MEASUREMENT)
        self.html = paint(self.p, phase=PHASE_UNDER_MEASUREMENT)

    def test_says_the_mission_is_already_running(self) -> None:
        self.assertIn("قيد القياس بالفعل", self.p["what_we_suggest_ar"])

    def test_warns_against_a_parallel_intervention(self) -> None:
        self.assertIn("لا تبدأ تدخلاً موازياً", self.html)

    def test_shows_what_is_measured_and_when_we_reconsider(self) -> None:
        self.assertIn("ماذا سنقيس؟", self.html)
        self.assertIn("متى نراجع؟", self.html)
        self.assertIn("ما الذي سيجعلنا نغيّر رأينا؟", self.html)

    def test_current_intervention_stays_visible_as_context(self) -> None:
        self.assertTrue(self.p["active_intervention_ar"])
        self.assertIn('data-cf2-civ-recommendation="0"', self.html)
        self.assertIn("cf2-civ__act--context", self.html)
        self.assertIn("التدخل الجاري", self.html)

    def test_ready_card_carries_no_context_line(self) -> None:
        ready = projection()
        self.assertEqual(ready["active_intervention_ar"], "")
        self.assertIn('data-cf2-civ-recommendation="1"', paint(ready))

    def test_blocked_card_never_ends_on_an_instruction_to_act(self) -> None:
        for label, p in (
            ("wait", projection(conflict=CONFLICT_CAPACITY_ONLY)),
            ("conflict", projection(conflict=CONFLICT_MEASUREMENT_CONTAMINATION)),
        ):
            with self.subTest(label):
                self.assertEqual(p["active_intervention_ar"], "")
                self.assertNotIn("افتح أسباب التردد", p["what_we_suggest_ar"])
                self.assertTrue(p["what_we_suggest_ar"], "no empty state")


class AdvisoryCompressionTests(unittest.TestCase):
    """One advisory block: why safe -> why not stronger -> do not do."""

    def setUp(self) -> None:
        self.html = paint(projection())

    def test_reads_in_the_required_order(self) -> None:
        safe = self.html.index("لماذا هذا آمن الآن؟")
        stronger = self.html.index("لماذا لا نقترح تدخلاً أقوى؟")
        dont = self.html.index("لا تفعل الآن")
        self.assertLess(safe, stronger)
        self.assertLess(stronger, dont)

    def test_is_one_block_with_inline_sublabels(self) -> None:
        self.assertEqual(self.html.count('data-cf2-civ-block="limit"'), 1)
        self.assertIn('<p class="cf2-civ__advice"', self.html)
        self.assertIn('<b class="cf2-civ__sub">', self.html)

    def test_keeps_every_safety_meaning(self) -> None:
        p = projection()
        self.assertIn(p["why_this_is_safe_ar"], self.html)
        self.assertIn(p["dont_do_ar"], self.html)
        self.assertIn(p["blocked_candidates"][0]["merchant_ar"], self.html)

    def test_does_not_repeat_the_rationale(self) -> None:
        for label in ("لماذا هذا آمن الآن؟", "لماذا لا نقترح تدخلاً أقوى؟", "لا تفعل الآن"):
            self.assertEqual(self.html.count(label), 1)

    def test_does_not_expose_economic_input_identifiers(self) -> None:
        for token in ("shipping_cost", "gross_margin", "margin_floor", "cogs", "missing_inputs"):
            self.assertNotIn(token, self.html)


class MeasurementHierarchyTests(unittest.TestCase):
    """Three separated questions; the guardrail belongs to the first."""

    def setUp(self) -> None:
        self.html = paint(projection())

    def test_three_questions_are_separate_units(self) -> None:
        for kind in ("measure", "recheck", "mind-change"):
            self.assertIn('data-cf2-civ-ask="' + kind + '"', self.html)
        self.assertEqual(self.html.count('class="cf2-civ__ask"'), 3)

    def test_guardrail_sits_under_what_we_measure(self) -> None:
        block = self.html[self.html.index('data-cf2-civ-ask="measure"') :]
        block = block[: block.index('data-cf2-civ-ask="recheck"')]
        self.assertIn("الحد الذي لا نتجاوزه", block)
        self.assertIn("لا تراجع في تحوّل السلة إلى شراء", block)

    def test_guardrail_fallback_reads_naturally(self) -> None:
        p = projection()
        p["guardrail_metric"] = "لا يوجد مقياس اقتصادي موثوق بعد."
        html = paint(p)
        self.assertIn("لا يوجد مقياس اقتصادي موثوق بعد.", html)
        for token in ("null", "undefined", "None"):
            self.assertNotIn(">" + token + "<", html)

    def test_no_revenue_claim(self) -> None:
        p = projection()
        blob = " ".join(
            str(p.get(k) or "")
            for k in ("primary_metric", "guardrail_metric", "recheck_condition",
                      "mind_change_condition", "what_we_suggest_ar")
        )
        for token in ("إيراد", "أرباح", "ريال", "مبيعات إضافية"):
            self.assertNotIn(token, blob)


class LifecycleActionFamilyTests(unittest.TestCase):
    """Accept, confirm and reverse are one CartFlow visual system."""

    def test_ready_renders_the_primary_action_only(self) -> None:
        html = paint(projection())
        self.assertIn('data-cf-lifecycle-action="primary"', html)
        self.assertIn(ACCEPT_AR, html)
        self.assertNotIn('data-cf-lifecycle-action="confirm"', html)
        self.assertNotIn('data-cf-lifecycle-action="secondary"', html)

    def test_action_chosen_renders_confirm_and_reversal(self) -> None:
        html = paint(projection(phase=PHASE_ACTION_CHOSEN), phase=PHASE_ACTION_CHOSEN)
        self.assertIn('data-cf-lifecycle-action="confirm"', html)
        self.assertIn(CONFIRM_AR, html)
        self.assertIn('data-cf-lifecycle-action="secondary"', html)
        self.assertIn(REVERSE_AR, html)

    def test_confirm_copy_and_supporting_line_are_preserved(self) -> None:
        html = paint(projection(phase=PHASE_ACTION_CHOSEN), phase=PHASE_ACTION_CHOSEN)
        self.assertIn(CONFIRM_AR, html)
        self.assertIn("بعد التأكيد يبدأ CartFlow قياس أثر المهمة.", html)

    def test_under_measurement_never_offers_accept_again(self) -> None:
        html = paint(projection(phase=PHASE_UNDER_MEASUREMENT), phase=PHASE_UNDER_MEASUREMENT)
        self.assertNotIn('data-cf2-mission-act="accept"', html)
        self.assertNotIn(ACCEPT_AR, html)

    def test_under_measurement_never_offers_confirm_again(self) -> None:
        html = paint(projection(phase=PHASE_UNDER_MEASUREMENT), phase=PHASE_UNDER_MEASUREMENT)
        self.assertNotIn('data-cf2-mission-act="confirm"', html)
        self.assertNotIn(CONFIRM_AR, html)

    def test_under_measurement_keeps_reversal_cdc_already_allows(self) -> None:
        html = paint(projection(phase=PHASE_UNDER_MEASUREMENT), phase=PHASE_UNDER_MEASUREMENT)
        self.assertIn('data-cf-lifecycle-action="secondary"', html)
        self.assertIn(REVERSE_AR, html)

    def test_recheck_due_offers_the_recheck_action_only(self) -> None:
        html = paint(projection(phase=PHASE_RECHECK_DUE), phase=PHASE_RECHECK_DUE)
        self.assertIn('data-cf2-mission-act="recheck"', html)
        self.assertNotIn('data-cf2-mission-act="accept"', html)
        self.assertNotIn('data-cf2-mission-act="confirm"', html)
        self.assertNotIn('data-cf2-mission-act="abandon"', html)

    def test_blocked_renders_no_executable_control(self) -> None:
        html = paint(projection(conflict=CONFLICT_CAPACITY_ONLY))
        self.assertIn('data-cf-intervention-cta="0"', html)
        self.assertNotIn("data-cf-lifecycle-action=", html)
        self.assertNotIn("<button", html)

    def test_no_state_shows_two_primary_controls(self) -> None:
        for phase in (None, PHASE_ACTION_CHOSEN, PHASE_UNDER_MEASUREMENT, PHASE_RECHECK_DUE):
            with self.subTest(phase=phase):
                html = paint(projection(phase=phase), phase=phase)
                dominant = html.count('data-cf-lifecycle-action="primary"') + html.count(
                    'data-cf-lifecycle-action="confirm"'
                )
                self.assertLessEqual(dominant, 1)

    def test_no_state_shows_contradictory_controls(self) -> None:
        html = paint(projection(phase=PHASE_UNDER_MEASUREMENT), phase=PHASE_UNDER_MEASUREMENT)
        self.assertNotIn(ACCEPT_AR, html)
        blocked = paint(projection(conflict=CONFLICT_CAPACITY_ONLY))
        self.assertNotIn(ACCEPT_AR, blocked)


class LifecycleActionStyleTests(unittest.TestCase):
    """A frozen, reusable style family — never one-off inline styling."""

    def test_the_three_classes_exist(self) -> None:
        for cls in ("--primary", "--confirm", "--secondary"):
            self.assertIn(".cf-lifecycle-action" + cls, WORKSPACE_CSS)
            self.assertIn("cf-lifecycle-action" + cls, WORKSPACE_JS)

    def test_geometry_is_shared_by_the_base_class(self) -> None:
        start = WORKSPACE_CSS.index('body[data-cf-ui="v2"] .cf-lifecycle-action {')
        base = WORKSPACE_CSS[start : WORKSPACE_CSS.index("}", start)]
        for prop in ("min-height", "border-radius", "font-weight", "padding", "font-size"):
            self.assertIn(prop, base)

    def test_focus_and_pressed_states_exist(self) -> None:
        self.assertIn(".cf-lifecycle-action:focus-visible", WORKSPACE_CSS)
        self.assertIn(".cf-lifecycle-action:active", WORKSPACE_CSS)

    def test_primary_and_confirm_are_dark_and_reversal_is_not_red(self) -> None:
        def block(sel: str) -> str:
            start = WORKSPACE_CSS.index('body[data-cf-ui="v2"] ' + sel + " {")
            return WORKSPACE_CSS[start : WORKSPACE_CSS.index("}", start)]

        self.assertIn("#14181c", block(".cf-lifecycle-action--primary"))
        self.assertIn("#1f2630", block(".cf-lifecycle-action--confirm"))
        reversal = block(".cf-lifecycle-action--secondary")
        self.assertIn("transparent", reversal)
        for red in ("#d0", "#e0", "#f0", "red", "crimson"):
            self.assertNotIn(red, reversal.lower())

    def test_no_inline_style_attribute_on_lifecycle_controls(self) -> None:
        start = WORKSPACE_JS.index("function renderMissionActions")
        end = WORKSPACE_JS.index("async function missionPost")
        self.assertNotIn("style=", WORKSPACE_JS[start:end])


class OwnershipAndCostTests(unittest.TestCase):
    """No new business logic, no new read."""

    def test_projection_module_makes_no_query(self) -> None:
        tree = ast.parse(PROJECTION_SRC)
        verbs = {"query", "execute", "session", "commit", "add", "filter", "get_or_404"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, verbs)
        for token in ("db.", "sqlalchemy", "requests", "httpx", "openai", "aiohttp"):
            self.assertNotIn(token, PROJECTION_SRC)

    def test_heading_is_derived_server_side_not_in_the_browser(self) -> None:
        start = WORKSPACE_JS.index("function renderInterventionDecision")
        end = WORKSPACE_JS.index("function renderColDecision")
        body = WORKSPACE_JS[start:end]
        self.assertIn("iv.heading_state", body)
        for heading in HEADINGS_AR.values():
            if heading == "ما التدخل المقترح الآن؟":
                continue  # the only literal kept, as the render-time fallback
            self.assertNotIn(heading, body)

    def test_control_matrix_reads_cdc_phase_only(self) -> None:
        start = WORKSPACE_JS.index("function renderMissionActions")
        end = WORKSPACE_JS.index("async function missionPost")
        body = WORKSPACE_JS[start:end]
        self.assertIn('var phase = c && c.phase ? String(c.phase) : "";', body)
        for token in ("sort(", "truth_class", "recommendation_level", "conflict_type"):
            self.assertNotIn(token, body)

    def test_shipping_diagnosis_is_unchanged(self) -> None:
        p = projection()
        self.assertEqual(p["family"], SHIPPING)
        self.assertEqual(p["recommendation_level"], 2)
        self.assertIn("12 من 20", p["evidence_ar"])
        self.assertIn("60", p["primary_metric"])

    def test_merchant_facing_cross_sell_term_is_absent(self) -> None:
        self.assertNotIn("البيع المتقاطع", WORKSPACE_JS)
        self.assertNotIn("البيع المتقاطع", PROJECTION_SRC)
        self.assertNotIn("البيع المتقاطع", paint(projection()))


if __name__ == "__main__":
    unittest.main()
