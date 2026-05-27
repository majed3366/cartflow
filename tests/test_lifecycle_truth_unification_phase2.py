# -*- coding: utf-8 -*-
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services.customer_lifecycle_states_v1 import (
    STATE_ARCHIVED,
    STATE_RETURN_TO_SITE,
    STATE_WAITING_FIRST_SEND,
    attach_customer_lifecycle_state_v1,
    lifecycle_filter_counts_from_rows,
    lifecycle_truth_consistency_for_row,
)


def test_attach_lifecycle_sets_bucket_from_owner_state() -> None:
    payload: dict[str, object] = {}
    lc = attach_customer_lifecycle_state_v1(
        payload,
        recovery_key="s:r",
        phase_key="customer_returned",
        coarse="returned",
        sent_count=1,
        log_statuses={"returned_to_site", "sent_real"},
        behavioral={"user_returned_to_site": True},
        attempt_cap=2,
    )
    assert lc.state_key == STATE_RETURN_TO_SITE
    assert payload["merchant_cart_bucket"] == "sent"
    assert payload["merchant_cart_primary_bucket"] == "return_to_site"
    assert payload["merchant_cart_visible_tabs"] == ["all", "sent"]


def test_attach_archived_marks_terminal_and_not_active() -> None:
    payload: dict[str, object] = {}
    lc = attach_customer_lifecycle_state_v1(
        payload,
        recovery_key="s:r",
        merchant_archived=True,
    )
    assert lc.state_key == STATE_ARCHIVED
    assert payload["merchant_cart_is_terminal"] is True
    assert payload["merchant_cart_is_active"] is False
    assert payload["merchant_cart_bucket"] == "archived"


def test_counts_derive_from_lifecycle_state_only() -> None:
    rows = [
        {"customer_lifecycle_state": STATE_WAITING_FIRST_SEND, "merchant_cart_bucket": "sent"},
        {"customer_lifecycle_state": STATE_RETURN_TO_SITE, "merchant_cart_bucket": "waiting"},
        {"customer_lifecycle_state": STATE_ARCHIVED, "merchant_cart_bucket": "attention"},
    ]
    counts = lifecycle_filter_counts_from_rows(rows)
    assert counts["all"] == 3
    assert counts["waiting"] == 1
    assert counts["sent"] == 1
    assert counts["attention"] == 0
    assert counts["recovered"] == 0


def test_consistency_check_flags_impossible_archived_waiting() -> None:
    ok, reason = lifecycle_truth_consistency_for_row(
        {
            "customer_lifecycle_state": STATE_ARCHIVED,
            "customer_lifecycle_label_ar": "مؤرشفة",
            "customer_lifecycle_is_archived_visual": True,
            "merchant_cart_bucket": "waiting",
        }
    )
    assert ok is False
    assert "archived" in reason


def test_dev_lifecycle_truth_check_endpoint() -> None:
    client = TestClient(app)
    fake_row = {
        "recovery_key": "store:s1",
        "customer_lifecycle_state": "waiting_first_send",
        "customer_lifecycle_label_ar": "بانتظار الإرسال",
        "customer_lifecycle_is_archived_visual": False,
        "merchant_cart_bucket": "waiting",
    }
    with (
        patch("main._dashboard_recovery_store_row", return_value=None),
        patch(
            "main._normal_recovery_merchant_lightweight_alert_list_for_api",
            return_value=([fake_row], {"carts_count": 1}),
        ),
        patch("services.recovery_truth_timeline_v1.get_recovery_truth_timeline", return_value=[]),
        patch("services.recovery_truth_timeline_v1.timeline_status_set", return_value=frozenset()),
    ):
        res = client.get("/dev/lifecycle-truth-check", params={"recovery_key": "store:s1"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["consistent"] is True
    assert body["dashboard_tab"] == "waiting"
    assert body["count_bucket"] == "waiting"
