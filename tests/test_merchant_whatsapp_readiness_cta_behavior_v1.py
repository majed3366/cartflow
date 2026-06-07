# -*- coding: utf-8 -*-
"""WhatsApp Readiness primary CTA behavior — action-aware, never silent."""
from __future__ import annotations

import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from extensions import db
from models import Store
from services.merchant_whatsapp_connection_readiness_v1 import (
    CTA_ACTION_FOCUS_RESUME,
    CTA_ACTION_OPEN_ADVANCED_MERCHANT,
    CTA_ACTION_SCROLL_SETTINGS,
    CTA_ACTION_SHOW_PROVIDER_STATUS,
    CONNECTION_STATE_CONNECTED,
    CONNECTION_STATE_PAUSED,
    CONNECTION_STATE_PENDING_CONFIGURATION,
    CONNECTION_STATE_PROVIDER_ISSUE,
    CONNECTION_STATE_SETUP_REQUIRED,
    _CTA_MISSING_FIELDS_GUIDANCE_AR,
    _CTA_MERCHANT_PLACEHOLDER_AR,
    connection_readiness_for_merchant_api,
    resolve_readiness_primary_cta_behavior,
)
from services.merchant_whatsapp_mode_v1 import (
    WHATSAPP_MODE_CARTFLOW_MANAGED,
    WHATSAPP_MODE_MERCHANT_WHATSAPP,
)


class WhatsappReadinessCtaBehaviorV1Tests(unittest.TestCase):
    def test_cartflow_managed_scrolls_and_highlights_settings(self) -> None:
        behavior = resolve_readiness_primary_cta_behavior(
            CONNECTION_STATE_PENDING_CONFIGURATION,
            WHATSAPP_MODE_CARTFLOW_MANAGED,
            store_whatsapp_number="",
            recovery_enabled=False,
        )
        self.assertEqual(behavior["cta_action"], CTA_ACTION_SCROLL_SETTINGS)
        self.assertIn("store_number", behavior["highlight_fields"])
        self.assertIn("recovery_enabled", behavior["highlight_fields"])
        self.assertTrue(behavior["never_silent"])

    def test_missing_number_shows_guidance(self) -> None:
        behavior = resolve_readiness_primary_cta_behavior(
            CONNECTION_STATE_SETUP_REQUIRED,
            WHATSAPP_MODE_CARTFLOW_MANAGED,
            store_whatsapp_number="",
            recovery_enabled=True,
        )
        self.assertEqual(behavior["inline_guidance_ar"], _CTA_MISSING_FIELDS_GUIDANCE_AR)

    def test_merchant_whatsapp_opens_advanced_placeholder(self) -> None:
        behavior = resolve_readiness_primary_cta_behavior(
            CONNECTION_STATE_SETUP_REQUIRED,
            WHATSAPP_MODE_MERCHANT_WHATSAPP,
        )
        self.assertEqual(behavior["cta_action"], CTA_ACTION_OPEN_ADVANCED_MERCHANT)
        self.assertEqual(behavior["placeholder_ar"], _CTA_MERCHANT_PLACEHOLDER_AR)

    def test_connected_scrolls_to_settings(self) -> None:
        behavior = resolve_readiness_primary_cta_behavior(
            CONNECTION_STATE_CONNECTED,
            WHATSAPP_MODE_CARTFLOW_MANAGED,
        )
        self.assertEqual(behavior["cta_action"], CTA_ACTION_SCROLL_SETTINGS)

    def test_paused_focuses_resume_when_disabled(self) -> None:
        behavior = resolve_readiness_primary_cta_behavior(
            CONNECTION_STATE_PAUSED,
            WHATSAPP_MODE_CARTFLOW_MANAGED,
            recovery_enabled=False,
            production_truth={"action_required_ar": "فعّل استرجاع واتساب من هذه الصفحة."},
        )
        self.assertEqual(behavior["cta_action"], CTA_ACTION_FOCUS_RESUME)
        self.assertIn("recovery_enabled", behavior["highlight_fields"])
        self.assertIn("فعّل", behavior["inline_guidance_ar"])

    def test_provider_issue_shows_status_explanation(self) -> None:
        behavior = resolve_readiness_primary_cta_behavior(
            CONNECTION_STATE_PROVIDER_ISSUE,
            WHATSAPP_MODE_CARTFLOW_MANAGED,
            production_truth={
                "why_not_connected_ar": "قناة واتساب تحتاج متابعة قبل الإنتاج الكامل."
            },
        )
        self.assertEqual(behavior["cta_action"], CTA_ACTION_SHOW_PROVIDER_STATUS)
        self.assertTrue(behavior["status_explanation_ar"])

    def test_never_silent_for_all_canonical_states(self) -> None:
        from services.merchant_whatsapp_connection_readiness_v1 import (
            CANONICAL_CONNECTION_STATES,
        )

        for state in CANONICAL_CONNECTION_STATES:
            behavior = resolve_readiness_primary_cta_behavior(
                state, WHATSAPP_MODE_CARTFLOW_MANAGED
            )
            self.assertTrue(behavior["never_silent"], msg=state)
            self.assertTrue(behavior["cta_action"], msg=state)

    def test_merchant_api_includes_cta_behavior(self) -> None:
        db.create_all()
        zid = f"wa_cta_{uuid.uuid4().hex[:12]}"
        row = Store(
            zid_store_id=zid,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            whatsapp_recovery_enabled=False,
            store_whatsapp_number="",
        )
        db.session.add(row)
        db.session.commit()
        try:
            with patch(
                "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
                return_value={
                    "flags": {
                        "dashboard_ready": True,
                        "store_connected": True,
                        "whatsapp_configured": False,
                        "provider_ready": True,
                        "recovery_enabled": False,
                        "widget_installed": True,
                        "sandbox_mode_active": True,
                    },
                    "blocking_steps": ["recovery_disabled"],
                },
            ):
                ev = connection_readiness_for_merchant_api(row)
            af = ev.get("action_first") or {}
            self.assertIn("cta_behavior", af)
            self.assertTrue(af["cta_behavior"].get("never_silent"))
        finally:
            db.session.query(Store).filter_by(zid_store_id=zid).delete(
                synchronize_session=False
            )
            db.session.commit()

    def test_dashboard_whatsapp_page_has_cta_guidance_container(self) -> None:
        html = Path("templates/merchant_app.html").read_text(encoding="utf-8")
        self.assertIn('id="ma-wa-cta-guidance"', html)

    def test_js_wires_action_aware_cta_handler(self) -> None:
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("handlePrimaryCtaClick", js)
        self.assertIn("cta_behavior", js)
        self.assertIn("ma-wa-cta-guidance", js)
        self.assertIn("data-cf-wa-primary-cta", js)

    def test_readiness_cta_inherits_font_family(self) -> None:
        css = Path("static/merchant_app.css").read_text(encoding="utf-8")
        start = css.index(".ma-wa-readiness-cta {")
        end = css.index(".ma-wa-readiness-cta:hover", start)
        block = css[start:end]
        self.assertIn("font-family: inherit", block)


if __name__ == "__main__":
    unittest.main()
