# -*- coding: utf-8 -*-
"""Smart Actions v1 — rule-based suggestions only (no automation)."""

import unittest

from services.smart_actions import get_cart_smart_action, smart_action_cta_target


def _snap(**parts: object) -> dict[str, object]:
    return dict(parts)


class TestSmartActionsLayerV1(unittest.TestCase):
    def test_a_vip_price_reason_suggests_simple_offer(self) -> None:
        a = get_cart_smart_action(
            _snap(
                is_vip=True,
                reason_tag="price_high",
                vip_lifecycle_effective="contacted",
                has_customer_phone=True,
            )
        )
        self.assertEqual(a["title_ar"], "اقترح عرض بسيط")
        self.assertEqual(smart_action_cta_target(a["action_key"]), "offer_prefill")

    def test_b_vip_contacted_without_price_followup(self) -> None:
        a = get_cart_smart_action(
            _snap(
                is_vip=True,
                reason_tag="shipping",
                vip_lifecycle_effective="contacted",
                has_customer_phone=True,
            )
        )
        self.assertEqual(a["title_ar"], "تابع بلطف")
        self.assertEqual(smart_action_cta_target(a["action_key"]), "reminder_prefill")

    def test_c_vip_no_phone_wait(self) -> None:
        a = get_cart_smart_action(
            _snap(
                is_vip=True,
                reason_tag=None,
                vip_lifecycle_effective="abandoned",
                has_customer_phone=False,
            )
        )
        self.assertEqual(a["title_ar"], "انتظر رقم العميل")
        self.assertEqual(smart_action_cta_target(a["action_key"]), "none")

    def test_d_normal_not_ignored_price_and_default(self) -> None:
        p = get_cart_smart_action(
            _snap(
                is_vip=False,
                reason_tag="price",
                vip_lifecycle_effective="abandoned",
                has_customer_phone=True,
            )
        )
        self.assertEqual(p["title_ar"], "استرجاع عادي")
        self.assertEqual(smart_action_cta_target(p["action_key"]), "reminder_prefill")

        d = get_cart_smart_action(
            _snap(
                is_vip=False,
                reason_tag="thinking",
                vip_lifecycle_effective="abandoned",
                has_customer_phone=True,
            )
        )
        self.assertEqual(d["title_ar"], "متابعة عادية")
        self.assertEqual(smart_action_cta_target(d["action_key"]), "contact")

    def test_vip_price_takes_priority_over_no_phone_and_contacted(self) -> None:
        a = get_cart_smart_action(
            _snap(
                is_vip=True,
                reason_tag="price",
                vip_lifecycle_effective="contacted",
                has_customer_phone=False,
            )
        )
        self.assertEqual(a["action_key"], "vip_suggest_simple_offer")


if __name__ == "__main__":
    unittest.main()
