# -*- coding: utf-8 -*-
"""
Normal-carts snapshot parity — behavior-preserving snapshot writes.

Governance: live and snapshot builders share ``build_normal_carts_dashboard_api_payload``.
Before persisting, verify row identities, sent-log coverage, and serialization safety.
Block writes that would regress merchant-visible carts.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from services.dashboard_snapshot_v1 import (
    SNAPSHOT_TYPE_NORMAL_CARTS,
    STATUS_ACTIVE,
    STATUS_FAILED,
    decode_snapshot_payload,
    encode_snapshot_payload_json,
    fetch_latest_snapshot_row,
    snapshot_payload_json_cap,
    snapshot_row_is_stale,
)
from services.merchant_dashboard_recovery_resolve_v1 import SENT_LOG_STATUSES
from services.normal_carts_dashboard_batch_v1 import NormalCartsDashboardPerfMeta

_log = logging.getLogger(__name__)


def _payload_json_cap() -> int:
    return snapshot_payload_json_cap(SNAPSHOT_TYPE_NORMAL_CARTS)


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _row_collections(payload: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key in (
        "merchant_carts_page_rows",
        "merchant_archived_carts_page_rows",
        "merchant_table_rows",
    ):
        for row in list(payload.get(key) or []):
            if isinstance(row, dict):
                out.append(row)
    return out


def row_identity_signature(row: dict[str, Any]) -> str:
    rk = _norm(row.get("recovery_key"))
    if rk:
        return f"rk:{rk}"
    aid = int(row.get("merchant_case_row_id") or row.get("abandoned_cart_id") or row.get("id") or 0)
    if aid:
        return f"ac:{aid}"
    cid = _norm(row.get("zid_cart_id") or row.get("cart_id"))
    if cid:
        return f"cart:{cid}"
    return f"row:{id(row)}"


def extract_row_parity_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in _row_collections(payload):
        sig = row_identity_signature(row)
        if sig in seen:
            continue
        seen.add(sig)
        tabs = row.get("merchant_cart_visible_tabs") or []
        tab_list = [str(t).strip().lower() for t in tabs if str(t).strip()]
        records.append(
            {
                "signature": sig,
                "recovery_key": _norm(row.get("recovery_key")) or None,
                "abandoned_cart_id": int(row.get("merchant_case_row_id") or row.get("id") or 0) or None,
                "merchant_case_row_id": int(row.get("merchant_case_row_id") or row.get("id") or 0) or None,
                "cart_id": _norm(row.get("zid_cart_id") or row.get("cart_id")) or None,
                "bucket": _norm(
                    row.get("merchant_cart_bucket")
                    or row.get("merchant_cart_primary_bucket")
                    or row.get("customer_lifecycle_state")
                )
                or None,
                "visible_tabs": tab_list,
            }
        )
    return records


def compare_normal_carts_payload_parity(
    live_payload: dict[str, Any],
    candidate_payload: dict[str, Any],
) -> dict[str, Any]:
    live_sigs = {r["signature"] for r in extract_row_parity_records(live_payload)}
    cand_sigs = {r["signature"] for r in extract_row_parity_records(candidate_payload)}
    live_filters = dict(live_payload.get("merchant_cart_filter_counts") or {})
    cand_filters = dict(candidate_payload.get("merchant_cart_filter_counts") or {})
    return {
        "equivalent": live_sigs == cand_sigs and live_filters == cand_filters,
        "live_row_count": len(live_sigs),
        "candidate_row_count": len(cand_sigs),
        "missing_from_candidate": sorted(live_sigs - cand_sigs),
        "extra_in_candidate": sorted(cand_sigs - live_sigs),
        "live_filter_counts": live_filters,
        "candidate_filter_counts": cand_filters,
    }


def _payload_for_storage(payload: dict[str, Any]) -> dict[str, Any]:
    from services.dashboard_snapshot_normal_carts_slim_v1 import (  # noqa: PLC0415
        slim_normal_carts_payload_for_snapshot,
    )

    return slim_normal_carts_payload_for_snapshot(payload)


def _serialization_check(payload: dict[str, Any]) -> dict[str, Any]:
    clean = _payload_for_storage(payload)
    cap = _payload_json_cap()
    full_json = json.dumps(clean, ensure_ascii=False, default=str)
    storage_json = encode_snapshot_payload_json(clean, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS)
    parse_ok = True
    decoded: dict[str, Any] = {}
    try:
        parsed = json.loads(storage_json)
        decoded = parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        parse_ok = False
        decoded = {}

    full_sigs = {r["signature"] for r in extract_row_parity_records(clean)}
    trunc_sigs = {r["signature"] for r in extract_row_parity_records(decoded)} if parse_ok else set()
    dropped = sorted(full_sigs - trunc_sigs)
    truncated = len(full_json.encode("utf-8")) > cap or len(storage_json) < len(full_json)
    return {
        "json_bytes": len(full_json.encode("utf-8")),
        "json_cap": cap,
        "truncated": truncated,
        "parse_ok": parse_ok,
        "dropped_identities": dropped,
        "storage_json": storage_json,
    }


def _missing_sent_log_identities(
    *,
    store_slug: str,
    payload: dict[str, Any],
    live_payload: Optional[dict[str, Any]] = None,
) -> list[str]:
    slug = _norm(store_slug)
    if not slug:
        return []
    try:
        from services.merchant_dashboard_recovery_resolve_v1 import sent_logs_for_store  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []

    records = extract_row_parity_records(payload)
    rk_set = {_norm(r.get("recovery_key")) for r in records if r.get("recovery_key")}
    cart_set = {_norm(r.get("cart_id")) for r in records if r.get("cart_id")}
    ac_set = {int(r.get("abandoned_cart_id") or 0) for r in records if r.get("abandoned_cart_id")}

    live_records = extract_row_parity_records(live_payload or payload)
    live_rk_set = {_norm(r.get("recovery_key")) for r in live_records if r.get("recovery_key")}
    live_cart_set = {_norm(r.get("cart_id")) for r in live_records if r.get("cart_id")}
    live_ac_set = {
        int(r.get("abandoned_cart_id") or 0) for r in live_records if r.get("abandoned_cart_id")
    }

    missing: list[str] = []
    try:
        logs = sent_logs_for_store(slug, limit=48)
    except Exception:  # noqa: BLE001
        return missing

    for lg in logs:
        status = _norm(getattr(lg, "status", None)).lower()
        if status not in SENT_LOG_STATUSES:
            continue
        rk = _norm(getattr(lg, "recovery_key", None))
        cid = _norm(getattr(lg, "cart_id", None))
        sid = _norm(getattr(lg, "session_id", None))
        aid = int(getattr(lg, "abandoned_cart_id", 0) or 0)
        on_live_dashboard = (
            (rk and rk in live_rk_set)
            or (cid and cid in live_cart_set)
            or (aid and aid in live_ac_set)
        )
        if not on_live_dashboard:
            continue
        found = False
        if rk and rk in rk_set:
            found = True
        if cid and cid in cart_set:
            found = True
        if aid and aid in ac_set:
            found = True
        if not found:
            missing.append(rk or f"{slug}:{cid or sid or aid}")
    return missing


@dataclass
class NormalCartsSnapshotWriteDecision:
    allow_write: bool
    drop_stage: str
    reason: str
    payload_for_storage: dict[str, Any] = field(default_factory=dict)
    storage_json: str = ""
    status: str = STATUS_ACTIVE
    parity: dict[str, Any] = field(default_factory=dict)
    keep_previous: bool = False


def evaluate_normal_carts_snapshot_write(
    *,
    store_slug: str,
    live_payload: dict[str, Any],
    candidate_payload: dict[str, Any],
    perf: Optional[NormalCartsDashboardPerfMeta] = None,
) -> NormalCartsSnapshotWriteDecision:
    """Decide whether to persist a normal_carts snapshot."""
    slug = _norm(store_slug)
    parity = compare_normal_carts_payload_parity(live_payload, candidate_payload)
    storage_payload = _payload_for_storage(candidate_payload)
    storage_parity = compare_normal_carts_payload_parity(live_payload, storage_payload)
    parity["storage_identity_equivalent"] = storage_parity["equivalent"]
    parity["storage_missing_identities"] = storage_parity["missing_from_candidate"]
    parity["sent_log_missing"] = _missing_sent_log_identities(
        store_slug=slug,
        payload=storage_payload,
        live_payload=live_payload,
    )

    ser = _serialization_check(candidate_payload)
    parity["serialization"] = {
        "truncated": ser["truncated"],
        "parse_ok": ser["parse_ok"],
        "dropped_identities": ser["dropped_identities"],
        "json_bytes": ser["json_bytes"],
    }

    prev_row = fetch_latest_snapshot_row(store_slug=slug, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS)
    prev_payload: dict[str, Any] = {}
    prev_valid = False
    if prev_row is not None and not snapshot_row_is_stale(prev_row):
        prev_payload = decode_snapshot_payload(prev_row)
        prev_valid = bool(extract_row_parity_records(prev_payload))

    cand_records = extract_row_parity_records(storage_payload)
    prev_records = extract_row_parity_records(prev_payload)
    cand_sigs = {r["signature"] for r in cand_records}
    prev_sigs = {r["signature"] for r in prev_records}

    degraded = bool(getattr(perf, "degraded", False) or getattr(perf, "partial", False))
    parity["build_degraded"] = degraded
    parity["previous_valid"] = prev_valid
    parity["previous_row_count"] = len(prev_sigs)

    if not parity["equivalent"]:
        return NormalCartsSnapshotWriteDecision(
            allow_write=False,
            drop_stage="row_build",
            reason="live_snapshot_builder_identity_mismatch",
            parity=parity,
            keep_previous=prev_valid,
            status=STATUS_FAILED,
        )

    if not storage_parity["equivalent"]:
        return NormalCartsSnapshotWriteDecision(
            allow_write=False,
            drop_stage="snapshot_write",
            reason="snapshot_slim_identity_loss",
            parity=parity,
            keep_previous=prev_valid,
            status=STATUS_FAILED,
        )

    if ser["dropped_identities"] or not ser["parse_ok"] or ser["truncated"]:
        return NormalCartsSnapshotWriteDecision(
            allow_write=False,
            drop_stage="snapshot_write",
            reason="payload_truncated_or_invalid_json",
            parity=parity,
            keep_previous=prev_valid,
            status=STATUS_FAILED,
        )

    if parity["sent_log_missing"]:
        return NormalCartsSnapshotWriteDecision(
            allow_write=False,
            drop_stage="row_build",
            reason="sent_log_rows_missing",
            parity=parity,
            keep_previous=prev_valid,
            status=STATUS_FAILED,
        )

    if degraded and prev_valid and len(cand_sigs) < len(prev_sigs):
        return NormalCartsSnapshotWriteDecision(
            allow_write=False,
            drop_stage="row_build",
            reason="partial_build_regression",
            parity=parity,
            keep_previous=True,
            status=STATUS_FAILED,
        )

    if prev_valid and prev_sigs and cand_sigs and prev_sigs - cand_sigs:
        parity["lost_previous_identities"] = sorted(prev_sigs - cand_sigs)
        return NormalCartsSnapshotWriteDecision(
            allow_write=False,
            drop_stage="snapshot_write",
            reason="non_empty_regression",
            parity=parity,
            keep_previous=True,
            status=STATUS_FAILED,
        )

    clean = storage_payload
    return NormalCartsSnapshotWriteDecision(
        allow_write=True,
        drop_stage="included",
        reason="ok",
        payload_for_storage=clean,
        storage_json=ser["storage_json"],
        parity=parity,
        keep_previous=False,
        status=STATUS_ACTIVE,
    )


def build_canonical_normal_carts_payload(
    dash_store: Any,
) -> tuple[dict[str, Any], dict[str, Any], NormalCartsDashboardPerfMeta]:
    """Single canonical builder used for live API and snapshot persistence."""
    from services.normal_carts_dashboard_batch_v1 import (  # noqa: PLC0415
        build_normal_carts_dashboard_api_payload,
    )

    body, prof, perf = build_normal_carts_dashboard_api_payload(
        dash_store,
        page_limit=50,
        page_offset=0,
        debug_perf=False,
    )
    out = dict(body)
    from services.merchant_intelligence_v1 import (  # noqa: PLC0415
        ensure_normal_carts_merchant_intelligence_store_v1,
    )

    ensure_normal_carts_merchant_intelligence_store_v1(out)
    from services.merchant_value_composition_v1 import (  # noqa: PLC0415
        ensure_normal_carts_merchant_value_stories_v1,
    )

    ensure_normal_carts_merchant_value_stories_v1(out)
    try:
        from services.cart_page_primary_action_v1 import (  # noqa: PLC0415
            ensure_normal_carts_primary_action_v1,
        )

        ensure_normal_carts_primary_action_v1(out)
    except Exception:  # noqa: BLE001
        pass
    return out, dict(prof), perf


def build_and_guard_normal_carts_snapshot_write(
    *,
    store_slug: str,
    dash_store: Any,
) -> NormalCartsSnapshotWriteDecision:
    """Dual-build parity check then evaluate write guard."""
    live_payload, _prof_a, perf_a = build_canonical_normal_carts_payload(dash_store)
    candidate_payload, _prof_b, perf_b = build_canonical_normal_carts_payload(dash_store)
    perf = perf_b if perf_b.rows_built >= perf_a.rows_built else perf_a
    if perf_a.partial or perf_a.degraded:
        perf = perf_a
    return evaluate_normal_carts_snapshot_write(
        store_slug=store_slug,
        live_payload=live_payload,
        candidate_payload=candidate_payload,
        perf=perf,
    )


__all__ = [
    "NormalCartsSnapshotWriteDecision",
    "build_and_guard_normal_carts_snapshot_write",
    "build_canonical_normal_carts_payload",
    "compare_normal_carts_payload_parity",
    "evaluate_normal_carts_snapshot_write",
    "extract_row_parity_records",
    "row_identity_signature",
]
