# -*- coding: utf-8 -*-
"""Cart Detail Migration v1 — routing consumer certification tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.cart_detail_projection_v1 import (
    MODE_EXPLANATION,
    attach_cart_detail_projection_v1,
    build_cart_detail_projection_v1,
)
from services.knowledge_routing_v1 import SURFACE_CART_DETAIL
from services.merchant_decision_layer_v1 import (
    DECISION_CONTACT_CUSTOMER,
    attach_merchant_decisions_v1,
    attach_merchant_decision_layer_v1,
)
from services.merchant_explanation_v1 import attach_merchant_explanation_v1
from services.merchant_proof_surface_v1 import attach_merchant_proof_surface_v1

_ROOT = Path(__file__).resolve().parent.parent
_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")


def _sample_row(**overrides: object) -> dict:
    base = {
        "recovery_key": "rk:demo:1",
        "store_slug": "demo-store",
        "customer_lifecycle_state": "waiting_send",
        "customer_lifecycle_label_ar": "بانتظار الإرسال",
        "customer_lifecycle_what_happened_ar": "أضاف عميل منتجات للسلة.",
        "customer_lifecycle_system_did_ar": "CartFlow ينتظر إرسال رسالة الاسترجاع.",
        "customer_lifecycle_what_next_ar": "سيتم الإرسال تلقائياً.",
        "customer_lifecycle_merchant_needed_ar": "لا",
        "customer_lifecycle_dashboard_action": "archive",
        "merchant_decision_key": DECISION_CONTACT_CUSTOMER,
        "merchant_intervention_executable": True,
        "merchant_intervention_contact_href": "https://wa.me/966500000000",
        "merchant_intervention_action_ar": "فتح واتساب",
    }
    base.update(overrides)
    attach_merchant_proof_surface_v1(
        base,
        recovery_key=str(base["recovery_key"]),
        purchase_truth=False,
        customer_lifecycle_state=str(base["customer_lifecycle_state"]),
        customer_lifecycle_what_happened_ar=str(base["customer_lifecycle_what_happened_ar"]),
        log_statuses=[],
        merchant_decision_key=str(base.get("merchant_decision_key") or ""),
    )
    attach_merchant_explanation_v1(base, purchase_truth=False)
    attach_merchant_decision_layer_v1(
        base,
        customer_lifecycle_state=str(base["customer_lifecycle_state"]),
        customer_lifecycle_merchant_needed_ar=str(base["customer_lifecycle_merchant_needed_ar"]),
        has_phone=True,
        purchase_truth=False,
    )
    attach_merchant_decisions_v1(base, purchase_truth=False)
    attach_cart_detail_projection_v1(base)
    return base


class CartDetailMigrationV1Tests(unittest.TestCase):
    def test_js_has_no_merchant_decision_executable(self) -> None:
        forbidden = (
            "merchantDecisionExecutable",
            "MERCHANT_DECISION_LABEL_AR",
            "NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS",
        )
        for token in forbidden:
            self.assertNotIn(token, _JS, msg=f"JS still owns knowledge: {token}")

    def test_js_uses_cart_detail_projection(self) -> None:
        self.assertIn("cart_detail_projection_v1", _JS)
        self.assertIn("cartDetailProjection", _JS)

    def test_projection_attached_with_routing_block(self) -> None:
        row = _sample_row()
        proj = row["cart_detail_projection_v1"]
        self.assertEqual(proj["version"], "v1")
        self.assertEqual(proj["mode"], MODE_EXPLANATION)
        self.assertIn("explanation", proj)
        self.assertIn("knowledge_routing_v1", proj)
        self.assertEqual(proj["knowledge_routing_v1"]["surface"], SURFACE_CART_DETAIL)

    def test_explanation_from_merchant_explanation_v1(self) -> None:
        row = _sample_row()
        expl = row["cart_detail_projection_v1"]["explanation"]
        source = row["merchant_explanation_v1"]
        self.assertEqual(expl["status_label_ar"], source["status_label_ar"])
        self.assertEqual(expl["what_happened_ar"], source["what_happened_ar"])

    def test_suggested_action_from_routed_decision_not_js_gate(self) -> None:
        row = _sample_row(merchant_intervention_executable=False)
        sa = row["cart_detail_projection_v1"]["suggested_action"]
        self.assertIn("visible", sa)
        self.assertIn("label_ar", sa)
        self.assertIn("routing_priority", sa)

    def test_contact_action_from_row_semantics(self) -> None:
        row = _sample_row()
        contact = row["cart_detail_projection_v1"]["contact_action"]
        self.assertTrue(contact["visible"])
        self.assertIn("wa.me", contact["href"])

    def test_lifecycle_ui_archive_visible(self) -> None:
        row = _sample_row(customer_lifecycle_dashboard_action="archive")
        lc = row["cart_detail_projection_v1"]["lifecycle_ui"]
        self.assertTrue(lc["archive_visible"])
        self.assertFalse(lc["reopen_visible"])

    def test_archived_mode(self) -> None:
        row = _sample_row(
            customer_lifecycle_state="archived",
            customer_lifecycle_is_archived_visual=True,
            customer_lifecycle_dashboard_action="reopen",
        )
        proj = row["cart_detail_projection_v1"]
        self.assertEqual(proj["mode"], "archived")
        self.assertTrue(proj["lifecycle_ui"]["reopen_visible"])

    def test_identical_input_identical_projection(self) -> None:
        row_a = _sample_row()
        row_b = _sample_row()
        self.assertEqual(
            row_a["cart_detail_projection_v1"]["suggested_action"],
            row_b["cart_detail_projection_v1"]["suggested_action"],
        )

    def test_build_without_attach_helper(self) -> None:
        row = _sample_row()
        del row["cart_detail_projection_v1"]
        built = build_cart_detail_projection_v1(row)
        self.assertEqual(built["surface"], SURFACE_CART_DETAIL)
        self.assertTrue(built["explanation"]["status_label_ar"])


if __name__ == "__main__":
    unittest.main()
