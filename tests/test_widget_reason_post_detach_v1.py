# -*- coding: utf-8 -*-
"""Widget Fast Path V1.1 — reason POST detach + connection warm + phone open."""
from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_FETCH = (
    _ROOT / "static/cartflow_widget_runtime/cartflow_widget_fetch.js"
).read_text(encoding="utf-8")
_FLOWS = (_ROOT / "static/cartflow_widget_runtime/cartflow_widget_flows.js").read_text(
    encoding="utf-8"
)
_LOADER = (_ROOT / "static/widget_loader.js").read_text(encoding="utf-8")
_ROUTES = (_ROOT / "routes/cartflow.py").read_text(encoding="utf-8")
_CORS = (_ROOT / "services/cartflow_storefront_cors_v1.py").read_text(encoding="utf-8")


class WidgetReasonPostDetachV1Tests(unittest.TestCase):
    def test_arm_detached_not_background_tasks(self) -> None:
        self.assertIn("_spawn_reason_recovery_arm_detached", _ROUTES)
        self.assertIn("detached_thread", _ROUTES)
        start = _ROUTES.index("async def post_abandonment_reason")
        end = _ROUTES.index("install_cart_recovery_ready_signals_once", start)
        body = _ROUTES[start:end]
        self.assertIn("_spawn_reason_recovery_arm_detached(", body)
        self.assertNotIn("background_tasks.add_task", body)
        self.assertNotIn("background_tasks: BackgroundTasks", body)

    def test_cors_pure_asgi(self) -> None:
        self.assertIn("Pure ASGI", _CORS)
        self.assertIn("class StorefrontWidgetCorsMiddleware:", _CORS)
        self.assertNotIn(
            "class StorefrontWidgetCorsMiddleware(BaseHTTPMiddleware)", _CORS
        )

    def test_warm_and_phone_fast_path(self) -> None:
        self.assertIn("warmReasonConnection", _FETCH)
        self.assertIn("warmReasonConnection", _FLOWS)
        self.assertIn("deferAfterReasonCapture", _FLOWS)
        self.assertIn("handleThanksAfterReason(rk)", _FLOWS)

    def test_runtime(self) -> None:
        self.assertIn("v2-widget-reason-post-detach-v1-4", _LOADER)


if __name__ == "__main__":
    unittest.main()
