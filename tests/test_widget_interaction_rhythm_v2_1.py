# -*- coding: utf-8 -*-
"""Widget Journey V2.1 — interaction rhythm polish (superseded by V2.2 deferred loading)."""
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


class WidgetInteractionRhythmV21Tests(unittest.TestCase):
    def test_reason_ack_is_more_than_border(self) -> None:
        idx = _FLOWS.index("function acknowledgeReasonPick")
        block = _FLOWS[idx : idx + 4500]
        self.assertIn('"✓ " + base', block)
        self.assertIn("[CF REASON ACK]", block)
        self.assertIn('data-cf-reason-transition', block)

    def test_reason_ack_before_persist_unchanged(self) -> None:
        idx = _FLOWS.index("function openReasonPath")
        block = _FLOWS[idx : idx + 14000]
        self.assertLess(
            block.index("acknowledgeReasonPick();"),
            block.index("ensureCartTruthBeforeReason"),
        )
        self.assertLess(
            block.index("Cf.Api.postReason(payloadCopy)"),
            block.index("showContinuation(rk, subCat)"),
        )

    def test_phone_deferred_loading_keeps_success(self) -> None:
        self.assertIn("[CF PHONE SAVE ACK]", _UI)
        self.assertIn("جاري حفظ الرقم…", _UI)
        self.assertIn("phoneLoadingTimer = window.setTimeout", _UI)
        on_save = _FLOWS[_FLOWS.index("onSave: function (pn)") : _FLOWS.index("onSkip:")]
        self.assertNotIn("hideFooterMessage", on_save)
        self.assertIn('showSuccess("تم حفظ الرقم")', _FLOWS)
        self.assertIn("return Cf.Phone.postReasonMerged", on_save)

    def test_runtime_version(self) -> None:
        self.assertIn("v2-widget-", _LOADER)


if __name__ == "__main__":
    unittest.main()
