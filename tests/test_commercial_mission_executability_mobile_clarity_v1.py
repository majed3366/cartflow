# -*- coding: utf-8 -*-
"""Commercial Mission Executability & Mobile Clarity V1 — failure tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.commercial_action_language_v1.contract_v1 import (
    CTA_ACCEPT_MISSION_AR,
    FAMILY_SHIPPING,
    contract_for_family_v1,
)
from services.commercial_action_language_v1.execution_path_v1 import (
    EXECUTION_CTA_AR,
    SETTINGS_EXECUTION_HASH,
    SETTINGS_SURFACE_AR,
    shipping_distinction_executable_v1,
)
from services.commercial_action_language_v1.project_v1 import (
    project_commercial_action_language_v1,
)
from services.commercial_opportunity_layer_v1.compose_v1 import (
    compose_commercial_opportunity_layer_v1,
)
from services.recovery_timing_presentation_v1 import (
    first_message_delays_seconds,
    global_send_range_ar,
    selected_stage_timing_ar,
)

ROOT = Path(__file__).resolve().parents[1]

MERCHANT_FACING_PATHS = (
    ROOT / "services" / "commercial_action_language_v1" / "contract_v1.py",
    ROOT / "services" / "commercial_action_language_v1" / "execution_path_v1.py",
    ROOT / "static" / "merchant_ui_v2_workspace.js",
    ROOT / "static" / "merchant_ui_v2_home.js",
    ROOT / "static" / "commercial_decision_arc_production_v1.js",
    ROOT / "static" / "commercial_decision_arc_production_v1.css",
    ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html",
    ROOT / "docs" / "product" / "commercial_action_language_v1" / "README.md",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _merchant_blob() -> str:
    return "\n".join(_read(p) for p in MERCHANT_FACING_PATHS)


class CommercialMissionExecutabilityMobileClarityV1Tests(unittest.TestCase):
    def test_mobile_commercial_text_cannot_clamp_or_ellipsis(self) -> None:
        css = _read(ROOT / "static" / "commercial_decision_arc_production_v1.css")
        self.assertIn("overflow-wrap: break-word", css)
        self.assertNotIn("-webkit-line-clamp", css)
        self.assertNotIn("text-overflow: ellipsis", css)
        js = _read(ROOT / "static" / "commercial_decision_arc_production_v1.js")
        self.assertIn("fieldsFromOpp(opp, true)", js)
        self.assertNotIn("slice(0, 137)", js)

    def test_stale_and_unsafe_shipping_copy_zero_on_merchant_surfaces(self) -> None:
        blob = _merchant_blob()
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
        pack_blob = " ".join(pack.values())
        self.assertEqual(blob.count("احتكاك"), 0)
        self.assertEqual(pack_blob.count("احتكاك"), 0)
        self.assertEqual(blob.count("يوقف الشراء"), 0)
        self.assertEqual(pack_blob.count("يوقف الشراء"), 0)
        self.assertNotIn("يقطع الشراء", pack_blob)
        self.assertNotIn("يغادر العملاء بعد خطوة الشحن", pack_blob)
        self.assertIn("60", pack["evidence_ar"])
        self.assertIn("تكلفة الشحن مرتفعة", pack["action_ar"])
        self.assertIn("مدة التوصيل طويلة", pack["action_ar"])
        self.assertIn("افتح أسباب التردد", pack["action_ar"])
        self.assertIn("قبل أي تغيير في السعر", pack["mission_ar"])
        self.assertNotEqual(pack["mission_ar"], pack["action_ar"])

    def test_shipping_reasons_exist_and_action_is_executable(self) -> None:
        path = shipping_distinction_executable_v1()
        self.assertTrue(path["shipping_cost_reason_exists"])
        self.assertTrue(path["delivery_duration_reason_exists"])
        self.assertTrue(path["merchant_can_enable_each"])
        self.assertTrue(path["action_executable"])
        self.assertFalse(path["merchant_can_add_or_delete_reasons"])
        self.assertEqual(path["cta_ar"], EXECUTION_CTA_AR)
        self.assertEqual(path["destination_hash"], SETTINGS_EXECUTION_HASH)
        self.assertIn("سياسة الاسترجاع", str(path["destination_surface_ar"]))

    def test_execution_cta_reaches_real_settings_surface(self) -> None:
        html = _read(ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html")
        js = _read(ROOT / "static" / "merchant_ui_v2_workspace.js")
        settings = _read(ROOT / "static" / "merchant_ui_v2_settings.js")
        self.assertIn('data-cf2-settings-panel="recovery"', html)
        self.assertIn("أسباب التردد", html)
        self.assertIn(EXECUTION_CTA_AR, js)
        self.assertIn(SETTINGS_EXECUTION_HASH, js)
        self.assertIn("focusFromHash", settings)
        self.assertIn("applyRecoveryFocusFromHash", settings)
        self.assertIn("applyLocationHash", settings)
        self.assertIn("areaFromHash", settings)
        app = _read(ROOT / "static" / "merchant_ui_v2_app.js")
        self.assertIn("applyLocationHash", app)
        self.assertIn("areaFromHash()", app)
        tpl = _read(ROOT / "static" / "merchant_trigger_templates.js")
        self.assertIn("maApplyRecoveryReasonFocus", tpl)
        self.assertIn("shipping-hesitation", tpl)

    def test_accept_does_not_start_execution(self) -> None:
        js = _read(ROOT / "static" / "merchant_ui_v2_workspace.js")
        self.assertIn('اعتمد هذه المهمة', js)
        self.assertIn('data-cf2-mission-act="accept"', js)
        self.assertIn("missionPost(\"accept\", {})", js)
        self.assertNotIn("ابدأ التنفيذ", js)
        self.assertIn("القبول يسجّل القرار فقط", js)
        self.assertIn("فتح الإعدادات لا يبدأ القياس", js)
        self.assertIn('data-cf2-mission-exec="settings"', js)
        accept_idx = js.index("act === \"accept\"")
        exec_idx = js.index("confirm-execution")
        self.assertLess(accept_idx, exec_idx)

    def test_action_unavailable_when_required_reason_missing(self) -> None:
        from services.commercial_action_language_v1 import execution_path_v1 as ep

        real_tags = ep._REASON_TAGS
        try:
            ep._REASON_TAGS = frozenset({"price", "quality"})
            path = ep.shipping_distinction_executable_v1()
            self.assertFalse(path["action_executable"])
            self.assertEqual(path["unavailable_ar"], "ACTION CURRENTLY NOT EXECUTABLE")
            self.assertEqual(path["cta_ar"], "")
        finally:
            ep._REASON_TAGS = real_tags

    def test_global_timing_summary_derived_from_configured_stages(self) -> None:
        rows = [
            {
                "key": "shipping",
                "enabled": True,
                "messages": [{"delay": 60, "unit": "minute"}],
            },
            {
                "key": "price",
                "enabled": True,
                "messages": [{"delay": 30, "unit": "minute"}],
            },
            {
                "key": "delivery",
                "enabled": True,
                "messages": [{"delay": 3, "unit": "hour"}],
            },
        ]
        secs = first_message_delays_seconds(rows)
        summary = global_send_range_ar(secs)
        self.assertEqual(summary, "من 30 دقيقة إلى 3 ساعات بحسب السبب والمرحلة")
        self.assertEqual(
            selected_stage_timing_ar(0, 60, "minute"),
            "الرسالة 1 لهذا السبب: بعد 60 دقيقة من ترك السلة",
        )
        changed = [dict(r) for r in rows]
        changed[0] = {
            "key": "shipping",
            "enabled": True,
            "messages": [{"delay": 90, "unit": "minute"}],
        }
        next_summary = global_send_range_ar(first_message_delays_seconds(changed))
        self.assertEqual(next_summary, "من 30 دقيقة إلى 3 ساعات بحسب السبب والمرحلة")
        changed[2] = {
            "key": "delivery",
            "enabled": True,
            "messages": [{"delay": 2, "unit": "hour"}],
        }
        after = global_send_range_ar(first_message_delays_seconds(changed))
        self.assertEqual(after, "من 30 دقيقة إلى 2 ساعات بحسب السبب والمرحلة")
        tpl = _read(ROOT / "static" / "merchant_trigger_templates.js")
        self.assertIn("formatGlobalSendRangeAr", tpl)
        self.assertIn("messages[0]", tpl)
        self.assertNotIn("30 دقيقة - 3 ساعات", tpl)
        html = _read(ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html")
        self.assertIn("نطاق مواعيد الإرسال الحالية", html)
        self.assertIn("data-ma-tpl-delay-scope", tpl)

    def test_tenant_isolation_hash_is_ui_location_only(self) -> None:
        self.assertNotIn("store_slug", SETTINGS_EXECUTION_HASH)
        self.assertNotIn("tenant", SETTINGS_EXECUTION_HASH)
        self.assertTrue(SETTINGS_EXECUTION_HASH.startswith("#settings?"))
        settings = _read(ROOT / "static" / "merchant_ui_v2_settings.js")
        self.assertIn("focusFromHash", settings)
        self.assertNotIn("CARTFLOW_STORE_SLUG = params", settings)

    def test_sidebar_handle_discoverability_and_a11y_preserved(self) -> None:
        css = _read(ROOT / "static" / "merchant_ui_v2_frame.css")
        html = _read(ROOT / "templates" / "merchant_app_v2.html")
        app = _read(ROOT / "static" / "merchant_ui_v2_app.js")
        self.assertIn("cf2-ctx-handle", html)
        self.assertIn('aria-controls="cf2-ctx"', html)
        self.assertIn("aria-expanded", html)
        self.assertIn("#d7eeec", css.lower())
        self.assertIn("#0d6e69", css.lower())
        self.assertIn(".cf2-ctx-handle:focus-visible", css)
        self.assertIn("toggleCtxDrawer", app)
        self.assertIn("openCtxDrawer", app)

    def test_no_frontend_ranker_and_no_lifecycle_bypass(self) -> None:
        ws = _read(ROOT / "static" / "merchant_ui_v2_workspace.js")
        home = _read(ROOT / "static" / "merchant_ui_v2_home.js")
        for blob in (ws, home):
            self.assertNotIn("rankOpportunities", blob)
            self.assertNotIn("function rerank", blob)
            self.assertNotIn('data-cf2-mission-act="accept" === "confirm"', blob)
        self.assertIn("missionPost(\"accept\", {})", ws)
        self.assertIn("confirm-execution", ws)

    def test_overlay_rewrites_home_title_without_col_family_change(self) -> None:
        col = compose_commercial_opportunity_layer_v1(
            {
                "store_slug": "cf_live_reality_lab",
                "merchant_reason_counts_week": {
                    "shipping": 12,
                    "price": 5,
                    "thinking": 3,
                },
            },
            store_slug="cf_live_reality_lab",
        )
        self.assertEqual((col.get("primary") or {}).get("family"), FAMILY_SHIPPING)
        body = {"commercial_opportunity_layer_v1": col}
        project_commercial_action_language_v1(body)
        primary = body["commercial_opportunity_layer_v1"]["primary"]
        self.assertEqual(primary.get("family"), FAMILY_SHIPPING)
        self.assertNotIn("احتكاك", str(primary.get("title_ar") or ""))
        self.assertEqual((primary.get("decision_contract_ar") or {}).get("cta_ar"), CTA_ACCEPT_MISSION_AR)
        body["mission_catalog_v1"] = {
            "ok": True,
            "primary": {"family": FAMILY_SHIPPING, "title_ar": primary.get("title_ar")},
            "explain": {"why_this_one_now_ar": "احتكاك الشحن يقطع الشراء قبل الدفع."},
        }
        project_commercial_action_language_v1(body)
        expl = (body["mission_catalog_v1"].get("explain") or {}).get("why_this_one_now_ar") or ""
        self.assertNotIn("احتكاك", expl)
        self.assertNotIn("يقطع", expl)
        self.assertIn(SETTINGS_SURFACE_AR, SETTINGS_SURFACE_AR)


if __name__ == "__main__":
    unittest.main()
