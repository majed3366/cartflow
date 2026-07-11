# -*- coding: utf-8 -*-
"""Widget Journey V2.2 — zero-friction deferred persist loading."""
from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_FLOWS = (_ROOT / "static/cartflow_widget_runtime/cartflow_widget_flows.js").read_text(
    encoding="utf-8"
)
_UI = (_ROOT / "static/cartflow_widget_runtime/cartflow_widget_ui.js").read_text(
    encoding="utf-8"
)
_LOADER = (_ROOT / "static/widget_loader.js").read_text(encoding="utf-8")


class WidgetZeroFrictionV22Tests(unittest.TestCase):
    def test_reason_loading_deferred_400ms(self) -> None:
        idx = _FLOWS.index("function openReasonPath")
        block = _FLOWS[idx : idx + 14000]
        self.assertIn("PERSIST_LOADING_THRESHOLD_MS = 400", block)
        self.assertIn("showReasonSavingSlowPath", block)
        self.assertIn("[CF REASON SAVE SLOW PATH]", block)
        self.assertIn("[CF REASON PERSIST TIMING]", block)
        # Immediate ack must not show saving copy
        ack = block[
            block.index("function acknowledgeReasonPick") : block.index(
                "function showReasonSavingSlowPath"
            )
        ]
        self.assertNotIn("جاري الحفظ", ack)
        self.assertIn('"✓ " + base', ack)
        # Saving copy only on slow path
        slow = block[
            block.index("function showReasonSavingSlowPath") : block.index(
                "function clearReasonLoadingTimer"
            )
        ]
        self.assertIn("جاري الحفظ…", slow)
        self.assertLess(
            block.index("acknowledgeReasonPick();"),
            block.index("reasonLoadingTimer = window.setTimeout"),
        )
        self.assertLess(
            block.index("Cf.Api.postReason(payloadCopy)"),
            block.index("showContinuation(rk, subCat)"),
        )

    def test_phone_loading_deferred_400ms(self) -> None:
        self.assertIn("PERSIST_LOADING_THRESHOLD_MS = 400", _UI)
        self.assertIn("[CF PHONE SAVE SLOW PATH]", _UI)
        self.assertIn("[CF PHONE PERSIST TIMING]", _UI)
        self.assertIn('save.textContent = "جاري حفظ الرقم…"', _UI)
        # Immediate click must not set saving label before timer
        click = _UI[
            _UI.index("save.addEventListener(\"click\"") : _UI.index(
                "[CF V2 SHOW PHONE OPTIONAL]"
            )
        ]
        # First assignment of جاري should be inside setTimeout callback
        self.assertIn("phoneLoadingTimer = window.setTimeout", click)
        self.assertLess(
            click.index("phoneLoadingTimer = window.setTimeout"),
            click.index('save.textContent = "جاري حفظ الرقم…"'),
        )

    def test_runtime_version(self) -> None:
        self.assertIn("v2-widget-zero-friction-v2_2", _LOADER)


if __name__ == "__main__":
    unittest.main()
