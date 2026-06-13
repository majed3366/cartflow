# -*- coding: utf-8 -*-
from __future__ import annotations

from services.customer_lifecycle_states_v1 import (
    STATE_ARCHIVED,
    STATE_COMPLETED,
    STATE_NEEDS_INTERVENTION,
    STATE_WAITING_NEXT_SCHEDULED,
    attach_customer_lifecycle_state_v1,
    classify_customer_lifecycle_state_v1,
)
from services.lifecycle_authority_recovery_v1 import (
    attach_merchant_row_lifecycle_authority,
    lifecycle_authority_active_count,
    sync_merchant_followup_clarity_from_lifecycle,
    sync_vip_legacy_display_from_lifecycle,
)


def test_vip_lane_uses_lifecycle_not_vip_column_label() -> None:
    lc = classify_customer_lifecycle_state_v1(
        recovery_key="s:vip",
        is_vip_lane=True,
        vip_lifecycle_status_evidence="contacted",
    )
    assert lc.state_key == STATE_NEEDS_INTERVENTION
    assert "تم التواصل" in lc.label_ar


def test_vip_closed_maps_to_archived_lifecycle() -> None:
    lc = classify_customer_lifecycle_state_v1(
        recovery_key="s:vip",
        is_vip_lane=True,
        vip_lifecycle_status_evidence="closed",
    )
    assert lc.state_key == STATE_ARCHIVED


def test_vip_converted_maps_to_completed_lifecycle() -> None:
    lc = classify_customer_lifecycle_state_v1(
        recovery_key="s:vip",
        is_vip_lane=True,
        vip_lifecycle_status_evidence="converted",
        cart_status="recovered",
    )
    assert lc.state_key == STATE_COMPLETED


def test_followup_clarity_derives_from_lifecycle_not_schedule() -> None:
    payload: dict[str, object] = {
        "customer_lifecycle_state": STATE_WAITING_NEXT_SCHEDULED,
        "customer_lifecycle_what_next_ar": "رسالة تذكير مجدولة — ساعتين",
        "customer_lifecycle_next_followup_line_ar": "المتابعة القادمة بعد: ساعتين",
    }
    sync_merchant_followup_clarity_from_lifecycle(
        payload, sent_count=1, configured_count=2
    )
    assert payload["merchant_followup_next_line_ar"] == "المتابعة القادمة بعد: ساعتين"
    assert payload.get("merchant_followup_sequence_line_ar") is None


def test_attach_row_authority_syncs_vip_legacy_derivatives() -> None:
    row: dict[str, object] = {"recovery_key": "s:1"}
    attach_merchant_row_lifecycle_authority(
        row,
        recovery_key="s:1",
        is_vip_lane=True,
        vip_lifecycle_status_evidence="abandoned",
    )
    assert row.get("customer_lifecycle_state") == STATE_NEEDS_INTERVENTION
    assert row.get("display_status_ar") == row.get("customer_lifecycle_label_ar")
    assert row.get("alert_status") == STATE_NEEDS_INTERVENTION


def test_summary_active_count_from_lifecycle_only() -> None:
    rows = [
        {"customer_lifecycle_state": STATE_NEEDS_INTERVENTION},
        {"customer_lifecycle_state": STATE_ARCHIVED},
        {"customer_lifecycle_state": STATE_COMPLETED},
        {"merchant_cart_bucket": "sent"},
    ]
    assert lifecycle_authority_active_count(rows) == 1


def test_sync_vip_legacy_from_completed() -> None:
    row = {
        "customer_lifecycle_state": STATE_COMPLETED,
        "customer_lifecycle_label_ar": "تمت الاستعادة",
    }
    sync_vip_legacy_display_from_lifecycle(row)
    assert row["vip_lifecycle_status_evidence"] == "converted"
    assert row["vip_lifecycle_hide_actions"] is True


def test_normal_lane_not_blanketed_to_vip_intervention() -> None:
    lc = classify_customer_lifecycle_state_v1(
        recovery_key="s:n",
        phase_key="pending_send",
        coarse="pending",
        sent_count=0,
        is_vip_lane=False,
    )
    assert lc.state_key != STATE_NEEDS_INTERVENTION


def test_attach_lifecycle_still_sets_bucket() -> None:
    payload: dict[str, object] = {}
    attach_customer_lifecycle_state_v1(
        payload,
        recovery_key="s:r",
        merchant_archived=True,
    )
    assert payload["customer_lifecycle_state"] == STATE_ARCHIVED
    assert payload["merchant_cart_bucket"] == "archived"
