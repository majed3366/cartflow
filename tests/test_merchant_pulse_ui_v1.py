# -*- coding: utf-8 -*-
"""Merchant Pulse V1 frontend rendering — flag, fallback, leave/enter_work CTA."""
from __future__ import annotations

import os
import re
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parent.parent
_JS = (_ROOT / "static" / "merchant_pulse_v1.js").read_text(encoding="utf-8")
_LAZY = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_TMPL = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_CSS = (_ROOT / "static" / "merchant_pulse_v1.css").read_text(encoding="utf-8")


def _slot(status: str, message: str, confidence: str = "medium") -> dict:
    return {
        "status": status,
        "message": message,
        "confidence": confidence,
        "last_updated": "2026-07-10T00:00:00+00:00",
    }


def _valid_pulse(*, fork: str = "leave", status: str = "healthy") -> dict:
    return {
        "ok": True,
        "projection": "MerchantPulseV1",
        "fork": fork,
        "status": status,
        "executive_brief": _slot("healthy", "المتجر هادئ"),
        "decision_summary": _slot("no_action", "لا شيء يحتاجك"),
        "cartflow_progress": _slot("no_action", "لا إنجازات بعد"),
        "merchant_decision": _slot(
            "require_action" if fork == "enter_work" else "no_action",
            "احصل على رقم العميل" if fork == "enter_work" else "لا قرار مطلوب",
        ),
    }


class MerchantPulseUiFlagTests(unittest.TestCase):
    def test_default_off(self) -> None:
        from services.merchant_pulse_ui_v1_flag import merchant_pulse_ui_v1_enabled

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CARTFLOW_MERCHANT_PULSE_UI_V1", None)
            self.assertFalse(merchant_pulse_ui_v1_enabled())

    def test_flag_on(self) -> None:
        from services.merchant_pulse_ui_v1_flag import merchant_pulse_ui_v1_enabled

        with mock.patch.dict(os.environ, {"CARTFLOW_MERCHANT_PULSE_UI_V1": "1"}):
            self.assertTrue(merchant_pulse_ui_v1_enabled())


class MerchantPulseJsContractTests(unittest.TestCase):
    def test_js_has_no_fetch(self) -> None:
        self.assertNotIn("fetch(", _JS)

    def test_js_binds_only_projection_fields(self) -> None:
        for key in (
            "executive_brief",
            "decision_summary",
            "cartflow_progress",
            "merchant_decision",
            "fork",
        ):
            self.assertIn(key, _JS)

    def test_leave_has_no_cta_markup_path(self) -> None:
        self.assertIn('pulse.fork !== "enter_work"', _JS)
        self.assertIn("ma-pulse-enter-work-btn", _JS)
        self.assertIn('goTo("carts")', _JS)

    def test_lazy_failsafe_to_home(self) -> None:
        self.assertIn("maApplyMerchantPulseV1", _LAZY)
        self.assertIn("maApplyHomeExperience", _LAZY)
        self.assertIn("pulseRendered", _LAZY)
        self.assertRegex(
            _LAZY,
            re.compile(r"if\s*\(\s*!pulseRendered\s*&&\s*window\.maApplyHomeExperience\s*\)"),
        )

    def test_template_flag_and_assets(self) -> None:
        self.assertIn("data-merchant-pulse-ui-v1", _TMPL)
        self.assertIn("merchant_pulse_v1.js", _TMPL)
        self.assertIn("merchant_pulse_v1.css", _TMPL)
        self.assertIn("merchant_pulse_ui_v1", _TMPL)

    def test_css_status_classes(self) -> None:
        for cls in (
            "ma-pulse-slot--loading",
            "ma-pulse-slot--healthy",
            "ma-pulse-slot--no_action",
            "ma-pulse-slot--unknown",
            "ma-pulse-slot--require_action",
        ):
            self.assertIn(cls, _CSS)

    def test_validity_helper_exported(self) -> None:
        self.assertIn("maMerchantPulseV1IsValid", _JS)
        self.assertIn("isValidPulse", _JS)


class MerchantPulsePayloadShapeTests(unittest.TestCase):
    """Mirror JS validity rules in Python for leave / enter_work / invalid."""

    def _valid(self, pulse: dict | None) -> bool:
        if not isinstance(pulse, dict) or pulse.get("ok") is False:
            return False
        if pulse.get("fork") not in ("leave", "enter_work"):
            return False
        for key in (
            "executive_brief",
            "decision_summary",
            "cartflow_progress",
            "merchant_decision",
        ):
            slot = pulse.get(key)
            if not isinstance(slot, dict):
                return False
            if not isinstance(slot.get("message"), str):
                return False
            if not isinstance(slot.get("status"), str):
                return False
        return True

    def test_leave_payload_valid(self) -> None:
        p = _valid_pulse(fork="leave")
        self.assertTrue(self._valid(p))
        self.assertEqual(p["fork"], "leave")

    def test_enter_work_payload_valid(self) -> None:
        p = _valid_pulse(fork="enter_work")
        self.assertTrue(self._valid(p))
        self.assertEqual(p["fork"], "enter_work")

    def test_missing_projection_invalid(self) -> None:
        self.assertFalse(self._valid(None))
        self.assertFalse(self._valid({}))

    def test_unknown_slot_still_valid_shape(self) -> None:
        p = _valid_pulse(fork="leave", status="unknown")
        p["executive_brief"] = _slot("unknown", "غير معروف بعد — لن نخترع عملاً")
        p["decision_summary"] = _slot("unknown", "غير معروف بعد — لن نخترع عملاً")
        self.assertTrue(self._valid(p))

    def test_duplicate_cta_not_in_markup_contract(self) -> None:
        # Only one CTA id exists in the renderer source.
        self.assertEqual(_JS.count("ma-pulse-enter-work-btn"), 2)  # id + getElementById


if __name__ == "__main__":
    unittest.main()
