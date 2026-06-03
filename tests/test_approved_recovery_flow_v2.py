# -*- coding: utf-8 -*-
"""Approved V2 cart recovery UX — short suggestions, شكراً, optional phone once."""
from __future__ import annotations

import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_FLOWS = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_flows.js"
_UI = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_ui.js"
_CONFIG = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_config.js"
_LOADER = _ROOT / "static" / "widget_loader.js"


class ApprovedRecoveryFlowV2Tests(unittest.TestCase):
    def test_opening_question_is_cart_recovery(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn('return "تبي أساعدك تكمل طلبك؟"', flows)
        self.assertNotIn("تحتاج مساعدة قبل ما تطلع؟", flows.split("getCartRecoveryQuestion")[1][:200])

    def test_suggestion_bullets_not_long_paragraphs(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("RECOVERY_SUGGESTIONS", flows)
        self.assertIn("قد يفيدك", _UI.read_text(encoding="utf-8"))
        self.assertIn("الدفع لاحقاً", flows)
        self.assertIn("معرفة خيارات الشراء المتاحة", flows)
        self.assertIn("متابعة حالة الطلب", flows)
        self.assertIn("شروط الضمان", flows)
        self.assertIn("شكراً", _UI.read_text(encoding="utf-8"))
        ui = _UI.read_text(encoding="utf-8")
        compact_block = ui.split("if (!compact)", 1)[0]
        self.assertNotIn("أحتاج مساعدة الآن", compact_block)

    def test_no_price_sub_branch_before_suggestions(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertNotIn("renderPriceBranches", flows)
        self.assertNotIn("price_discount_request", flows)

    def test_phone_after_thanks_optional_once(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("handleThanksAfterReason", flows)
        self.assertIn("renderOptionalPhoneFollowup", _UI.read_text(encoding="utf-8"))
        self.assertIn("اترك رقمك للمتابعة", flows)
        self.assertIn("cartflow_cf_v2_optional_phone_done", flows)
        self.assertNotIn("openReasonPhoneImmediate", flows)

    def test_other_reason_form_copy(self) -> None:
        ui = _UI.read_text(encoding="utf-8")
        self.assertIn("وش السبب اللي مخلّيك متردد؟", ui)
        self.assertIn("renderOtherRecoveryForm", ui)
        self.assertIn("اختياري", ui)

    def test_reason_labels_match_catalog(self) -> None:
        cfg = _CONFIG.read_text(encoding="utf-8")
        for label in ("السعر", "الشحن", "الجودة", "التوصيل", "الضمان", "سبب آخر"):
            self.assertIn('"' + label + '"', cfg)

    def test_browsing_assistant_still_isolated_to_exit_no_cart(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("اختَر واحد يخدمك الآن", flows)
        idx = flows.find("function showExitNoCart")
        self.assertGreater(idx, 0)
        self.assertIn("أبحث عن منتج", flows[idx : idx + 1200])

    def test_back_on_suggestion_screen(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        ui = _UI.read_text(encoding="utf-8")
        self.assertIn("onBackReasons", flows)
        self.assertIn("mountReasonList();", flows.split("onBackReasons")[1][:120])
        self.assertIn("appendBackButton", ui)
        self.assertIn('back.textContent = "رجوع"', ui)

    def test_no_retry_button_in_compact_recovery(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        ui = _UI.read_text(encoding="utf-8")
        self.assertNotIn("onRetryBackgroundSave", flows.split("showContinuationQuiet")[1][:900])
        self.assertNotIn("إعادة إرسال", ui.split("renderOtherDraftForm")[0])

    def test_runtime_version_bumped(self) -> None:
        self.assertIn("v2-storefront-ux-cleanup-1", _LOADER.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
