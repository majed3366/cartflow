# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import unittest
from unittest.mock import patch

from services.dashboard_normal_carts_perf_v1 import (
    dashboard_normal_carts_perf_add_lifecycle_ms,
    dashboard_normal_carts_perf_begin,
    dashboard_normal_carts_perf_emit,
    dashboard_normal_carts_perf_record_loads,
    dashboard_normal_carts_perf_stage,
)


class DashboardNormalCartsPerfTests(unittest.TestCase):
    def test_emit_logs_dashboard_perf_line(self) -> None:
        import time

        wall0 = time.perf_counter()
        dashboard_normal_carts_perf_begin()
        dashboard_normal_carts_perf_record_loads(
            abandoned_carts=12,
            recovery_log_rows=40,
            recovery_schedule_rows=8,
        )
        with dashboard_normal_carts_perf_stage("batch_reads"):
            pass
        dashboard_normal_carts_perf_add_lifecycle_ms(15.5)
        with self.assertLogs("cartflow", level="INFO") as captured:
            dashboard_normal_carts_perf_emit(wall_perf_start=wall0)
        joined = "\n".join(captured.output)
        self.assertIn("[DASHBOARD PERF]", joined)
        self.assertIn("total_ms=", joined)
        self.assertIn("queries=", joined)
        self.assertIn("carts=12", joined)
        self.assertIn("schedules=8", joined)
        self.assertIn("logs=40", joined)
        self.assertIn("lifecycle_ms=15.5", joined)
        self.assertIn("slow_stage=", joined)

    def test_emit_noop_when_not_begun(self) -> None:
        import time

        with patch.object(logging.getLogger("cartflow"), "info") as mock_info:
            dashboard_normal_carts_perf_emit(wall_perf_start=time.perf_counter())
        mock_info.assert_not_called()


if __name__ == "__main__":
    unittest.main()
