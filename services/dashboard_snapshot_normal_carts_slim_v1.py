# -*- coding: utf-8 -*-
"""
Slim normal-carts payloads for dashboard snapshot persistence.

Live API responses stay full; snapshots keep merchant-visible fields only.
"""
from __future__ import annotations

from typing import Any, Optional

_MESSAGE_PREVIEW_SNAPSHOT_MAX = 120

# Merchant dashboard row fields required for filters, lifecycle UI, archive/reopen.
NORMAL_CARTS_SNAPSHOT_ROW_ALLOWLIST = frozenset(
    {
        "recovery_key",
        "zid_cart_id",
        "cart_id",
        "session_id",
        "store_slug",
        "merchant_case_row_id",
        "id",
        "abandoned_cart_id",
        "customer_lifecycle_state",
        "customer_lifecycle_label_ar",
        "customer_lifecycle_what_happened_ar",
        "customer_lifecycle_system_did_ar",
        "customer_lifecycle_what_next_ar",
        "customer_lifecycle_merchant_needed_ar",
        "customer_lifecycle_dashboard_action",
        "customer_lifecycle_status_row_class",
        "customer_lifecycle_completed_variant",
        "customer_lifecycle_is_archived_visual",
        "customer_lifecycle_next_followup_line_ar",
        "customer_lifecycle_continuation_explanation_ar",
        "merchant_cart_bucket",
        "merchant_cart_primary_bucket",
        "merchant_cart_visible_tabs",
        "merchant_cart_is_terminal",
        "merchant_cart_is_active",
        "merchant_cart_value",
        "merchant_has_customer_phone",
        "merchant_phone_line_ar",
        "merchant_cart_fact_v1",
        "merchant_coarse_status",
        "merchant_status_row_class",
        "merchant_status_label_ar",
        "merchant_next_action_ar",
        "merchant_next_action_urgent",
        "merchant_is_history_slice",
        "merchant_history_note_ar",
        "merchant_recovery_kind",
        "merchant_reason_chip_class",
        "merchant_reason_chip_label_ar",
        "reason_tag",
        "merchant_reason_canonical",
        "merchant_time_relative_ar",
        "merchant_last_seen_display",
        "merchant_followup_progress_ar",
        "merchant_followup_sequence_line_ar",
        "merchant_followup_next_line_ar",
        "merchant_whatsapp_line_ar",
        "merchant_return_line_ar",
        "merchant_purchase_line_ar",
        "message_preview",
        "merchant_decision_key",
        "merchant_intervention_executable",
        "merchant_intervention_contact_href",
        "merchant_intervention_action_ar",
        "merchant_attention_display_group",
        "merchant_identity_trust_ar",
        "merchant_proof_surface_v1",
        "merchant_explanation_v1",
        "merchant_decisions_v1",
        "normal_recovery_continuation_explanation_ar",
        "next_attempt_due_at",
    }
)

NORMAL_CARTS_SNAPSHOT_TOP_LEVEL_KEYS = (
    "merchant_carts_page_rows",
    "merchant_archived_carts_page_rows",
    "merchant_table_rows",
    "merchant_archived_cart_count",
    "merchant_cart_filter_counts",
    "merchant_nav_badge_abandoned",
    "merchant_store_cart_counts",
    "merchant_visible_page_counts",
    "merchant_counter_health",
    "merchant_counter_generated_at",
    "merchant_counter_source",
    "merchant_dashboard_refresh_token",
    "merchant_dashboard_refresh_last_log_id",
    "merchant_dashboard_refresh_last_sent_log_id",
    "merchant_dashboard_refresh_sent_total",
    "merchant_dashboard_refresh_archive_rev",
)

