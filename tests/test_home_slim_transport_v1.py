# -*- coding: utf-8 -*-
"""Gate 1 — Home Slim Transport V1."""
from __future__ import annotations

import unittest

from services.home_executive_summary_v1.compose_v1 import (
    OBS_EMPTY_AR,
    attach_home_executive_summary_to_summary_v1,
    build_home_executive_summary_v1,
)
from services.home_executive_summary_v1.slim_transport_v1 import (
    extract_home_teaser_inputs_v1,
    home_slim_transport_v1_enabled,
    strip_heavy_home_summary_payload_v1,
)
from services.merchant_home_experience_activation_v1 import (
    finalize_dashboard_summary_payload,
)


class HomeSlimTransportV1Tests(unittest.TestCase):
    def test_slim_flag_default_on(self) -> None:
        self.assertTrue(home_slim_transport_v1_enabled(environ={}))
        self.assertFalse(
            home_slim_transport_v1_enabled(
                environ={"CARTFLOW_HOME_SLIM_TRANSPORT_V1": "0"}
            )
        )

    def test_teasers_from_kpi_fields(self) -> None:
        t = extract_home_teaser_inputs_v1(
            {
                "merchant_nav_badge_abandoned": 4,
                "merchant_kpi_wa_sent_fmt": "2",
            }
        )
        self.assertEqual(t["carts"]["count"], 4)
        self.assertTrue(t["health"]["watching"])
        self.assertEqual(t["communication"]["sent"], 2)

    def test_hes_from_teasers_obs_links_workspace(self) -> None:
        summary = {
            "home_teaser_inputs_v1": {
                "schema": "home_teaser_inputs_v1",
                "health": {"watching": True, "abandoned_carts": 2},
                "decisions": {"count": 1, "top_title_ar": "راجع سلة"},
                "observations": {
                    "count": 1,
                    "top": {
                        "product_name_ar": "زيت الورد",
                        "statement_ar": "اهتمام مرتفع.",
                    },
                },
                "carts": {"count": 2},
                "communication": {"sent": 1, "schedules": 0, "activity": True},
            }
        }
        hes = build_home_executive_summary_v1(
            summary, environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"}
        )
        obs = next(s for s in hes["sections"] if s["id"] == "observations")
        self.assertEqual(obs["view_details_href"], "#workspace")
        self.assertEqual(obs["findings_preview"], [])
        self.assertIn("زيت الورد", obs["summary_ar"])

    def test_finalize_slim_strips_heavy_packages(self) -> None:
        body = {
            "ok": True,
            "merchant_nav_badge_abandoned": 3,
            "merchant_kpi_wa_sent_fmt": "1",
            "merchant_experience_integration_v1": {
                "ok": True,
                "pages": {"home": {"sections": {"merchant_decisions": [{"title_ar": "X"}]}}},
            },
            "observation_reality_validation_v1": {
                "ok": True,
                "findings": [
                    {
                        "product_name_ar": "A",
                        "statement_ar": "B",
                        "recommended_action_ar": "C",
                    }
                ],
            },
            "merchant_daily_brief_v1": {"ok": True},
            "merchant_pulse_v1": {"ok": True},
        }
        out = finalize_dashboard_summary_payload(
            body,
            summary_source="live",
            store_slug="store-a",
        )
        self.assertTrue(out.get("home_slim_transport_v1"))
        self.assertNotIn("merchant_experience_integration_v1", out)
        self.assertNotIn("merchant_daily_brief_v1", out)
        self.assertNotIn("merchant_pulse_v1", out)
        hes = out["home_executive_summary_v1"]
        self.assertTrue(hes["ok"])
        self.assertEqual(out["home_surface_mode"], "executive_summary_v1")
        obs = next(s for s in hes["sections"] if s["id"] == "observations")
        # Teasers extracted before strip — count may be 1; no action preview.
        self.assertEqual(obs["findings_preview"], [])
        self.assertEqual(obs["view_details_href"], "#workspace")

    def test_strip_helper(self) -> None:
        d = {
            "merchant_experience_integration_v1": {"ok": True},
            "merchant_home_experience_v1": {
                "ok": True,
                "store_slug": "s",
                "daily_brief_v1": {"x": 1},
            },
        }
        strip_heavy_home_summary_payload_v1(d)
        self.assertNotIn("merchant_experience_integration_v1", d)
        self.assertTrue(d["merchant_home_experience_v1"]["slim_transport"])

    def test_empty_obs_copy(self) -> None:
        hes = build_home_executive_summary_v1(
            {"home_teaser_inputs_v1": {"schema": "home_teaser_inputs_v1", "observations": {"count": 0}}},
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        obs = next(s for s in hes["sections"] if s["id"] == "observations")
        self.assertEqual(obs["summary_ar"], OBS_EMPTY_AR)


if __name__ == "__main__":
    unittest.main()
