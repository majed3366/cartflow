# -*- coding: utf-8 -*-
"""Merchant normal-carts must not hide phone-pending carts from active tab."""
from __future__ import annotations

import unittest

from main import (
    NORMAL_RECOVERY_PHASE_KEY_BLOCKED_MISSING_CUSTOMER_PHONE,
    _NORMAL_RECOVERY_ARCHIVED_COARSE_STATUSES,
    _normal_recovery_coarse_status,
)


class TestMerchantNormalCartsActiveVisibility(unittest.TestCase):
    def test_missing_phone_maps_to_pending_not_archived(self) -> None:
        coarse = _normal_recovery_coarse_status(
            NORMAL_RECOVERY_PHASE_KEY_BLOCKED_MISSING_CUSTOMER_PHONE
        )
        self.assertEqual(coarse, "pending")
        self.assertNotIn(coarse, _NORMAL_RECOVERY_ARCHIVED_COARSE_STATUSES)


if __name__ == "__main__":
    unittest.main()
