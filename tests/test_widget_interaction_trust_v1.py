# -*- coding: utf-8 -*-
"""Widget Journey V2 — interaction reliability & trust."""
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
_SHELL = (_ROOT / "static/cartflow_widget_runtime/cartflow_widget_shell.js").read_text(
    encoding="utf-8"
)
_LOADER = (_ROOT / "static/widget_loader.js").read_text(encoding="utf-8")


class WidgetInteractionTrustV1Tests(unittest.TestCase):
    def test_reason_ack_before_bridge_and_persist(self) -> None:
        idx = _FLOWS.index("function openReasonPath")
        block = _FLOWS[idx : idx + 9000]
        self.assertIn("acknowledgeReasonPick", block)
        self.assertIn("[CF REASON ACK]", block)
        self.assertIn("جاري الحفظ…", block)
        self.assertIn('data-cf-reason-selected', block)
        # Ack + in_flight lock happen before ensureCartTruthBeforeReason
        self.assertLess(
            block.index("acknowledgeReasonPick();"),
            block.index("ensureCartTruthBeforeReason"),
        )
        self.assertLess(
            block.index("st().reason_save_in_flight = true;"),
            block.index("ensureCartTruthBeforeReason"),
        )
        # Persist still before transition
        self.assertLess(
            block.index("Cf.Api.postReason(payloadCopy)"),
            block.index("showContinuation(rk, subCat)"),
        )

    def test_reason_fail_clears_selection(self) -> None:
        self.assertIn("clearReasonPickVisual", _FLOWS)
        self.assertIn("failReasonPersist", _FLOWS)

    def test_phone_save_immediate_ack(self) -> None:
        self.assertIn("[CF PHONE SAVE ACK]", _UI)
        self.assertIn("جاري الحفظ…", _UI)
        self.assertIn("جاري حفظ الرقم…", _UI)
        self.assertIn("Promise.resolve(ret)", _UI)
        self.assertIn("[CF PHONE SAVE ACK SUCCESS]", _FLOWS)
        self.assertIn("تم حفظ الرقم — سنتابع طلبك", _FLOWS)
        self.assertIn("return Cf.Phone.postReasonMerged", _FLOWS)

    def test_shell_footer_status_exported(self) -> None:
        self.assertIn("showFooterMessage: showFooterMessage", _SHELL)
        self.assertIn("hideFooterMessage: hideFooterMessage", _SHELL)

    def test_runtime_version_bumped(self) -> None:
        self.assertIn("v2-widget-interaction-trust-v1", _LOADER)

    def test_double_submit_still_guarded(self) -> None:
        self.assertIn('why: "in_flight"', _FLOWS)
        self.assertIn('if (b.getAttribute("disabled") === "true") return', _UI)
        self.assertIn('if (save.getAttribute("disabled") === "true") return', _UI)


if __name__ == "__main__":
    unittest.main()
