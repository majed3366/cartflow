# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from services.cartflow_merchant_lifecycle_precedence import (
    lifecycle_delay_scheduling_only,
    lifecycle_returned_evidence,
)


class MerchantLifecyclePrecedenceTests(unittest.TestCase):
    def test_queued_tail_does_not_suppress_return_when_anti_spam_in_history(self) -> None:
        log_ss = frozenset({"mock_sent", "skipped_anti_spam", "queued"})
        ret = lifecycle_returned_evidence(
            bh={},
            ls="queued",
            bk="",
            pk="pending_second_attempt",
            cr="sent",
            log_ss=log_ss,
            dashboard_return_track=False,
            dashboard_return_intel_panel=False,
        )
        self.assertTrue(ret)
        self.assertFalse(
            lifecycle_delay_scheduling_only(
                ls="queued",
                pk="pending_second_attempt",
                purchased=False,
                replied=False,
                returned=ret,
            )
        )

    def test_dashboard_return_track_counts_as_returned(self) -> None:
        self.assertTrue(
            lifecycle_returned_evidence(
                bh={},
                ls="queued",
                bk="",
                pk="pending_send",
                cr="pending",
                log_ss=frozenset({"queued"}),
                dashboard_return_track=True,
                dashboard_return_intel_panel=False,
            )
        )


if __name__ == "__main__":
    unittest.main()
