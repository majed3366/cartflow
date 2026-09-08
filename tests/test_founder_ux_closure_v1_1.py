# -*- coding: utf-8 -*-
"""Founder UX Closure V1.1 — language consistency, CTA cue, shipping/delivery."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.commercial_action_language_v1.contract_v1 import (
    ACCEPTED_STATE_AR,
    CTA_ACCEPT_MISSION_AR,
    FAMILY_PRICE,
    FAMILY_SHIPPING,
    FAMILY_WAIT,
    FORBIDDEN_WIDGET_ALT_AR,
    FORBIDDEN_WIDGET_AR,
    MISSION_SHIPPING_AR,
    contract_for_family_v1,
)
from services.commercial_action_language_v1.execution_path_v1 import EXECUTION_CTA_AR
from services.commercial_action_language_v1.project_v1 import (
    project_commercial_action_language_v1,
)
from services.commercial_opportunity_layer_v1.compose_v1 import (
    compose_commercial_opportunity_layer_v1,
)
from services.mission_catalog_v1.compose_v1 import compose_mission_catalog_v1
from services.operational_guidance_v1.compose_v1 import (
    compose_from_hesitation_distribution_v1,
    compose_wait_insufficient_v1,
)

ROOT = Path(__file__).resolve().parents[1]

STALE_HOME_PHRASES = (
    "راجع نصوص سبب",
    "واصل جمع الأدلة",
    "لا يستطيع CartFlow تحديد السبب التشغيلي",
    FORBIDDEN_WIDGET_AR,
    FORBIDDEN_WIDGET_ALT_AR,
)


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
    ogl = compose_from_hesitation_distribution_v1(
        store_slug="cf_live_reality_lab",
        total=20,
        distribution={"shipping": 12, "price": 5, "thinking": 3},
    )
    body = {
        "commercial_opportunity_layer_v1": col,
        "mission_catalog_v1": cat,
        "operational_guidance_v1": ogl,
        "home_executive_summary_v1": {
            "ok": True,
            "operational_guidance_v1": {
                "ok": True,
                "family": (ogl or {}).get("family"),
                "home_surface": dict(((ogl or {}).get("home_surface") or {})),
            },
        },
    }
    project_commercial_action_language_v1(body)
    return body


class FounderUxClosureV11Tests(unittest.TestCase):
    def test_home_and_workspace_share_shipping_decision_contract(self) -> None:
        body = _r17_overlaid()
        col = body["commercial_opportunity_layer_v1"]
        cat = body["mission_catalog_v1"]
        ogl = body["operational_guidance_v1"]
        primary = col["primary"]
        card = cat["primary"]
        dc = primary["decision_contract_ar"]
        self.assertEqual(primary["family"], FAMILY_SHIPPING)
        self.assertEqual(card["family"], FAMILY_SHIPPING)
        self.assertEqual(primary["title_ar"], card["title_ar"])
        self.assertEqual(dc["decision_ar"], card["title_ar"])
        self.assertEqual(dc["do_this_ar"], card["mission_ar"])
        self.assertEqual(card["mission_ar"], MISSION_SHIPPING_AR)
        hs = ogl["home_surface"]
        self.assertIn("12", hs["what_we_see_ar"])
        self.assertIn("20", hs["what_we_see_ar"])
        self.assertIn("60", hs["what_we_see_ar"])
        self.assertEqual(hs["what_we_see_ar"], dc["why_now_ar"])
        self.assertEqual(hs["what_it_means_ar"], dc["diagnosis_ar"])
        self.assertEqual(hs["what_to_do_now_ar"], card["action_ar"])
        nested = body["home_executive_summary_v1"]["operational_guidance_v1"]["home_surface"]
        self.assertEqual(nested["what_we_see_ar"], hs["what_we_see_ar"])
        home = _read("static/merchant_ui_v2_home.js")
        self.assertIn("commercialContractGuide", home)
        self.assertIn("isStaleMerchantCopy", home)
        self.assertIn("sectionHasStaleMerchantCopy", home)
        self.assertIn("تحديد السبب التشغيلي", home)
        self.assertIn("Prefer overlaid top-level OGL", home)
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn("card.mission_ar || card.action_ar", ws)
        self.assertIn("decision_contract_ar", ws)

    def test_stale_home_shipping_copy_is_zero(self) -> None:
        body = _r17_overlaid()
        hs = body["operational_guidance_v1"]["home_surface"]
        primary = body["commercial_opportunity_layer_v1"]["primary"]
        card = body["mission_catalog_v1"]["primary"]
        blob = " ".join(
            [
                str(hs.get("what_we_see_ar") or ""),
                str(hs.get("what_it_means_ar") or ""),
                str(hs.get("what_to_do_now_ar") or ""),
                str(primary.get("title_ar") or ""),
                str(primary.get("why_ar") or ""),
                str(primary.get("action_ar") or ""),
                str((primary.get("decision_contract_ar") or {}).get("do_this_ar") or ""),
                str(card.get("mission_ar") or ""),
                str(card.get("why_ar") or ""),
            ]
        )
        stale = 0
        for phrase in STALE_HOME_PHRASES:
            stale += blob.count(phrase)
        self.assertEqual(stale, 0)

    def test_wait_ogl_does_not_keep_stale_copy_when_catalog_is_shipping(self) -> None:
        summary = _r17_summary()
        col = compose_commercial_opportunity_layer_v1(summary)
        cat = compose_mission_catalog_v1(
            col_package=col, store_slug="cf_live_reality_lab"
        )
        wait = compose_wait_insufficient_v1(
            store_slug="cf_live_reality_lab",
            missing_ar="عدد أسباب التردد المسجّلة (3) أقل من الحد الآمن (8).",
            observe_ar="استمر في تشغيل الودجيت لجمع أسباب تردد مؤهّلة دون تغيير السعر أو الشحن.",
            unlock_ar="أعد القرار عندما يصل إجمالي أسباب التردد إلى 8.",
        )
        self.assertEqual(wait.get("family"), FAMILY_WAIT)
        body = {
            "commercial_opportunity_layer_v1": col,
            "mission_catalog_v1": cat,
            "operational_guidance_v1": wait,
        }
        project_commercial_action_language_v1(body)
        ogl = body["operational_guidance_v1"]
        self.assertEqual(ogl.get("family"), FAMILY_WAIT)
        hs = ogl.get("home_surface") or {}
        see = str(hs.get("what_we_see_ar") or "")
        do_now = str(hs.get("what_to_do_now_ar") or "")
        self.assertIn("12", see)
        self.assertIn("60", see)
        self.assertNotIn("ودج", see)
        self.assertNotIn("ودج", do_now)
        self.assertNotIn("واصل جمع الأدلة", do_now)
        self.assertNotIn("راجع نصوص سبب", do_now)

    def test_shipping_and_price_numeric_truth_isolated(self) -> None:
        body = _r17_overlaid()
        primary = body["commercial_opportunity_layer_v1"]["primary"]
        self.assertEqual(primary["family"], FAMILY_SHIPPING)
        ev = (primary.get("evidence") or {}).get("counts") or {}
        self.assertEqual(ev.get("top_count"), 12)
        self.assertEqual(ev.get("hesitation_total"), 20)
        self.assertIn("12 من 20", primary["why_ar"])
        self.assertIn("60", primary["why_ar"])
        price_rows = [
            r
            for r in (body["commercial_opportunity_layer_v1"].get("secondaries") or [])
            if r.get("family") == FAMILY_PRICE
        ]
        self.assertTrue(price_rows)
        self.assertIn("5 من 20", price_rows[0]["why_ar"])
        self.assertIn("25", price_rows[0]["why_ar"])
        self.assertNotIn("12 من 20", price_rows[0]["why_ar"])
        contamination = 0
        for row in price_rows:
            if "12 من 20" in str(row.get("why_ar") or ""):
                contamination += 1
        self.assertEqual(contamination, 0)

    def test_no_widget_in_r17_commercial_mission_copy(self) -> None:
        pack = contract_for_family_v1(
            FAMILY_SHIPPING,
            evidence={
                "counts": {
                    "hesitation_total": 20,
                    "top_reason": "shipping",
                    "top_count": 12,
                    "top_share": 0.6,
                }
            },
        )
        assert pack is not None
        blob = " ".join(pack.values())
        self.assertEqual(blob.count(FORBIDDEN_WIDGET_AR), 0)
        self.assertEqual(blob.count(FORBIDDEN_WIDGET_ALT_AR), 0)
        self.assertEqual(blob.count("ودجت"), 0)
        body = _r17_overlaid()
        mission = body["mission_catalog_v1"]["primary"]["mission_ar"]
        self.assertNotIn("ودج", mission)
        self.assertEqual(mission, MISSION_SHIPPING_AR)

    def test_mission_wording_is_merchant_arabic(self) -> None:
        self.assertEqual(
            MISSION_SHIPPING_AR,
            "حدّد هل التردد مرتبط بتكلفة الشحن أم مدة التوصيل قبل أي تغيير في السعر.",
        )
        pack = contract_for_family_v1(FAMILY_SHIPPING)
        assert pack is not None
        self.assertEqual(pack["mission_ar"], MISSION_SHIPPING_AR)
        self.assertNotEqual(pack["mission_ar"], pack["action_ar"])
        self.assertNotIn("المهيمن", pack["mission_ar"])
        self.assertNotIn("المهمين", pack["mission_ar"])
        self.assertNotIn("ميّز سبب", pack["mission_ar"])

    def test_execution_cta_uses_settings_icon_not_accordion_chevron(self) -> None:
        css = _read("static/merchant_ui_v2_workspace.css")
        js = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn(EXECUTION_CTA_AR, js)
        self.assertIn('data-cf2-mission-cue="gear"', js)
        self.assertIn("cf2-mission__btn-cue-svg", js)
        self.assertIn("cf2-mission__btn-cue-svg", css)
        cue_start = css.index("body[data-cf-ui=\"v2\"] .cf2-mission__btn-cue {")
        cue_end = css.index("body[data-cf-ui=\"v2\"] .cf2-mission__hint", cue_start)
        cue_block = css[cue_start:cue_end]
        self.assertNotIn("rotate(45deg)", cue_block)
        self.assertNotIn("border-block-end: 2px solid currentColor", cue_block)
        self.assertIn("a.cf2-mission__btn--exec", css)
        self.assertIn("min-height: 44px", css)

    def test_accepted_state_copy_does_not_imply_execution(self) -> None:
        self.assertEqual(
            ACCEPTED_STATE_AR,
            "هذه مهمتك الحالية حتى تُنفَّذ أو تتغير الأدلة.",
        )
        ws = _read("static/merchant_ui_v2_workspace.js")
        home = _read("static/merchant_ui_v2_home.js")
        self.assertIn(ACCEPTED_STATE_AR, ws)
        self.assertIn(ACCEPTED_STATE_AR, home)
        self.assertNotIn("لا نستبدله بفرصة أضعف", ws)
        self.assertNotIn("بانتظار إثبات التنفيذ", ws)
        body = _r17_overlaid()
        body["mission_catalog_v1"]["primary"]["cdc_phase"] = "ACTION_CHOSEN"
        body["mission_catalog_v1"]["explain"] = {
            "why_this_one_now_ar": "قرار معتمد بانتظار إثبات التنفيذ — لا نستبدله بفرصة أضعف."
        }
        project_commercial_action_language_v1(body)
        self.assertEqual(
            body["mission_catalog_v1"]["explain"]["why_this_one_now_ar"],
            ACCEPTED_STATE_AR,
        )
        self.assertNotIn("بدأ", ACCEPTED_STATE_AR)
        self.assertNotIn("جاري التنفيذ", ACCEPTED_STATE_AR)

    def test_shipping_and_delivery_are_visible_and_separate(self) -> None:
        html = _read("templates/partials/merchant_settings_canonical_v1.html")
        tpl = _read("static/merchant_trigger_templates.js")
        css = _read("static/merchant_ui_v2_settings.css")
        self.assertNotIn('id="ma-rec-mission-pair"', html)
        self.assertEqual(html.count('data-cf2-rec-pick="shipping"'), 0)
        self.assertEqual(html.count('data-cf2-rec-pick="delivery"'), 0)
        self.assertIn("مدة التوصيل", html)
        self.assertIn("تكلفة الشحن مرتفعة", html)
        self.assertIn("مدة التوصيل طويلة", html)
        self.assertIn('keys = ["shipping", "delivery"]', tpl)
        self.assertIn("shipping: 0, delivery: 1", tpl)
        self.assertNotIn("pairMetaForKey", tpl)
        self.assertNotIn("card.scrollIntoView", tpl)
        self.assertIn("flex-wrap: wrap", css)
        self.assertNotIn(".cf2-rec-mission-pair", css)
        self.assertIn('shipping: "الشحن"', tpl)
        self.assertIn('delivery: "مدة التوصيل"', tpl)
        self.assertNotEqual(
            tpl.split('shipping: "')[1].split('"')[0],
            tpl.split('delivery: "')[1].split('"')[0],
        )

    def test_accept_is_not_execute_and_deeplink_is_not_measurement(self) -> None:
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn(CTA_ACCEPT_MISSION_AR, ws)
        self.assertIn('data-cf2-mission-act="accept"', ws)
        self.assertIn("القبول يسجّل القرار فقط", ws)
        self.assertIn("فتح الإعدادات لا يبدأ القياس", ws)
        self.assertLess(ws.index('act === "accept"'), ws.index("confirm-execution"))
        settings = _read("static/merchant_ui_v2_settings.js")
        self.assertNotIn("UNDER_MEASUREMENT", settings)
        self.assertNotIn("/api/commercial-mission", settings)

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

    def test_visual_restraints_remain(self) -> None:
        frame = _read("static/merchant_ui_v2_frame.css")
        self.assertIn("#d7eeec", frame)
        self.assertIn("#0d6e69", frame)
        js = _read("static/commercial_decision_arc_production_v1.js")
        self.assertNotIn('viewBox="0 0 120 300"', js)
        self.assertIn("cf-cda__rail", js)
        home_css = _read("static/merchant_ui_v2_home.css")
        self.assertNotIn("max-width: 18ch", home_css)
        self.assertIn("overflow-wrap: break-word", home_css)


if __name__ == "__main__":
    unittest.main()
