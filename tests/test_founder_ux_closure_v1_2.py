# -*- coding: utf-8 -*-
"""Founder UX Closure V1.2 — settings dedupe + confirm language + CTA cue."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.commercial_action_language_v1.contract_v1 import (
    ACCEPTED_STATE_AR,
    CTA_ACCEPT_MISSION_AR,
    FAMILY_PRICE,
    FAMILY_SHIPPING,
    MISSION_SHIPPING_AR,
)
from services.commercial_action_language_v1.execution_path_v1 import EXECUTION_CTA_AR
from services.commercial_action_language_v1.project_v1 import (
    project_commercial_action_language_v1,
)
from services.commercial_opportunity_layer_v1.compose_v1 import (
    compose_commercial_opportunity_layer_v1,
)
from services.mission_catalog_v1.compose_v1 import compose_mission_catalog_v1

ROOT = Path(__file__).resolve().parents[1]

CONFIRM_AR = "أكد إتمام الضبط"
CONFIRM_HINT_AR = "بعد التأكيد يبدأ CartFlow قياس أثر المهمة."


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _r17_summary() -> dict:
    return {
        "store_slug": "cf_live_reality_lab",
        "merchant_reason_counts_week": {"shipping": 12, "price": 5, "thinking": 3},
        "merchant_store_cart_counts": {"no_phone_total": 0},
        "truth_class": "production_ready",
    }


def _r17_overlaid() -> dict:
    summary = _r17_summary()
    col = compose_commercial_opportunity_layer_v1(summary)
    cat = compose_mission_catalog_v1(
        col_package=col, store_slug="cf_live_reality_lab"
    )
    body = {
        "commercial_opportunity_layer_v1": col,
        "mission_catalog_v1": cat,
    }
    project_commercial_action_language_v1(body)
    return body


class FounderUxClosureV12Tests(unittest.TestCase):
    def test_focus_does_not_clone_shipping_or_delivery_cards(self) -> None:
        html = _read("templates/partials/merchant_settings_canonical_v1.html")
        tpl = _read("static/merchant_trigger_templates.js")
        self.assertNotIn("ma-rec-mission-pair", html)
        self.assertNotIn("ma-rec-mission-pair", tpl)
        self.assertNotIn("pairMetaForKey", tpl)
        self.assertEqual(html.count('data-cf2-rec-pick="shipping"'), 0)
        self.assertEqual(html.count('data-cf2-rec-pick="delivery"'), 0)
        self.assertEqual(tpl.count("data-cf2-rec-pick=\"' +"), 1)
        self.assertEqual(tpl.count('<div class="ma-tpl-card" data-ma-tpl-key="'), 1)
        self.assertIn("classList.toggle(\"is-mission-focus\"", tpl)
        self.assertIn("shipping: 0, delivery: 1", tpl)
        self.assertNotIn("cloneNode", tpl)
        focus_fn = tpl.split("function applyRecoveryReasonFocus")[1].split(
            "window.maUpdateRecoveryReasonsSummary"
        )[0]
        self.assertNotIn("createElement", focus_fn)
        self.assertNotIn("innerHTML", focus_fn)

    def test_shipping_and_delivery_remain_separate_and_configurable(self) -> None:
        tpl = _read("static/merchant_trigger_templates.js")
        html = _read("templates/partials/merchant_settings_canonical_v1.html")
        self.assertIn('shipping: "الشحن"', tpl)
        self.assertIn('delivery: "مدة التوصيل"', tpl)
        self.assertNotEqual(
            tpl.split('shipping: "')[1].split('"')[0],
            tpl.split('delivery: "')[1].split('"')[0],
        )
        self.assertIn('keys = ["shipping", "delivery"]', tpl)
        self.assertIn("تكلفة الشحن مرتفعة", html)
        self.assertIn("مدة التوصيل طويلة", html)
        css = _read("static/merchant_ui_v2_settings.css")
        self.assertIn("flex-wrap: wrap", css)
        self.assertIn(".cf2-rec-reason.is-mission-focus", css)

    def test_execution_confirm_language_and_cdc_authority(self) -> None:
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn(CONFIRM_AR, ws)
        self.assertIn(CONFIRM_HINT_AR, ws)
        self.assertNotIn("جعلت أسباب تردد الشحن تفرّق", ws)
        self.assertNotIn("التأكيد = إثبات تنفيذ", ws)
        self.assertIn('data-cf2-mission-act="confirm"', ws)
        self.assertIn('missionPost("confirm-execution"', ws)
        self.assertIn(CTA_ACCEPT_MISSION_AR, ws)
        self.assertIn("القبول يسجّل القرار فقط", ws)
        self.assertIn("فتح الإعدادات لا يبدأ القياس", ws)
        self.assertLess(ws.index('act === "accept"'), ws.index("confirm-execution"))
        settings = _read("static/merchant_ui_v2_settings.js")
        self.assertNotIn("confirm-execution", settings)
        self.assertNotIn("/api/commercial-mission", settings)

    def test_execution_cta_uses_gear_cue(self) -> None:
        js = _read("static/merchant_ui_v2_workspace.js")
        css = _read("static/merchant_ui_v2_workspace.css")
        self.assertIn(EXECUTION_CTA_AR, js)
        self.assertIn('data-cf2-mission-cue="gear"', js)
        self.assertNotIn('data-cf2-mission-cue="settings"', js)
        cue_start = css.index("body[data-cf-ui=\"v2\"] .cf2-mission__btn-cue {")
        cue_end = css.index("body[data-cf-ui=\"v2\"] .cf2-mission__hint", cue_start)
        cue_block = css[cue_start:cue_end]
        self.assertNotIn("rotate(45deg)", cue_block)
        self.assertIn("min-height: 44px", css)

    def test_home_workspace_language_and_evidence_unregressed(self) -> None:
        body = _r17_overlaid()
        primary = body["commercial_opportunity_layer_v1"]["primary"]
        card = body["mission_catalog_v1"]["primary"]
        self.assertEqual(primary["family"], FAMILY_SHIPPING)
        self.assertEqual(card["mission_ar"], MISSION_SHIPPING_AR)
        self.assertIn("12 من 20", primary["why_ar"])
        self.assertIn("60", primary["why_ar"])
        price_rows = [
            r
            for r in (body["commercial_opportunity_layer_v1"].get("secondaries") or [])
            if r.get("family") == FAMILY_PRICE
        ]
        self.assertTrue(price_rows)
        self.assertIn("5 من 20", price_rows[0]["why_ar"])
        self.assertNotIn("12 من 20", price_rows[0]["why_ar"])
        ws = _read("static/merchant_ui_v2_workspace.js")
        home = _read("static/merchant_ui_v2_home.js")
        self.assertIn(ACCEPTED_STATE_AR, ws)
        self.assertIn(ACCEPTED_STATE_AR, home)
        self.assertIn("commercialContractGuide", home)

    def test_timing_and_visual_restraints_unregressed(self) -> None:
        tpl = _read("static/merchant_trigger_templates.js")
        self.assertIn("formatGlobalSendRangeAr", tpl)
        frame = _read("static/merchant_ui_v2_frame.css")
        self.assertIn("#d7eeec", frame)
        self.assertIn("#0d6e69", frame)
        js = _read("static/commercial_decision_arc_production_v1.js")
        self.assertIn("cf-cda__rail", js)
        self.assertNotIn('viewBox="0 0 120 300"', js)

    def test_tenant_isolation_and_no_frontend_ranker(self) -> None:
        settings = _read("static/merchant_ui_v2_settings.js")
        app = _read("static/merchant_ui_v2_app.js")
        self.assertIn("never tenant/security authority", settings)
        self.assertNotIn("store_slug = params.get", settings)
        self.assertNotIn("store_slug = params.get", app)
        for rel in (
            "static/merchant_ui_v2_home.js",
            "static/merchant_ui_v2_workspace.js",
            "static/merchant_ui_v2_settings.js",
        ):
            src = _read(rel)
            self.assertNotIn("compose_commercial_opportunity_layer", src)
            self.assertNotIn("rank_mission_catalog", src)
            self.assertNotIn("UNDER_MEASUREMENT =", src)


if __name__ == "__main__":
    unittest.main()
