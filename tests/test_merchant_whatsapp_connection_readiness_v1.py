# -*- coding: utf-8 -*-
"""WhatsApp Production Strategy Phase 5 — connection & readiness architecture."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from extensions import db
from models import Store
from services.admin_whatsapp_visibility_v1 import build_admin_whatsapp_store_row
from services.merchant_whatsapp_connection_readiness_v1 import (
    CANONICAL_CONNECTION_STATES,
    CONNECTION_STATE_CONNECTED,
    CONNECTION_STATE_PAUSED,
    CONNECTION_STATE_SETUP_REQUIRED,
    READINESS_OVERALL_NOT_READY,
    READINESS_OVERALL_READY,
    connection_journey_for_mode,
    evaluate_whatsapp_connection_readiness,
    meta_future_placeholders_for_api,
)
from services.merchant_whatsapp_mode_v1 import WHATSAPP_MODE_CARTFLOW_MANAGED
from services.merchant_whatsapp_readiness_ui import build_merchant_whatsapp_readiness_card


def _flags(**kwargs: bool) -> dict[str, bool]:
    base = {
        "dashboard_ready": True,
        "store_connected": True,
        "whatsapp_configured": True,
        "provider_ready": True,
        "recovery_enabled": True,
        "widget_installed": True,
        "test_recovery_possible": True,
        "sandbox_mode_active": False,
    }
    base.update(kwargs)
    return base


def _ob(flags: dict[str, bool], blocking: list[str]) -> dict:
    return {"flags": flags, "blocking_steps": blocking, "ready": not blocking}


class MerchantWhatsappConnectionReadinessV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_conn_{uuid.uuid4().hex[:12]}"
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()
        self.row = Store(
            zid_store_id=self.zid,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            whatsapp_recovery_enabled=True,
            store_whatsapp_number="+966501234567",
        )
        db.session.add(self.row)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()

    def test_canonical_connection_states(self) -> None:
        self.assertEqual(len(CANONICAL_CONNECTION_STATES), 7)

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value=_ob(_flags(recovery_enabled=False), ["recovery_disabled"]),
    )
    def test_paused_when_recovery_disabled(self, _m: object) -> None:
        ev = evaluate_whatsapp_connection_readiness(self.row)
        self.assertEqual(ev["connection_state"], CONNECTION_STATE_PAUSED)
        self.assertEqual(ev["readiness_overall"], READINESS_OVERALL_NOT_READY)
        self.assertTrue(ev["production_truth"]["why_paused_ar"])

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value=_ob(
            _flags(store_connected=False, widget_installed=False),
            ["store_not_connected"],
        ),
    )
    def test_setup_required_when_store_missing(self, _m: object) -> None:
        ev = evaluate_whatsapp_connection_readiness(self.row)
        self.assertEqual(ev["connection_state"], CONNECTION_STATE_SETUP_REQUIRED)
        blob = " ".join(ev["missing_requirements_ar"] + [ev["production_truth"]["action_required_ar"]])
        self.assertIn("ربط المتجر", blob)

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value=_ob(_flags(), []),
    )
    def test_ready_when_all_green(self, _m: object) -> None:
        ev = evaluate_whatsapp_connection_readiness(self.row)
        self.assertEqual(ev["connection_state"], CONNECTION_STATE_CONNECTED)
        self.assertEqual(ev["readiness_overall"], READINESS_OVERALL_READY)
        dims = {d["key"]: d["ready"] for d in ev["readiness_dimensions"]}
        self.assertTrue(dims["store_connected"])
        self.assertTrue(dims["widget_ready"])

    def test_managed_journey_hides_meta_terms(self) -> None:
        journey = connection_journey_for_mode(WHATSAPP_MODE_CARTFLOW_MANAGED)
        hidden = " ".join(journey["hidden_from_merchant_ar"]).lower()
        self.assertIn("waba", hidden)
        self.assertIn("meta", hidden)

    def test_setup_checklist_structure(self) -> None:
        with patch(
            "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
            return_value=_ob(_flags(widget_installed=False), []),
        ):
            ev = evaluate_whatsapp_connection_readiness(self.row)
        checklist = ev["setup_checklist"]
        self.assertIn("headline_ar", checklist)
        self.assertTrue(any(not i["complete"] for i in checklist["checklist_ar"]))

    def test_meta_placeholders_hidden_by_default(self) -> None:
        self.assertEqual(meta_future_placeholders_for_api(visible=False), [])

    @patch(
        "services.merchant_whatsapp_readiness_ui.evaluate_onboarding_readiness",
        return_value=_ob(_flags(recovery_enabled=False), ["recovery_disabled"]),
    )
    def test_readiness_card_includes_phase5_fields(self, _m: object) -> None:
        card = build_merchant_whatsapp_readiness_card(self.row)
        for key in (
            "connection_state",
            "connection_state_ar",
            "whatsapp_mode_label_ar",
            "required_actions_ar",
            "expected_outcome_ar",
            "setup_checklist",
        ):
            self.assertIn(key, card, msg=f"missing {key}")

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value=_ob(_flags(), []),
    )
    def test_admin_row_includes_readiness_fields(self, _m: object) -> None:
        admin = build_admin_whatsapp_store_row(self.row)
        d = admin.to_api_dict()
        self.assertIn("readiness_state", d)
        self.assertIn("connection_state", d)
        self.assertIn("missing_requirements_ar", d)
        self.assertIn("operational_notes_ar", d)


if __name__ == "__main__":
    unittest.main()
