# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import unittest

from services import cartflow_observability_mode as obs


class CartflowObservabilityModeTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("CARTFLOW_OBSERVABILITY_MODE", None)
        os.environ.pop("CARTFLOW_DB_REQUEST_AUDIT", None)
        os.environ.pop("CARTFLOW_STRUCTURED_HEALTH_LOG", None)
        os.environ.pop("CARTFLOW_PROVIDER_READINESS_LOG", None)
        os.environ.pop("CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG", None)

    def test_default_off_audit_inactive(self) -> None:
        os.environ.pop("CARTFLOW_OBSERVABILITY_MODE", None)
        self.assertEqual(obs.observability_mode(), "off")
        self.assertFalse(obs.observability_request_sql_audit_active())

    def test_basic_enables_audit_and_section_profiles(self) -> None:
        os.environ["CARTFLOW_OBSERVABILITY_MODE"] = "basic"
        self.assertTrue(obs.observability_request_sql_audit_active())
        self.assertTrue(obs.observability_emit_dashboard_section_profile())
        self.assertFalse(obs.observability_dashboard_route_endpoint_profile_enabled())

    def test_audit_env_zero_blocks_even_in_basic(self) -> None:
        os.environ["CARTFLOW_OBSERVABILITY_MODE"] = "basic"
        os.environ["CARTFLOW_DB_REQUEST_AUDIT"] = "0"
        self.assertFalse(obs.observability_request_sql_audit_active())

    def test_debug_deep_flags(self) -> None:
        os.environ.pop("CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG", None)
        os.environ["CARTFLOW_OBSERVABILITY_MODE"] = "debug"
        self.assertTrue(obs.observability_stall_trace_enabled())
        self.assertFalse(obs.observability_peers_sql_explain_enabled())


if __name__ == "__main__":
    unittest.main()
