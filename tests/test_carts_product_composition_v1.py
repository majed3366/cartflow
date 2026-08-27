# -*- coding: utf-8 -*-
"""Carts Product Composition V1 — static contract guards (no new semantics)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")
CARTS_CSS = (ROOT / "static" / "merchant_ui_v2_carts.css").read_text(encoding="utf-8")
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")


class CartsProductCompositionV1Tests(unittest.TestCase):
    def test_page_stage_wired_not_stub(self) -> None:
        self.assertIn('id="cf2-carts-root"', V2_HTML)
        self.assertIn("carts-product-composition-v1", CARTS_JS)
        self.assertIn("CartFlowUiV2Carts", APP_JS)
        self.assertIn('{ id: "carts", label: "السلال", slice: true }', APP_JS)
        self.assertIn("merchant_ui_v2_carts.js", V2_HTML)
        self.assertNotIn("قسم السلال خارج شريحة V2", V2_HTML)

    def test_canonical_question_and_ops_filters(self) -> None:
        self.assertIn(
            "ما السلال التي تحتاج انتباهي الآن، وما الإجراء التشغيلي المطلوب لكل سلة؟",
            V2_HTML,
        )
        for key in ("all", "attention", "nophone", "sent", "recovered"):
            self.assertIn('key: "%s"' % key, CARTS_JS)
        self.assertIn("يحتاجني", CARTS_JS)
        self.assertIn("بانتظار رقم العميل", CARTS_JS)
        self.assertIn("اكتمل", CARTS_JS)

    def test_primary_action_contract_unchanged(self) -> None:
        for key in (
            "wait",
            "contact_customer",
            "follow_up_manually",
            "review_cart",
            "no_action_required",
            "reopen",
        ):
            self.assertIn(key, CARTS_JS)
        self.assertIn("/api/dashboard/normal-carts", CARTS_JS)
        self.assertIn("/api/dashboard/cart-lifecycle/archive", CARTS_JS)
        self.assertIn("/api/dashboard/cart-lifecycle/reopen", CARTS_JS)
        self.assertIn("data-cf-primary-action", CARTS_JS)

    def test_purchase_suppresses_contact(self) -> None:
        self.assertIn("isPurchased", CARTS_JS)
        self.assertIn('pa.key !== "contact_customer"', CARTS_JS)
        self.assertIn("no_action_required", CARTS_JS)

    def test_no_workspace_or_vip_config(self) -> None:
        forbidden = (
            "merchant_value_stories_v1",
            "merchant_product_language",
            "ما القرار الذي يجب أن أتخذه",
            "vip_cart_threshold",
            "ma-vip-settings-form",
            "commerce_situations",
        )
        for token in forbidden:
            self.assertNotIn(token, CARTS_JS)
            self.assertNotIn(token, CARTS_CSS)
        self.assertNotIn("vip_cart_threshold", V2_HTML)

    def test_mobile_queue_then_detail(self) -> None:
        self.assertIn("is-detail-open", CARTS_JS)
        self.assertIn("data-carts-back", CARTS_JS)
        self.assertIn("@media (max-width: 1023px)", CARTS_CSS)
        self.assertIn("is-detail-open .cf2-carts__queue", CARTS_CSS)
        self.assertIn("cf2-carts__back", CARTS_CSS)

    def test_shell_home_workspace_untouched_markers(self) -> None:
        self.assertIn("shell-integration-v1", V2_HTML)
        self.assertIn("home-stage-closure-v1", HOME_JS)
        self.assertIn("workspace-composition-closure-v1", WS_JS)
        self.assertIn("carts: null", APP_JS)

    def test_no_fake_metrics_language(self) -> None:
        self.assertNotIn("conversion", CARTS_JS.lower())
        self.assertNotIn("confidence", CARTS_JS.lower())
        self.assertIn("لا توجد سلال تحتاج تدخلك الآن", CARTS_JS)

    def test_queue_does_not_repeat_identical_why_and_state(self) -> None:
        self.assertIn("whyText && whyText !== stateText", CARTS_JS)
        self.assertIn("product && product !== title", CARTS_JS)


if __name__ == "__main__":
    unittest.main()
