# -*- coding: utf-8 -*-
"""Gate 2C — Decision Portfolio & Performance Recovery."""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class PortfolioBalanceTests(unittest.TestCase):
    def test_category_cap_and_landscape(self) -> None:
        from services.decision_composition_engine_v1.portfolio_v1 import (
            build_portfolio_v1,
        )

        published = [
            {
                "decision_id": "a",
                "decision_type": "recoverability_gap",
                "merchant_decision": "recovery A",
                "priority": 90,
                "priority_band": "needs_action_now",
            },
            {
                "decision_id": "b",
                "decision_type": "recoverability_gap",
                "merchant_decision": "recovery B",
                "priority": 80,
                "priority_band": "needs_action_now",
            },
            {
                "decision_id": "c",
                "decision_type": "verified_existing_finding",
                "finding_type": "high_interest_low_purchase_product_v1",
                "merchant_decision": "product C",
                "priority": 70,
                "priority_band": "needs_action_now",
            },
            {
                "decision_id": "d",
                "decision_type": "verified_existing_finding",
                "finding_type": "whatsapp_message_timing_test_v1",
                "merchant_decision": "comms D",
                "priority": 60,
                "priority_band": "monitor",
            },
        ]
        pkg = build_portfolio_v1(published, max_visible=6)
        portfolio = pkg["portfolio"]
        cats = [d["decision_category"] for d in portfolio]
        # Recovery capped to 1 primary
        self.assertEqual(cats.count("recovery"), 1)
        self.assertIn("products", cats)
        self.assertIn("communication", cats)
        # Landscape covers all categories; healthy ones say no action
        landscape = pkg["category_landscape"]
        # Gate 2D expands categories with pricing + shipping.
        self.assertEqual(len(landscape), 9)
        healthy = [x for x in landscape if x.get("no_action_required")]
        self.assertGreaterEqual(len(healthy), 1)
        self.assertTrue(any("لا إجراء" in (x.get("status_ar") or "") for x in healthy))
        # Ranked
        self.assertEqual(portfolio[0]["portfolio_rank"], 1)

    def test_communication_cannot_alone_block_products(self) -> None:
        from services.decision_composition_engine_v1.portfolio_v1 import (
            build_portfolio_v1,
        )

        published = [
            {
                "decision_id": "comm",
                "decision_type": "verified_existing_finding",
                "finding_type": "whatsapp_message_timing_test_v1",
                "priority": 99,
                "priority_band": "needs_action_now",
                "merchant_decision": "comms",
            },
            {
                "decision_id": "prod",
                "decision_type": "verified_existing_finding",
                "finding_type": "high_interest_low_purchase_product_v1",
                "priority": 40,
                "priority_band": "monitor",
                "merchant_decision": "product",
            },
        ]
        pkg = build_portfolio_v1(published)
        ids = [d["decision_id"] for d in pkg["portfolio"]]
        self.assertIn("comm", ids)
        self.assertIn("prod", ids)


class SnapshotCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["CARTFLOW_DCE_TEST_CACHE"] = "1"
        from services.decision_composition_engine_v1.snapshot_cache_v1 import (
            cache_clear,
        )

        cache_clear()

    def tearDown(self) -> None:
        os.environ.pop("CARTFLOW_DCE_TEST_CACHE", None)
        from services.decision_composition_engine_v1.snapshot_cache_v1 import (
            cache_clear,
        )

        cache_clear()

    def test_second_call_is_cache_hit(self) -> None:
        from services.decision_composition_engine_v1.compose_v1 import (
            compose_decisions_v1,
        )

        calls = {"n": 0}

        def fake_counters(slug: str):
            calls["n"] += 1
            return {
                "store_slug": slug,
                "available": True,
                "no_phone_total": 5,
                "waiting_total": 5,
                "engaged_total": 0,
                "active_total": 5,
            }

        with patch(
            "services.decision_composition_engine_v1.compose_v1.load_store_counter_inputs_v1",
            side_effect=fake_counters,
        ), patch(
            "services.decision_composition_engine_v1.compose_v1.load_bound_finding_inputs_v1",
            return_value=[],
        ):
            a = compose_decisions_v1("store-x", use_cache=True)
            b = compose_decisions_v1("store-x", use_cache=True)
        self.assertEqual(calls["n"], 1)
        self.assertTrue((b.get("_cache") or {}).get("hit"))
        self.assertEqual(a["counts"]["published"], b["counts"]["published"])

    def test_payload_counters_skip_db_scan(self) -> None:
        from services.decision_composition_engine_v1.compose_v1 import (
            compose_decisions_v1,
        )
        from services.decision_composition_engine_v1.snapshot_cache_v1 import (
            cache_clear,
        )

        cache_clear()
        with patch(
            "services.decision_composition_engine_v1.compose_v1.load_store_counter_inputs_v1",
            side_effect=AssertionError("should not scan"),
        ), patch(
            "services.decision_composition_engine_v1.compose_v1.load_bound_finding_inputs_v1",
            return_value=[],
        ):
            pkg = compose_decisions_v1(
                "s",
                counters={
                    "store_slug": "s",
                    "available": True,
                    "no_phone_total": 43,
                    "waiting_total": 43,
                    "engaged_total": 0,
                },
                use_cache=True,
            )
        self.assertEqual((pkg.get("timing_ms") or {}).get("counters_source"), "payload")
        self.assertGreaterEqual(pkg["counts"]["published"], 1)


class TeaserPayloadTests(unittest.TestCase):
    def test_teaser_uses_summary_counters(self) -> None:
        from services.decision_composition_engine_v1.teaser_v1 import (
            count_composed_decisions_for_teaser_v1,
        )
        from services.decision_composition_engine_v1.snapshot_cache_v1 import (
            cache_clear,
        )

        os.environ["CARTFLOW_DCE_TEST_CACHE"] = "1"
        cache_clear()
        summary = {
            "store_slug": "s",
            "merchant_store_cart_counts": {
                "no_phone_total": 10,
                "waiting_total": 10,
                "active_total": 10,
                "engaged_total": 0,
            },
        }
        with patch(
            "services.decision_composition_engine_v1.compose_v1.load_store_counter_inputs_v1",
            side_effect=AssertionError("no scan"),
        ), patch(
            "services.decision_composition_engine_v1.compose_v1.load_bound_finding_inputs_v1",
            return_value=[],
        ):
            teaser = count_composed_decisions_for_teaser_v1("s", summary=summary)
        self.assertGreaterEqual(teaser["count"], 1)
        self.assertTrue(teaser.get("category_landscape"))
        os.environ.pop("CARTFLOW_DCE_TEST_CACHE", None)
        cache_clear()


class UiContractTests(unittest.TestCase):
    def test_portfolio_ui_markers(self) -> None:
        grid = (ROOT / "static" / "cart_workspace_grid_v1.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("data-gate2c", grid)
        self.assertIn("محفظة القرارات", grid)
        self.assertIn("cw-landscape", grid)
        card = (ROOT / "static" / "cart_workspace_decision_card_v1.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("الأولوية", card)
        self.assertIn("portfolio_rank", card)


if __name__ == "__main__":
    unittest.main()
