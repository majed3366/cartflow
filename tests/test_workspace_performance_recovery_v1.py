# -*- coding: utf-8 -*-
"""Gate 0 — Workspace Performance Recovery: no request-path ORV when package reusable."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class PackageReuseTests(unittest.TestCase):
    def test_enrich_reuses_dce_situations_without_orv_rebuild(self) -> None:
        from services.cart_workspace.business_findings_enrichment_v1 import (
            enrich_projection_with_fde_v1,
        )

        cs_pkg = {
            "ok": True,
            "counts": {"published": 1},
            "published_situations": [
                {
                    "situation_id": "sit:1",
                    "decision_id": "sit:1",
                    "title_ar": "منتج يحتاج قرار",
                    "title": "منتج يحتاج قرار",
                    "merchant_decision": "راجع التسعير",
                    "why": "why",
                    "why_now": "now",
                    "evidence": "ev",
                    "priority": 70,
                    "confidence": "high",
                    "product_name_ar": "منتج",
                }
            ],
        }
        fake_pkg = {
            "ok": True,
            "composition_version": "decision_composition_engine_v1",
            "decisions": [],
            "portfolio": [],
            "needs_action_now": [],
            "monitor": [],
            "suppression_registry": [],
            "counts": {"published": 0, "candidates_total": 0},
            "business_facts_v1": {"ok": True, "counts": {"facts": 1}, "facts": []},
            "commerce_situations_v1": cs_pkg,
            "merchant_publication_v1": {
                "ok": True,
                "highest_priority_decision_id": "sit:1",
                "primary_action": "راجع التسعير",
                "primary_subject": "منتج",
            },
            "_cache": {"hit": True, "fresh": True},
        }

        orv_mock = MagicMock(side_effect=AssertionError("ORV must not rebuild"))
        facts_mock = MagicMock(side_effect=AssertionError("facts must not rebuild"))
        situ_build_mock = MagicMock(
            side_effect=AssertionError("situations must not rebuild")
        )

        with patch(
            "services.decision_composition_engine_v1.flag_v1.decision_composition_engine_v1_enabled",
            return_value=True,
        ), patch(
            "services.decision_composition_engine_v1.compose_v1.compose_decisions_v1",
            return_value=fake_pkg,
        ), patch(
            "services.business_facts_v1.business_facts_v1_enabled",
            return_value=True,
        ), patch(
            "services.commerce_situations_v1.commerce_situations_v1_enabled",
            return_value=True,
        ), patch(
            "services.commerce_situations_v1.workspace_cards_from_commerce_situations_v1",
            return_value=[
                {
                    "decision_id": "sit:1",
                    "title": "منتج يحتاج قرار",
                    "merchant_decision": "راجع التسعير",
                    "situation_id": "sit:1",
                    "priority": 70,
                    "confidence": "high",
                    "product_name_ar": "منتج",
                }
            ],
        ), patch(
            "services.observation_foundation_v1.merchant_findings_v1.build_observation_reality_validation_v1",
            orv_mock,
        ), patch(
            "services.business_facts_v1.build_business_facts_package_v1",
            facts_mock,
        ), patch(
            "services.commerce_situations_v1.build_commerce_situations_package_v1",
            situ_build_mock,
        ), patch(
            "services.decision_workspace_v2.flag_v1.decision_workspace_v2_enabled",
            return_value=False,
        ):
            out = enrich_projection_with_fde_v1(
                {"zone_a": [], "zone_b": [], "zone_labels": {}}, "demo"
            )

        self.assertTrue(out.get("gate_2b_decision_composition_engine"))
        self.assertGreaterEqual(len(out.get("zone_b") or []), 1)
        orv_mock.assert_not_called()
        facts_mock.assert_not_called()
        situ_build_mock.assert_not_called()


class SnapshotServeTests(unittest.TestCase):
    def test_read_miss_on_invalidated(self) -> None:
        from services.decision_workspace_v2.snapshot_serve_v1 import (
            read_decision_workspace_snapshot_v1,
        )

        row = MagicMock()
        row.version = 3
        with patch(
            "services.dashboard_snapshot_v1.canonical_snapshot_store_slug",
            return_value="demo",
        ), patch(
            "services.dashboard_snapshot_v1.fetch_latest_snapshot_row",
            return_value=row,
        ), patch(
            "services.dashboard_snapshot_v1.decode_snapshot_payload",
            return_value={"invalidated": True, "projection": {"zone_b": []}},
        ):
            self.assertIsNone(read_decision_workspace_snapshot_v1("demo"))

    def test_read_hit_returns_projection(self) -> None:
        from services.decision_workspace_v2.snapshot_serve_v1 import (
            read_decision_workspace_snapshot_v1,
        )

        row = MagicMock()
        row.version = 2
        with patch(
            "services.dashboard_snapshot_v1.canonical_snapshot_store_slug",
            return_value="demo",
        ), patch(
            "services.dashboard_snapshot_v1.fetch_latest_snapshot_row",
            return_value=row,
        ), patch(
            "services.dashboard_snapshot_v1.decode_snapshot_payload",
            return_value={
                "ok": True,
                "invalidated": False,
                "projection": {
                    "zone_a": [],
                    "zone_b": [{"decision_id": "d1"}],
                    "quiet": False,
                },
            },
        ), patch(
            "services.dashboard_snapshot_v1.snapshot_row_is_stale",
            return_value=False,
        ):
            out = read_decision_workspace_snapshot_v1("demo")
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out["zone_b"][0]["decision_id"], "d1")
        self.assertTrue(out["_workspace_snapshot_v1"]["hit"])


class PerfTimelineTests(unittest.TestCase):
    def test_timeline_pct_and_stages(self) -> None:
        from services.decision_workspace_v2.perf_timeline_v1 import (
            workspace_perf_begin,
            workspace_perf_end,
            workspace_perf_meta,
            workspace_perf_stage,
        )

        workspace_perf_begin(label="t")
        with workspace_perf_stage("a"):
            pass
        with workspace_perf_stage("b", cache="hit"):
            pass
        workspace_perf_meta(package_reuse=True)
        report = workspace_perf_end()
        self.assertTrue(report["ok"])
        self.assertEqual(report["stage_count"], 2)
        self.assertIn("pct_of_total", report["stages"][0])
        self.assertTrue(report["meta"].get("package_reuse"))


if __name__ == "__main__":
    unittest.main()
