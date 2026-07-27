# -*- coding: utf-8 -*-
"""Home Performance Hardening V1 — timeline + stale-snapshot composition path."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from services.home_performance_hardening_v1.timeline_v1 import (
    home_perf_begin,
    home_perf_end,
    home_perf_enabled,
    home_perf_stage,
)
from services.merchant_home_experience_activation_v1 import (
    TRANSPORT_DEGRADED,
    TRANSPORT_SNAPSHOT,
    finalize_dashboard_summary_payload,
)


def _ready_hes() -> dict:
    return {
        "ok": True,
        "sections": [
            {"id": "health", "diagnosis_ar": "x", "recommendation_ar": "y"},
        ],
        "diagnostic_reasoning": "diagnostic_reasoning_v1",
    }


class HomePerfTimelineTests(unittest.TestCase):
    def test_timeline_records_stages_and_pct(self) -> None:
        home_perf_begin(label="unit")
        self.assertTrue(home_perf_enabled())
        with home_perf_stage("alpha"):
            pass
        with home_perf_stage("beta"):
            pass
        report = home_perf_end()
        self.assertTrue(report["ok"])
        self.assertEqual(report["stage_count"], 2)
        self.assertEqual(report["stages"][0]["stage"], "alpha")
        self.assertIn("pct_of_total", report["stages"][0])
        self.assertFalse(home_perf_enabled())


class StaleSnapshotCompositionTests(unittest.TestCase):
    def test_degraded_miss_no_longer_runs_orv_on_home(self) -> None:
        """Prod-proven: snapshot/degraded Home must not run ORV (~3.3s)."""
        body = {
            "ok": True,
            "store_slug": "demo",
            "snapshot_degraded": True,
            "snapshot_reason": "no_snapshot",
            "home_executive_summary_v1": {"ok": True, "sections": []},
            "diagnostic_publication_v1": {
                "diagnosis_status": "insufficient_evidence",
                "diagnosis_ar": "x",
                "recommendation_ar": "y",
            },
        }
        called = {"orv": 0}

        def _orv(summary, slug):  # noqa: ANN001
            called["orv"] += 1

        with patch(
            "services.observation_foundation_v1.merchant_findings_v1."
            "attach_observation_reality_validation_to_summary_v1",
            side_effect=_orv,
        ):
            with patch(
                "services.diagnostic_reasoning_v1.attach_diagnostic_publication_from_snapshots_v1",
                side_effect=lambda s, store_slug="": s,
            ):
                out = finalize_dashboard_summary_payload(
                    body,
                    summary_source=TRANSPORT_DEGRADED,
                    store_slug="demo",
                )
        self.assertEqual(called["orv"], 0)
        self.assertEqual(
            (out.get("home_executive_summary_v1") or {}).get("diagnostic_reasoning"),
            "diagnostic_reasoning_v1",
        )

    def test_snapshot_transport_passthrough_skips_orv(self) -> None:
        """AFTER path: TRANSPORT_SNAPSHOT + ready HES must not admit ORV."""
        body = {
            "ok": True,
            "store_slug": "demo",
            "snapshot_stale": True,
            "snapshot_degraded": True,  # freshness flag only
            "home_executive_summary_v1": _ready_hes(),
            "diagnostic_publication_v1": {
                "diagnosis_status": "insufficient_evidence",
            },
        }
        called = {"orv": 0}

        def _orv(summary, slug):  # noqa: ANN001
            called["orv"] += 1

        with patch(
            "services.observation_foundation_v1.merchant_findings_v1."
            "attach_observation_reality_validation_to_summary_v1",
            side_effect=_orv,
        ):
            with patch(
                "services.diagnostic_reasoning_v1.attach_diagnostic_publication_from_snapshots_v1",
                side_effect=lambda s, store_slug="": s,
            ):
                out = finalize_dashboard_summary_payload(
                    body,
                    summary_source=TRANSPORT_SNAPSHOT,
                    store_slug="demo",
                )
        self.assertEqual(called["orv"], 0)
        self.assertEqual(out.get("home_surface_mode"), "executive_summary_v1")

    def test_persisted_row_selects_snapshot_source_even_when_stale(self) -> None:
        from contextlib import nullcontext

        from services.dashboard_snapshot_read_v1 import build_summary_from_snapshot

        stale_body = {
            "ok": True,
            "store_slug": "demo",
            "snapshot_mode": True,
            "snapshot_stale": True,
            "snapshot_degraded": True,
            "snapshot_reason": "stale_snapshot",
            "home_executive_summary_v1": _ready_hes(),
            "_snapshot": {
                "generated_at": "2026-07-27T00:00:00",
                "version": 12,
                "stale": True,
                "degraded": True,
                "read_ms": 2.0,
            },
        }
        sources: list[str] = []

        def _finalize(body, *, summary_source, store_slug=""):  # noqa: ANN001
            sources.append(summary_source)
            return body

        with patch(
            "services.dashboard_snapshot_read_v1.read_dashboard_snapshot_payload",
            return_value=dict(stale_body),
        ):
            with patch(
                "services.merchant_home_experience_activation_v1.finalize_dashboard_summary_payload",
                side_effect=_finalize,
            ):
                with patch(
                    "services.dashboard_snapshot_read_v1.enforce_route_budget",
                    side_effect=lambda body, wall0=0, endpoint="": body,
                ):
                    with patch(
                        "services.dashboard_snapshot_read_v1.dashboard_api_snapshot_request_scope",
                        return_value=nullcontext(),
                    ):
                        build_summary_from_snapshot(store_slug="demo")
        self.assertEqual(sources, [TRANSPORT_SNAPSHOT])

if __name__ == "__main__":
    unittest.main()
