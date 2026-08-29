# -*- coding: utf-8 -*-
"""Communication Product Composition V1 — ownership and truth guards."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
COMMS_CSS = (ROOT / "static" / "merchant_ui_v2_comms.css").read_text(encoding="utf-8")
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")


class CommunicationProductCompositionV1Tests(unittest.TestCase):
    def test_page_stage_wired_not_stub(self) -> None:
        self.assertIn('id="cf2-comms-root"', V2_HTML)
        self.assertIn("communication-product-composition-v1", COMMS_JS)
        self.assertIn("CartFlowUiV2Comms", APP_JS)
        self.assertIn("merchant_ui_v2_comms.js", V2_HTML)
        self.assertIn("merchant_ui_v2_comms.css", V2_HTML)
        self.assertNotIn("قسم التواصل خارج شريحة V2", V2_HTML)
        self.assertIn(
            "ماذا حدث في التواصل مع العملاء، وما الذي يحتاج متابعتي الآن؟",
            V2_HTML,
        )

    def test_canonical_hash_is_communication(self) -> None:
        self.assertIn('hashId = id === "comms" ? "communication" : id', APP_JS)
        self.assertIn('h === "communication" || h === "messages"', APP_JS)

    def test_runtime_truth_endpoints_only(self) -> None:
        self.assertIn("/api/dashboard/messages", COMMS_JS)
        self.assertIn("/api/dashboard/followups", COMMS_JS)
        self.assertIn("/api/dashboard/summary", COMMS_JS)
        self.assertIn("merchant_message_history_rows", COMMS_JS)
        self.assertIn("merchant_followup_rows", COMMS_JS)
        self.assertIn("needs_merchant_followup", COMMS_JS)

    def test_not_an_inbox(self) -> None:
        forbidden = (
            "unread",
            "wa.me",
            "فتح واتساب",
            "contact_wa_href",
            "typing",
            "read receipt",
            "conversation_id",
            "thread_id",
        )
        blob = COMMS_JS.lower()
        for token in forbidden:
            self.assertNotIn(token.lower(), blob)

    def test_carts_handoff_not_execution(self) -> None:
        self.assertIn('href="#carts"', COMMS_JS)
        self.assertIn("هذه الحالة تحتاج متابعتك", COMMS_JS)
        self.assertIn("افتح المتابعة في السلال", COMMS_JS)
        self.assertNotIn("/api/dashboard/cart-lifecycle", COMMS_JS)
        self.assertNotIn("contact_customer", COMMS_JS)

    def test_settings_not_embedded(self) -> None:
        self.assertIn('href="#settings"', COMMS_JS)
        self.assertIn("ضبط التواصل", COMMS_JS)
        self.assertNotIn("trigger-templates", COMMS_JS)
        self.assertNotIn("WABA", COMMS_JS)

    def test_state_hierarchy_contract(self) -> None:
        for key in (
            "NEEDS_MERCHANT_RESPONSE",
            "AUTOMATED_BY_CARTFLOW",
            "WAITING_FOR_CUSTOMER",
            "BLOCKED_BY_CONFIGURATION",
            "COMPLETED_OR_TERMINAL",
        ):
            self.assertIn(key, COMMS_JS)
        self.assertIn("أحداث التواصل", COMMS_JS)
        self.assertNotIn("bubble", COMMS_JS.lower())

    def test_mobile_list_then_detail(self) -> None:
        self.assertIn("is-detail-open", COMMS_JS)
        self.assertIn("data-comms-back", COMMS_JS)
        self.assertIn("@media (max-width: 1023px)", COMMS_CSS)
        self.assertIn("is-detail-open .cf2-comms__list", COMMS_CSS)
        self.assertIn("cf2-comms__back", COMMS_CSS)

    def test_shell_home_workspace_carts_untouched(self) -> None:
        self.assertIn("shell-integration-v1", V2_HTML)
        self.assertIn("home-stage-closure-v1", HOME_JS)
        self.assertIn("workspace-composition-closure-v1", WS_JS)
        self.assertIn("carts-product-composition-v1", CARTS_JS)
        self.assertIn("comms: null", APP_JS)
        self.assertIn("carts: null", APP_JS)

    def test_purchase_terminal_copy(self) -> None:
        self.assertIn("لا إجراء استرداد بعد تأكيد الشراء", COMMS_JS)
        self.assertIn("isPurchasedMessage", COMMS_JS)

    def test_visual_hierarchy_does_not_change_semantics(self) -> None:
        self.assertIn("cf2-comms__chip--own", COMMS_JS)
        self.assertIn("cf2-comms__ctx--ref", COMMS_JS)
        self.assertIn("التواصل غير جاهز", COMMS_JS)
        self.assertIn("لا يوجد ما يحتاج متابعتك", COMMS_JS)
        self.assertIn("CartFlow يتابع الحالات الآلية. السجل يبقى متاحاً.", COMMS_JS)
        self.assertIn(".cf2-comms.is-blocked .cf2-comms__orient-h", COMMS_CSS)
        self.assertIn(".cf2-comms__ctx--ref", COMMS_CSS)
        self.assertNotIn("warning", COMMS_CSS.lower())
        self.assertNotIn("banner", COMMS_CSS.lower())


if __name__ == "__main__":
    unittest.main()
