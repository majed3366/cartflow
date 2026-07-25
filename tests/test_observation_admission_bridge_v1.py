# -*- coding: utf-8 -*-
"""Observation Admission Bridge V1 — no silent rejection; entity-bound admit."""
from __future__ import annotations

import unittest

from services.observation_foundation_v1.admission_bridge_v1 import (
    admit_observation_candidates_v1,
)
from services.observation_foundation_v1.product_entity_resolve_v1 import (
    is_banned_product_key_v1,
    parse_identity_key_segments_v1,
    resolve_real_product_display_name_v1,
)


class ObservationAdmissionBridgeV1Tests(unittest.TestCase):
    def test_composite_key_segments(self) -> None:
        segs = parse_identity_key_segments_v1("b|demo_watch_band|demo-watch-band")
        self.assertIn("demo_watch_band", segs)
        self.assertIn("demo-watch-band", segs)

    def test_does_not_ban_composite_identity_keys(self) -> None:
        self.assertFalse(
            is_banned_product_key_v1("b|demo_watch_band|demo-watch-band")
        )
        self.assertTrue(is_banned_product_key_v1("DEMO-PERFUME"))
        self.assertTrue(is_banned_product_key_v1("demo"))
        self.assertTrue(is_banned_product_key_v1("orv-s1"))

    def test_admits_when_resolver_returns_real_name(self) -> None:
        pkg = {
            "store_slug": "demo",
            "counts": {"correlations": 1, "statement_capabilities_ready": 1},
            "correlations": [
                {
                    "statement_capability": "shipping_stronger_than_price",
                    "product_key": "b|demo_hp_air|demo-hp-air",
                    "correlation_kind": "reason_strength_compare_v1",
                    "compare": {"shipping": 6, "price": 3},
                    "reason_counts": {"shipping": 5, "price": 2},
                    "evidence_refs": [{"id": 1}, {"id": 2}, {"id": 3}],
                    "counts": {"cart_add": 4, "purchase": 1},
                }
            ],
        }
        out = admit_observation_candidates_v1(
            pkg,
            store_slug="demo",
            product_name_resolver=lambda s, k: "TrueSound Air — سماعة خفيفة",
        )
        self.assertEqual(out["orv_admitted_count"], 1)
        self.assertEqual(out["home_visible_count"], 1)
        self.assertEqual(out["workspace_visible_count"], 1)
        self.assertEqual(out["reconciliation"]["silent_drops"], 0)
        f = out["admitted"][0]
        self.assertEqual(f["product_name_ar"], "TrueSound Air — سماعة خفيفة")
        self.assertIn("شحن", f["statement_ar"])

    def test_suppresses_unresolved_identity_with_reason(self) -> None:
        pkg = {
            "correlations": [
                {
                    "statement_capability": "high_interest_low_conversion",
                    "product_key": "b|missing|sku-x",
                    "correlation_kind": "product_interest_conversion_v1",
                    "counts": {"cart_add": 5, "purchase": 0},
                    "evidence_refs": [{"id": 1}],
                }
            ]
        }
        out = admit_observation_candidates_v1(
            pkg,
            store_slug="demo",
            product_name_resolver=lambda s, k: None,
        )
        self.assertEqual(out["orv_admitted_count"], 0)
        self.assertGreaterEqual(out["suppressed_count"], 1)
        reasons = {r["rejection_reason"] for r in out["suppressed"]}
        self.assertIn("product_display_name_unresolved", reasons)

    def test_no_quality_home_only_not_workspace(self) -> None:
        pkg = {
            "correlations": [
                {
                    "statement_capability": "no_quality_issue_evidence",
                    "product_key": "sku:alpha",
                    "correlation_kind": "absent_reason_evidence_v1",
                    "absent_family": "quality",
                    "evidence_refs": [{"id": 1}, {"id": 2}],
                    "counts": {"cart_add": 3},
                }
            ]
        }
        out = admit_observation_candidates_v1(
            pkg,
            store_slug="demo",
            product_name_resolver=lambda s, k: "عطر الورد الملكي",
        )
        self.assertEqual(out["home_visible_count"], 1)
        self.assertEqual(out["workspace_visible_count"], 0)
        reasons = {r["rejection_reason"] for r in out["suppressed"]}
        self.assertIn("observation_valid_for_home_not_workspace", reasons)

    def test_banned_perfume_never_admits(self) -> None:
        pkg = {
            "correlations": [
                {
                    "statement_capability": "high_interest_low_conversion",
                    "product_key": "DEMO-PERFUME",
                    "counts": {"cart_add": 9, "purchase": 0},
                    "evidence_refs": [{"id": i} for i in range(5)],
                }
            ]
        }
        out = admit_observation_candidates_v1(
            pkg,
            store_slug="demo",
            product_name_resolver=lambda s, k: "should-not-use",
        )
        # Resolver may return a name, but hard ban stage rejects DEMO-PERFUME.
        # If banned at identity stage before resolver — admitted 0.
        self.assertEqual(out["orv_admitted_count"], 0)


if __name__ == "__main__":
    unittest.main()