# Heavy / debug fields stripped from snapshots (diagnostic reference).
NORMAL_CARTS_SNAPSHOT_STRIPPED_HEAVY_FIELDS = frozenset(
    {
        "recovery_message_context",
        "durable_lifecycle_closure",
        "last_sent_message_body",
        "lifecycle_evidence_phase_key",
        "lifecycle_evidence_coarse",
        "lifecycle_status",
        "lifecycle_label_ar",
        "lifecycle_status_authority",
        "lifecycle_label_ar_authority",
        "merchant_lifecycle_primary_key",
        "merchant_lifecycle_customer_behavior_ar",
        "merchant_lifecycle_system_outcome_ar",
        "merchant_lifecycle_next_action_ar",
        "recovery_context_status",
        "messages_page_status",
        "carts_page_status",
        "truth_mismatch_detected",
        "truth_mismatch_reason",
        "merchant_followup_sent_count",
        "merchant_followup_configured_count",
    }
)


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _cap_preview(value: Any) -> Optional[str]:
    s = _norm(value)
    if not s:
        return None
    if len(s) <= _MESSAGE_PREVIEW_SNAPSHOT_MAX:
        return s
    return s[: _MESSAGE_PREVIEW_SNAPSHOT_MAX - 1] + "…"


def slim_normal_carts_row_for_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    """Keep allowlisted merchant-visible fields; drop debug/heavy nested blobs."""
    if not isinstance(row, dict):
        return {}
    out: dict[str, Any] = {}
    for key in NORMAL_CARTS_SNAPSHOT_ROW_ALLOWLIST:
        if key not in row:
            continue
        val = row.get(key)
        if val is None:
            continue
        if key == "message_preview":
            capped = _cap_preview(val)
            if capped:
                out[key] = capped
            continue
        if key == "merchant_explanation_v1" and isinstance(val, dict):
            out[key] = {
                k: val[k]
                for k in (
                    "version",
                    "explanation_id",
                    "knowledge_event_type",
                    "merchant_visibility",
                    "eligible_surfaces",
                    "status_label_ar",
                    "what_happened_ar",
                    "system_did_ar",
                    "what_next_ar",
                    "followup_line_ar",
                    "merchant_action_needed_ar",
                    "action_required",
                    "attention_level",
                )
                if k in val and val[k] is not None
            }
            continue
        if key == "merchant_cart_fact_v1" and isinstance(val, dict):
            out[key] = {
                k: val[k]
                for k in ("kind", "label_ar")
                if k in val and val[k] is not None
            }
            continue
        out[key] = val
    return out


def slim_normal_carts_payload_for_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Slim full normal-carts API payload for snapshot storage."""
    active = [
        slim_normal_carts_row_for_snapshot(r)
        for r in list(payload.get("merchant_carts_page_rows") or [])
        if isinstance(r, dict)
    ]
    archived = [
        slim_normal_carts_row_for_snapshot(r)
        for r in list(payload.get("merchant_archived_carts_page_rows") or [])
        if isinstance(r, dict)
    ]
    out: dict[str, Any] = {
        "merchant_carts_page_rows": active,
        "merchant_archived_carts_page_rows": archived,
        "merchant_table_rows": active[:8],
        "merchant_archived_cart_count": int(
            payload.get("merchant_archived_cart_count")
            if payload.get("merchant_archived_cart_count") is not None
            else len(archived)
        ),
        "merchant_cart_filter_counts": dict(
            payload.get("merchant_cart_filter_counts") or {}
        ),
        "merchant_nav_badge_abandoned": int(
            payload.get("merchant_nav_badge_abandoned") or 0
        ),
    }
    for key in NORMAL_CARTS_SNAPSHOT_TOP_LEVEL_KEYS:
        if key in out:
            continue
        if key in payload:
            out[key] = payload[key]
    for key in (
        "merchant_dashboard_refresh_token",
        "merchant_dashboard_refresh_last_log_id",
        "merchant_dashboard_refresh_last_sent_log_id",
        "merchant_dashboard_refresh_sent_total",
        "merchant_dashboard_refresh_archive_rev",
    ):
        if key in payload:
            out[key] = payload[key]
    return out


__all__ = [
    "NORMAL_CARTS_SNAPSHOT_ROW_ALLOWLIST",
    "NORMAL_CARTS_SNAPSHOT_STRIPPED_HEAVY_FIELDS",
    "NORMAL_CARTS_SNAPSHOT_TOP_LEVEL_KEYS",
    "slim_normal_carts_payload_for_snapshot",
    "slim_normal_carts_row_for_snapshot",
]
