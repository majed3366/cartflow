# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import unittest

from services.dashboard_summary_json_safe_v1 import (
    finite_dashboard_float,
    preflight_utf8_json_payload,
    sanitize_dashboard_summary_payload,
)


class DashboardSummaryJsonSafeTests(unittest.TestCase):
    def test_finite_dashboard_float_coerces_nan(self) -> None:
        self.assertEqual(finite_dashboard_float(float("nan")), 0.0)
        self.assertEqual(finite_dashboard_float(float("inf")), 0.0)
        self.assertEqual(finite_dashboard_float("12.5"), 12.5)

    def test_sanitize_dashboard_summary_payload_makes_json_safe(self) -> None:
        payload = {
            "merchant_kpi_recovered_pct_vs_abandoned": float("nan"),
            "merchant_reason_rows_week": [
                {"count_pct": float("nan"), "label_ar": "test"}
            ],
        }
        clean = sanitize_dashboard_summary_payload(payload)
        preflight_utf8_json_payload(clean)
        self.assertEqual(clean["merchant_kpi_recovered_pct_vs_abandoned"], 0.0)
        self.assertEqual(clean["merchant_reason_rows_week"][0]["count_pct"], 0.0)
        json.dumps(clean, ensure_ascii=False, allow_nan=False)

    def test_sanitize_preserves_bool_none_and_zero(self) -> None:
        """Regression: singleton identity must not fall through to str()."""
        payload = {
            "ok": True,
            "empty": False,
            "count": 0,
            "cdc_phase": None,
            "nested": {"empty": False, "primary": {"family": "shipping_friction"}},
        }
        clean = sanitize_dashboard_summary_payload(payload)
        self.assertIs(clean["ok"], True)
        self.assertIs(clean["empty"], False)
        self.assertEqual(clean["count"], 0)
        self.assertIsNone(clean["cdc_phase"])
        self.assertIs(clean["nested"]["empty"], False)
        raw = json.dumps(clean, ensure_ascii=False, allow_nan=False)
        self.assertIn('"empty": false', raw)
        self.assertIn('"ok": true', raw)
        self.assertIn('"cdc_phase": null', raw)
        self.assertNotIn('"False"', raw)
        self.assertNotIn('"None"', raw)


if __name__ == "__main__":
    unittest.main()
