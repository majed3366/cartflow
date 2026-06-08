# -*- coding: utf-8 -*-
"""WhatsApp Onboarding Journeys UI V1."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from extensions import db
from models import Store
from services.admin_whatsapp_visibility_v1 import build_admin_whatsapp_store_row
from services.merchant_whatsapp_connection_readiness_v1 import (
    connection_readiness_for_merchant_api,
)
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    CTA_CHOOSE_JOURNEY_AR,
    CTA_CONTINUE_ACTIVATION_AR,
    JOURNEY_EXISTING_WHATSAPP_BUSINESS,
    JOURNEY_META_READY,
    JOURNEY_NEW_NUMBER,
    JOURNEY_NO_WHATSAPP_BUSINESS,
    JOURNEY_SELECTOR_TITLE_AR,
    CANONICAL_ONBOARDING_JOURNEYS,
    journey_guidance_for_key,
    onboarding_journey_options_for_api,
    onboarding_journeys_ui_block,
)

_BANNED = ("waba", "cloud api", "token", "webhook", "system user")


class MerchantWhatsappOnboardingJourneysV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        db.create_all()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_journey_{uuid.uuid4().hex[:12]}"
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()
        self.row = Store(
            zid_store_id=self.zid,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(self.row)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()

    def test_journey_selector_options_render(self) -> None:
        opts = onboarding_journey_options_for_api()
        self.assertEqual(len(opts), 4)
        self.assertEqual(opts[0]["label_ar"], "لدي واتساب أعمال")

    def test_each_journey_has_guidance_steps(self) -> None:
        for key in CANONICAL_ONBOARDING_JOURNEYS:
            g = journey_guidance_for_key(key)
            self.assertGreaterEqual(len(g["steps_ar"]), 3, msg=key)
            self.assertTrue(g["next_action_ar"], msg=key)
            self.assertTrue(g["expected_outcome_ar"], msg=key)

    def test_existing_whatsapp_business_guidance(self) -> None:
        g = journey_guidance_for_key(JOURNEY_EXISTING_WHATSAPP_BUSINESS)
        blob = " ".join(g["steps_ar"] + [g["next_action_ar"]])
        self.assertIn("رقم واتساب أعمال", blob)

    def test_no_whatsapp_business_guidance(self) -> None:
        g = journey_guidance_for_key(JOURNEY_NO_WHATSAPP_BUSINESS)
        self.assertIn("أنشئ حساب واتساب أعمال", g["steps_ar"][0])

    def test_meta_ready_shows_honest_placeholder(self) -> None:
        g = journey_guidance_for_key(JOURNEY_META_READY)
        self.assertIn("قيد التجهيز", g["placeholder_ar"])

    def test_new_number_guidance(self) -> None:
        g = journey_guidance_for_key(JOURNEY_NEW_NUMBER)
        self.assertIn("رقماً مخصصاً", g["steps_ar"][0])

    def test_journey_persists_on_store(self) -> None:
        from services.merchant_whatsapp_onboarding_journeys_v1 import (
            apply_whatsapp_onboarding_journey_from_body,
        )

        apply_whatsapp_onboarding_journey_from_body(
            self.row,
            {"whatsapp_onboarding_journey": JOURNEY_EXISTING_WHATSAPP_BUSINESS},
        )
        db.session.commit()
        self.assertEqual(
            self.row.whatsapp_onboarding_journey,
            JOURNEY_EXISTING_WHATSAPP_BUSINESS,
        )

    def test_api_includes_journey_fields(self) -> None:
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("whatsapp_onboarding_journeys", data)
        journeys = data["whatsapp_onboarding_journeys"]
        self.assertEqual(len(journeys.get("options") or []), 4)

    def test_api_post_returns_selected_journey(self) -> None:
        post = self.client.post(
            "/api/recovery-settings",
            json={"whatsapp_onboarding_journey": JOURNEY_EXISTING_WHATSAPP_BUSINESS},
        )
        self.assertEqual(post.status_code, 200, post.text[:300])
        data = post.json()
        self.assertEqual(
            data.get("whatsapp_onboarding_journey"),
            JOURNEY_EXISTING_WHATSAPP_BUSINESS,
        )

    def test_invalid_journey_normalized_to_null_on_apply(self) -> None:
        from services.merchant_whatsapp_onboarding_journeys_v1 import (
            apply_whatsapp_onboarding_journey_from_body,
        )

        apply_whatsapp_onboarding_journey_from_body(
            self.row, {"whatsapp_onboarding_journey": "not_a_real_journey"}
        )
        db.session.commit()
        self.assertIsNone(self.row.whatsapp_onboarding_journey)

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value={
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": False,
                "provider_ready": True,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        },
    )
    def test_readiness_without_journey_shows_choose_cta(self, _m: object) -> None:
        ev = connection_readiness_for_merchant_api(self.row)
        af = ev.get("action_first") or {}
        self.assertEqual(af.get("primary_cta_label_ar"), CTA_CHOOSE_JOURNEY_AR)
        journeys = ev.get("whatsapp_onboarding_journeys") or {}
        self.assertTrue(journeys.get("journey_required"))

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value={
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": True,
                "provider_ready": True,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": False,
            },
            "blocking_steps": [],
        },
    )
    def test_readiness_with_journey_shows_continue_cta(self, _m: object) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        db.session.commit()
        ev = connection_readiness_for_merchant_api(self.row)
        af = ev.get("action_first") or {}
        self.assertEqual(af.get("primary_cta_label_ar"), CTA_CONTINUE_ACTIVATION_AR)
        journeys = ev.get("whatsapp_onboarding_journeys") or {}
        self.assertEqual(
            journeys.get("selected_key"), JOURNEY_EXISTING_WHATSAPP_BUSINESS
        )
        self.assertIn("إدخال الرقم وتفعيل الاسترجاع", af.get("next_action_ar") or "")

    def test_admin_row_includes_onboarding_journey(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_NEW_NUMBER
        db.session.commit()
        admin = build_admin_whatsapp_store_row(self.row)
        d = admin.to_api_dict()
        self.assertEqual(d["whatsapp_onboarding_journey"], JOURNEY_NEW_NUMBER)
        self.assertIn("رقماً جديداً", d["whatsapp_onboarding_journey_ar"])

    def test_no_banned_technical_terms_in_merchant_copy(self) -> None:
        block = onboarding_journeys_ui_block(self.row)
        parts = [block["title_ar"]]
        for opt in block["options"]:
            parts.extend([opt["label_ar"], opt["description_ar"]])
        for key in CANONICAL_ONBOARDING_JOURNEYS:
            g = journey_guidance_for_key(key)
            parts.extend(g["steps_ar"])
            parts.append(g["next_action_ar"])
            parts.append(g["expected_outcome_ar"])
            parts.append(g.get("placeholder_ar") or "")
        blob = " ".join(parts).lower()
        for term in _BANNED:
            self.assertNotIn(term, blob, msg=f"leaked {term}")

    def test_js_renders_journey_selector(self) -> None:
        from pathlib import Path

        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("renderJourneyBlock", js)
        self.assertIn("data-ma-wa-journey-key", js)
        self.assertIn("open_journey_selector", js)
        self.assertIn(JOURNEY_SELECTOR_TITLE_AR, js)


if __name__ == "__main__":
    unittest.main()
