# -*- coding: utf-8 -*-
"""No-phone dashboard facet — counter/row parity."""
from __future__ import annotations

import unittest

from services.customer_lifecycle_states_v1 import (
    STATE_ARCHIVED,
    STATE_COMPLETED,
    STATE_NEEDS_INTERVENTION,
    UI_FILTER_ATTENTION,
    UI_FILTER_NOPHONE,
)
from services.dashboard_counter_totals_v1 import MerchantCartCounterTotals
from services.dashboard_no_phone_facet_v1 import (
    apply_no_phone_visible_tab_facet,
    is_no_phone_pre_send_dashboard_row,
)


def _no_phone_active_row() -> dict:
    return {
        "merchant_has_customer_phone": False,
        "customer_lifecycle_state": STATE_NEEDS_INTERVENTION,
        "merchant_cart_bucket": UI_FILTER_ATTENTION,
        "merchant_cart_visible_tabs": ["all", UI_FILTER_ATTENTION],
        "merchant_cart_is_active": True,
        "merchant_is_history_slice": False,
    }


class TestNoPhonePreSendDashboardRow(unittest.TestCase):
    def test_active_no_phone_pre_send_matches(self) -> None:
        self.assertTrue(
            is_no_phone_pre_send_dashboard_row(_no_phone_active_row(), log_has_sent=False)
        )

    def test_sent_log_excluded(self) -> None:
        row = _no_phone_active_row()
        self.assertFalse(
            is_no_phone_pre_send_dashboard_row(row, log_has_sent=True)
        )

    def test_archived_excluded(self) -> None:
        row = _no_phone_active_row()
        row["customer_lifecycle_state"] = STATE_ARCHIVED
        self.assertFalse(is_no_phone_pre_send_dashboard_row(row, log_has_sent=False))

    def test_completed_excluded(self) -> None:
        row = _no_phone_active_row()
        row["customer_lifecycle_state"] = STATE_COMPLETED
        self.assertFalse(is_no_phone_pre_send_dashboard_row(row, log_has_sent=False))

    def test_has_phone_excluded(self) -> None:
        row = _no_phone_active_row()
        row["merchant_has_customer_phone"] = True
        self.assertFalse(is_no_phone_pre_send_dashboard_row(row, log_has_sent=False))


class TestNoPhoneVisibleTabFacet(unittest.TestCase):
    def test_appends_nophone_keeps_attention_bucket(self) -> None:
        row = _no_phone_active_row()
        self.assertTrue(apply_no_phone_visible_tab_facet(row, log_has_sent=False))
        self.assertEqual(row["merchant_cart_bucket"], UI_FILTER_ATTENTION)
        self.assertIn(UI_FILTER_NOPHONE, row["merchant_cart_visible_tabs"])
        self.assertIn(UI_FILTER_ATTENTION, row["merchant_cart_visible_tabs"])

    def test_idempotent_append(self) -> None:
        row = _no_phone_active_row()
        apply_no_phone_visible_tab_facet(row, log_has_sent=False)
        apply_no_phone_visible_tab_facet(row, log_has_sent=False)
        self.assertEqual(
            row["merchant_cart_visible_tabs"].count(UI_FILTER_NOPHONE),
            1,
        )

    def test_counter_rule_matches_facet_rule(self) -> None:
        row = _no_phone_active_row()
        facet = apply_no_phone_visible_tab_facet(row, log_has_sent=False)
        counter = is_no_phone_pre_send_dashboard_row(row, log_has_sent=False)
        self.assertEqual(facet, counter)
        totals = MerchantCartCounterTotals()
        if counter:
            totals.no_phone_total += 1
        self.assertEqual(totals.no_phone_total, 1)


class TestNoPhoneClientFilterSemantics(unittest.TestCase):
    """Mirror cartRowMatchesFilterMode: nophone matches visible_tabs."""

    def test_nophone_tab_matches_filter_mode(self) -> None:
        row = _no_phone_active_row()
        apply_no_phone_visible_tab_facet(row, log_has_sent=False)
        tabs = [str(t).lower() for t in row["merchant_cart_visible_tabs"]]
        self.assertIn("nophone", tabs)


if __name__ == "__main__":
    unittest.main()
