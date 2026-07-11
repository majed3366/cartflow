# -*- coding: utf-8 -*-
"""Carts Sprint 2.3 — real cart freshness + desktop filter wiring."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from services.dashboard_hot_slice_v1 import (
    _bump_store_counters_for_new_hot_rows,
    apply_hot_slice_to_normal_carts_payload,
)
from services.dashboard_refresh_cart_revision_v1 import (
    append_cart_revision_to_refresh_token,
    apply_live_cart_revision_to_refresh_state,
)

_ROOT = Path(__file__).resolve().parent.parent
_APP_JS = (_ROOT / "static" / "merchant_app.js").read_text(encoding="utf-8")
_LAZY = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_MI = (_ROOT / "static" / "merchant_intelligence_carts_v1.js").read_text(encoding="utf-8")
_HOT = (_ROOT / "services" / "dashboard_hot_slice_v1.py").read_text(encoding="utf-8")
_READ = (_ROOT / "services" / "dashboard_snapshot_read_v1.py").read_text(encoding="utf-8")
_BUILD = (_ROOT / "services" / "merchant_setup_render_build.py").read_text(encoding="utf-8")


class CartsSprint23FreshnessTests(unittest.TestCase):
    def test_refresh_token_appends_cart_revision(self) -> None:
        self.assertEqual(
            append_cart_revision_to_refresh_token("slug:1:2:3:4", 99),
            "slug:1:2:3:4:c99",
        )
        self.assertEqual(
            append_cart_revision_to_refresh_token("slug:1:2:3:4:c10", 11),
            "slug:1:2:3:4:c11",
        )

    def test_apply_live_cart_revision_overlays_token(self) -> None:
        with patch(
            "services.dashboard_refresh_cart_revision_v1.live_abandoned_cart_max_id",
            return_value=42,
        ):
            out = apply_live_cart_revision_to_refresh_state(
                {"merchant_dashboard_refresh_token": "s:1:2:3:4"},
                store_slug="s",
            )
        self.assertEqual(out["merchant_dashboard_refresh_token"], "s:1:2:3:4:c42")
        self.assertEqual(out["merchant_dashboard_refresh_cart_rev"], 42)

    def test_refresh_state_snapshot_path_applies_cart_revision(self) -> None:
        self.assertIn("apply_live_cart_revision_to_refresh_state", _READ)

    def test_hot_slice_bumps_counters_for_new_keys_only(self) -> None:
        payload = {
            "merchant_store_cart_counts": {
                "active_total": 29,
                "waiting_total": 5,
                "sent_total": 10,
                "engaged_total": 14,
                "completed_total": 0,
                "no_phone_total": 0,
            },
            "merchant_cart_filter_counts": {
                "all": 29,
                "waiting": 5,
                "sent": 10,
                "attention": 14,
                "recovered": 0,
                "nophone": 0,
            },
        }
        snap = [
            {
                "recovery_key": "store:a",
                "merchant_cart_visible_tabs": ["all", "attention"],
                "merchant_cart_primary_bucket": "attention",
            }
        ]
        merged = snap + [
            {
                "recovery_key": "store:new",
                "merchant_cart_visible_tabs": ["all", "waiting"],
                "merchant_cart_primary_bucket": "waiting",
            }
        ]
        _bump_store_counters_for_new_hot_rows(
            payload, snapshot_rows=snap, merged_rows=merged
        )
        self.assertEqual(payload["merchant_store_cart_counts"]["active_total"], 30)
        self.assertEqual(payload["merchant_store_cart_counts"]["waiting_total"], 6)
        self.assertEqual(payload["merchant_store_cart_counts"]["engaged_total"], 14)
        self.assertEqual(payload["merchant_cart_filter_counts"]["all"], 30)
        self.assertEqual(payload["merchant_cart_filter_counts"]["waiting"], 6)
        self.assertTrue(payload["merchant_counter_health"]["counter_hot_slice_bumped"])

    def test_hot_slice_apply_wires_counter_bump(self) -> None:
        self.assertIn("_bump_store_counters_for_new_hot_rows", _HOT)
        payload = {
            "ok": True,
            "merchant_carts_page_rows": [
                {"recovery_key": "store:a", "merchant_cart_visible_tabs": ["all"]}
            ],
            "merchant_store_cart_counts": {"active_total": 1, "waiting_total": 1},
            "merchant_cart_filter_counts": {"all": 1, "waiting": 1},
        }
        with patch(
            "services.dashboard_hot_slice_v1.dashboard_hot_slice_enabled",
            return_value=True,
        ), patch(
            "services.dashboard_hot_slice_v1.build_hot_slice_active_rows",
            return_value=(
                [
                    {
                        "recovery_key": "store:b",
                        "merchant_cart_visible_tabs": ["all", "waiting"],
                        "merchant_cart_primary_bucket": "waiting",
                    }
                ],
                {
                    "hot_slice_rows": 1,
                    "hot_slice_ms": 1.0,
                    "hot_slice_queries": 1,
                    "hot_slice_degraded": False,
                },
            ),
        ):
            out = apply_hot_slice_to_normal_carts_payload(
                payload, store_slug="store", dash_store=object()
            )
        self.assertEqual(len(out["merchant_carts_page_rows"]), 2)
        self.assertEqual(out["merchant_store_cart_counts"]["active_total"], 2)

    def test_filter_apply_uses_groups_host(self) -> None:
        self.assertIn('getElementById("ma-carts-groups-v2")', _APP_JS)
        # Must not gate maPeV2OnFilterApplied solely on legacy queue-v2.
        block_start = _APP_JS.index("function applyCartFilterMode")
        block = _APP_JS[block_start : block_start + 900]
        self.assertIn("ma-carts-groups-v2", block)
        self.assertIn("maPeV2OnFilterApplied", block)

    def test_silent_skip_plan_key_includes_row_identity(self) -> None:
        self.assertIn("rowIdSig", _LAZY)
        self.assertIn("needsYou", _LAZY)
        self.assertIn("ui-setup-v8j-lifecycle-e2e-v1", _LAZY)
        self.assertIn("ui-setup-v8j-lifecycle-e2e-v1", _BUILD)
        self.assertIn("__maCartsRowTrace", _LAZY)
        self.assertIn("__maCartsRowProbe", _LAZY)
        self.assertIn("1_api_response", _LAZY)
        self.assertIn("4_filtered_rows", _LAZY)
        self.assertIn("6_final_dom_render", _LAZY)

    def test_workspace_key_includes_row_recovery_keys(self) -> None:
        self.assertIn("rowSig", _MI)
        self.assertIn('"::" + rowSig', _MI)
        self.assertIn("String(rows.length) + \"::\" + rowSig", _MI)


if __name__ == "__main__":
    unittest.main()
