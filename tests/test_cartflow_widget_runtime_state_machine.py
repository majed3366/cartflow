# -*- coding: utf-8 -*-
"""Static regressions for cartflow_widget.js deterministic runtime helpers."""
from __future__ import annotations

import pathlib
import unittest


_WIDGET = pathlib.Path(__file__).resolve().parent.parent / "static" / "cartflow_widget.js"


class CartflowWidgetRuntimeStateMachineTests(unittest.TestCase):
    def test_runtime_controller_and_logs_present(self) -> None:
        s = _WIDGET.read_text(encoding="utf-8")

        needles = (
            "function cfRuntimeConfig(",
            "var cfRuntimeTrigger = { timer:",
            '"[CF RUNTIME CONFIG]"',
            '"[CF TIMER CLEAR]"',
            '"[CF TIMER SCHEDULE]"',
            '"[CF TIMER FIRE]"',
            '"[CF TIMER BLOCKED]"',
            '"[CF WIDGET SHOW]"',
            '"[CF EXIT INTENT DETECTED]"',
            '"[CF EXIT INTENT SCHEDULED]"',
            '"[CF EXIT INTENT FIRE]"',
            '"[CF EXIT INTENT BLOCKED]"',
            "function cfHandleReasonSelected(",
            "function cfAfterReasonSaved(",
            "function cfShowPhoneCapture(",
            "function cfShowContinuation(",
            '"[CF PHONE SHOW]"',
            '"[CF PHONE SAVE START]"',
            '"[CF PHONE SAVE SUCCESS]"',
            '"[CF PHONE SAVE FAILED]"',
            '"[CF CONTINUATION SHOW]"',
            "computeRuntimeHesitationAnchorBlockReason",
        )
        missing = [n for n in needles if n not in s]
        self.assertEqual(
            missing,
            [],
            "Missing snippets in widget: " + ", ".join(missing),
        )

    def test_removed_legacy_duplicate_reason_branch_removed(self) -> None:
        s = _WIDGET.read_text(encoding="utf-8")
        self.assertNotIn("cfNonVipClassicReasonAfterSaveUi", s)
