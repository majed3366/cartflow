# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from services.recovery_message_strategy import get_recovery_message


class RecoveryMessageStrategyTests(unittest.TestCase):
    def test_three_attempts_are_distinct(self) -> None:
        m1 = get_recovery_message("price", 1)
        m2 = get_recovery_message("price", 2)
        m3 = get_recovery_message("price", 3)
        self.assertNotEqual(m1, m2)
        self.assertNotEqual(m2, m3)
        self.assertNotEqual(m1, m3)

    def test_attempt_roles_keywords(self) -> None:
        m1 = get_recovery_message(None, 1)
        m2 = get_recovery_message("shipping", 2)
        m3 = get_recovery_message("warranty", 3)
        self.assertIn("كمّلت", m1)
        self.assertTrue("شحن" in m2 or "مهمة" in m2)
        self.assertTrue(
            "نفد" in m3 or "محفوظ" in m3 or "إكمال" in m3 or "طلبك" in m3
        )

    def test_attempt_index_clamped(self) -> None:
        self.assertEqual(get_recovery_message("price", 1), get_recovery_message("price", 0))
        self.assertEqual(get_recovery_message("price", 3), get_recovery_message("price", 99))

    def test_merchant_guided_overrides_default(self) -> None:
        class _S:
            reason_templates_json = '{"price": {"guided_attempts": {"2": "نص مخصص للتاجر"}}}'

        d2 = get_recovery_message("price_high", 2)
        c2 = get_recovery_message("price_high", 2, _S())
        self.assertNotEqual(c2, d2)
        self.assertEqual(c2, "نص مخصص للتاجر")

    def test_per_reason_defaults_differ(self) -> None:
        p = get_recovery_message("price", 1)
        s = get_recovery_message("shipping", 1)
        self.assertNotEqual(p, s)


if __name__ == "__main__":
    unittest.main()
