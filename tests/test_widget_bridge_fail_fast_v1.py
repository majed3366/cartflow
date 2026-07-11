# -*- coding: utf-8 -*-
"""Widget Fast Path V1 — bridge ensure fail-fast (no await on reason path)."""
from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CORE = (
    _ROOT / "static/cartflow_widget_runtime/cartflow_storefront_cart_bridge_core.js"
).read_text(encoding="utf-8")
_FLOWS = (_ROOT / "static/cartflow_widget_runtime/cartflow_widget_flows.js").read_text(
    encoding="utf-8"
)
_LOADER = (_ROOT / "static/widget_loader.js").read_text(encoding="utf-8")


class WidgetBridgeFailFastV1Tests(unittest.TestCase):
    def test_ensure_does_not_await_read_and_persist(self) -> None:
        idx = _CORE.index("function ensureCartTruthBeforeReason")
        # Bound to this function only — later hooks still use allowFreshAfterInFlight.
        next_fn = _CORE.index("\n  function ", idx + 1)
        block = _CORE[idx:next_fn]
        self.assertIn("[CF BRIDGE ENSURE FAIL FAST]", block)
        self.assertIn("stable_identity_no_wait", block)
        self.assertIn("session_only_no_wait", block)
        self.assertIn("missing_identity", block)
        self.assertIn("already_persisted", block)
        self.assertIn("ensure_before_reason_bg", _CORE)
        self.assertIn("scheduleBackgroundPersistAfterReason", _CORE)
        self.assertIn("defer_cart_persist", _CORE)
        # Must not call awaited readAndPersist on the reason critical path
        self.assertNotIn("allowFreshAfterInFlight: true", block)
        self.assertNotIn('source_hint: "ensure_before_reason"', block)
        self.assertNotIn("return readAndPersist(", block)
        # Must not race cart-event with reason POST (scheduled after reason OK in flows)
        self.assertNotIn("scheduleBackgroundPersistAfterReason()", block)

    def test_ensure_before_reason_not_priority_wait(self) -> None:
        # Priority wait list must not include ensure_before_reason (was the wait trigger)
        pri = _CORE[
            _CORE.index("function isPriorityAddTrigger") : _CORE.index(
                "function logRetryStop"
            )
        ]
        self.assertNotIn("ensure_before_reason", pri)

    def test_flows_fail_fast_missing_identity(self) -> None:
        self.assertIn('fail_fast_path === "missing_identity"', _FLOWS)
        self.assertIn("ensureCartTruthBeforeReason", _FLOWS)
        # Persist-then-advance preserved
        self.assertIn("persistThenAdvance(res)", _FLOWS)
        self.assertIn("Cf.Api.postReason(payloadCopy)", _FLOWS)

    def test_flows_schedules_cart_persist_after_reason_ok(self) -> None:
        self.assertIn("defer_cart_persist", _FLOWS)
        self.assertIn("scheduleBackgroundPersistAfterReason()", _FLOWS)

    def test_runtime_version(self) -> None:
        # Superseded by reason-post-detach runtime; keep fail-fast markers in core.
        self.assertIn("v2-widget-", _LOADER)


if __name__ == "__main__":
    unittest.main()
