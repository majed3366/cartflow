# -*- coding: utf-8 -*-
"""Founder UX Closure V1 — deep-link, clipping, evidence isolation, affordance."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.commercial_action_language_v1.contract_v1 import (
    CTA_ACCEPT_MISSION_AR,
    FAMILY_PRICE,
    FAMILY_SHIPPING,
    contract_for_family_v1,
)
from services.commercial_action_language_v1.execution_path_v1 import (
    EXECUTION_CTA_AR,
    SETTINGS_EXECUTION_HASH,
)
from services.commercial_action_language_v1.project_v1 import (
    project_commercial_action_language_v1,
)
from services.commercial_opportunity_layer_v1.compose_v1 import (
    compose_commercial_opportunity_layer_v1,
)
from services.mission_catalog_v1.compose_v1 import compose_mission_catalog_v1
from services.recovery_timing_presentation_v1 import (
    first_message_delays_seconds,
    global_send_range_ar,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _r17_summary() -> dict:
    return {
        "store_slug": "cf_live_reality_lab",
        "merchant_reason_counts_week": {"shipping": 12, "price": 5, "thinking": 3},
        "merchant_store_cart_counts": {"no_phone_total": 0},
        "truth_class": "production_ready",
    }


class FounderUxClosureV1Tests(unittest.TestCase):
    def test_execution_cta_reaches_recovery_settings_hash(self) -> None:
        ws = _read("static/merchant_ui_v2_workspace.js")
        settings = _read("static/merchant_ui_v2_settings.js")
        html = _read("templates/partials/merchant_settings_canonical_v1.html")
        self.assertIn(EXECUTION_CTA_AR, ws)
        self.assertIn(SETTINGS_EXECUTION_HASH, ws)
        self.assertIn('data-cf2-settings-panel="recovery"', html)
        self.assertIn("أسباب التردد", html)
        self.assertIn('id="cf2-rec-reasons"', html)
        self.assertIn('data-cf2-focus-target="shipping-hesitation"', html)
        self.assertIn("applyLocationHash", settings)
        self.assertIn("areaFromHash", settings)
        app = _read("static/merchant_ui_v2_app.js")
        self.assertIn("applyLocationHash", app)
        self.assertIn("areaFromHash()", app)

    def test_focus_target_resolves_shipping_hesitation(self) -> None:
        tpl = _read("static/merchant_trigger_templates.js")
        self.assertIn('focus === "shipping-hesitation"', tpl)
        self.assertIn('keys = ["shipping", "delivery"]', tpl)
        self.assertIn("cf2-rec-reasons", tpl)

    def test_unknown_focus_fails_safely(self) -> None:
        tpl = _read("static/merchant_trigger_templates.js")
        self.assertIn("Unknown focus is a UI hint miss", tpl)
        settings = _read("static/merchant_ui_v2_settings.js")
        self.assertIn("Unknown area is a UI-location miss", settings)
        self.assertNotIn("if (asked) return asked;", settings)

    def test_navigation_hint_is_not_tenant_authority(self) -> None:
        settings = _read("static/merchant_ui_v2_settings.js")
        app = _read("static/merchant_ui_v2_app.js")
        self.assertIn("never tenant/security authority", settings)
        self.assertNotIn("store_slug = params.get", settings)
        self.assertNotIn("store_slug = params.get", app)
        self.assertNotIn("/api/auth", settings)

    def test_home_has_no_mid_word_truncation_path(self) -> None:
        home = _read("static/merchant_ui_v2_home.js")
        self.assertNotIn("slice(0, 137)", home)
        self.assertNotIn('slice(0, 107) + "…"', home)
        self.assertNotIn('slice(0, 69) + "…"', home)
        css = _read("static/merchant_ui_v2_home.css")
        self.assertNotIn("-webkit-line-clamp", css)
        self.assertNotIn("max-width: 18ch", css)
        self.assertIn("overflow-wrap: break-word", css)

    def test_shipping_and_price_evidence_are_family_owned(self) -> None:
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
        primary = body["commercial_opportunity_layer_v1"]["primary"]
        self.assertEqual(primary["family"], FAMILY_SHIPPING)
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
        cat_secs = body["mission_catalog_v1"].get("secondaries") or []
        price_cat = [r for r in cat_secs if r.get("family") == FAMILY_PRICE]
        if price_cat:
            self.assertIn("5 من 20", price_cat[0]["why_ar"])
            self.assertNotIn("12 من 20", price_cat[0]["why_ar"])

    def test_secondary_cannot_inherit_primary_evidence(self) -> None:
        body = {
            "commercial_opportunity_layer_v1": {
                "primary": {
                    "family": FAMILY_SHIPPING,
                    "evidence": {
                        "counts": {
                            "hesitation_total": 20,
                            "top_reason": "shipping",
                            "top_count": 12,
                            "top_share": 0.6,
                        }
                    },
                },
                "secondaries": [{"family": FAMILY_PRICE, "title_ar": "سعر"}],
            },
            "mission_catalog_v1": {
                "primary": {"family": FAMILY_SHIPPING},
                "secondaries": [{"family": FAMILY_PRICE, "title_ar": "سعر"}],
            },
        }
        project_commercial_action_language_v1(body)
        price = body["mission_catalog_v1"]["secondaries"][0]
        self.assertNotIn("12 من 20", str(price.get("why_ar") or ""))
        self.assertNotIn("60", str(price.get("why_ar") or ""))
        col_price = body["commercial_opportunity_layer_v1"]["secondaries"][0]
        self.assertNotIn("12 من 20", str(col_price.get("why_ar") or ""))

    def test_accept_is_not_execute(self) -> None:
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn(CTA_ACCEPT_MISSION_AR, ws)
        self.assertIn('data-cf2-mission-act="accept"', ws)
        self.assertIn("missionPost(\"accept\", {})", ws)
        self.assertIn("القبول يسجّل القرار فقط", ws)
        self.assertIn("فتح الإعدادات لا يبدأ القياس", ws)
        self.assertLess(ws.index("act === \"accept\""), ws.index("confirm-execution"))

    def test_deeplink_navigation_does_not_start_measurement(self) -> None:
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn('data-cf2-mission-exec="settings"', ws)
        settings = _read("static/merchant_ui_v2_settings.js")
        self.assertNotIn("UNDER_MEASUREMENT", settings)
        self.assertNotIn("confirm-execution", settings)
        self.assertNotIn("/api/commercial-mission", settings)

    def test_sidebar_open_close_unchanged(self) -> None:
        app = _read("static/merchant_ui_v2_app.js")
        self.assertIn("toggleCtxDrawer", app)
        self.assertIn("openCtxDrawer", app)
        self.assertIn("closeCtxDrawer", app)
        self.assertIn("cf2-ctx-handle", app)
        frame = _read("static/merchant_ui_v2_frame.css")
        self.assertIn(".cf2-ctx-handle", frame)
        self.assertIn("#d7eeec", frame)
        self.assertIn("#0d6e69", frame)

    def test_execution_cta_keyboard_and_touch(self) -> None:
        css = _read("static/merchant_ui_v2_workspace.css")
        self.assertIn("a.cf2-mission__btn--exec", css)
        self.assertIn("min-height: 44px", css)
        self.assertIn(":focus-visible", css)
        self.assertIn(":hover", css)
        self.assertIn(":active", css)
        js = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn('href="' , js)
        self.assertIn("cf2-mission__btn--exec", js)
        self.assertIn("<a ", js)

    def test_timing_summary_remains_derived(self) -> None:
        rows = [
            {"key": "shipping", "enabled": True, "messages": [{"delay": 30, "unit": "minute"}]},
            {"key": "delivery", "enabled": True, "messages": [{"delay": 3, "unit": "hour"}]},
        ]
        summary = global_send_range_ar(first_message_delays_seconds(rows))
        self.assertIn("30", summary)
        self.assertIn("3", summary)
        tpl = _read("static/merchant_trigger_templates.js")
        self.assertIn("formatGlobalSendRangeAr", tpl)
        self.assertIn("first_message_delays", _read("services/recovery_timing_presentation_v1.py"))

    def test_no_frontend_ranker_or_lifecycle_bypass(self) -> None:
        for rel in (
            "static/merchant_ui_v2_home.js",
            "static/merchant_ui_v2_workspace.js",
            "static/merchant_ui_v2_settings.js",
        ):
            src = _read(rel)
            self.assertNotIn("compose_commercial_opportunity_layer", src)
            self.assertNotIn("rank_mission_catalog", src)
            self.assertNotIn("UNDER_MEASUREMENT =", src)

    def test_mission_and_operational_copy_are_distinct(self) -> None:
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
        self.assertNotEqual(pack["mission_ar"], pack["action_ar"])
        self.assertIn("قبل أي تغيير في السعر", pack["mission_ar"])
        self.assertIn("افتح أسباب التردد", pack["action_ar"])
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn("card.mission_ar || card.action_ar", ws)
        cda = _read("static/commercial_decision_arc_production_v1.js")
        self.assertIn("القرار", cda)
        self.assertNotIn("cf-cda__scoop", cda)
        self.assertNotIn("cf-cda__taper", cda)

    def test_organism_decorative_mass_removed(self) -> None:
        js = _read("static/commercial_decision_arc_production_v1.js")
        css = _read("static/commercial_decision_arc_production_v1.css")
        self.assertNotIn("viewBox=\"0 0 120 300\"", js)
        self.assertIn("cf-cda__rail", js)
        self.assertIn("grid-template-columns: 16px", css)
        self.assertNotIn("min-height: 168px", css)


if __name__ == "__main__":
    unittest.main()
