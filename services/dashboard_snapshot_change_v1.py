# -*- coding: utf-8 -*-
"""
Snapshot semantic change detection + generation gate v1.

Implements Snapshot Generation Governance v1 (docs/snapshot_generation_governance_v1.md):

  SG-1  Generation follows change (a scheduler tick triggers a *check*, never a
        *write* by itself).
  SG-2  No identical rewrite (fingerprint gate at the production write point).
  SG-5  Per-type generation policy (independently configurable).
  SG-6  Fingerprint over a canonical semantic projection that excludes volatile,
        non-semantic fields (timestamps, relative "time ago", live countdowns,
        counter generation metadata, freshness age).
  SG-7  Schedule is a failsafe: when content is unchanged but the latest row is
        stale, freshness is refreshed in place instead of appending a new row.
  SG-9  Derived snapshots are not independently generated (handled by the builder
        for ``dashboard_cards`` ⊂ ``summary``).
  SG-10 Change detection is cheaper than the build it gates (hash of an
        already-built payload; no extra queries).

No merchant-visible behavior change: reads always fetch the latest row per
``(store_slug, snapshot_type)`` and see identical content; freshness is
preserved via in-place touch.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from services.dashboard_snapshot_generation_metrics_v1 import (
    MODE_SKIP,
    MODE_TOUCH,
    MODE_WRITE,
    record_generation_decision,
)
from services.dashboard_snapshot_v1 import (
    SNAPSHOT_TYPE_ABANDONED_CANDIDATES,
    SNAPSHOT_TYPE_DASHBOARD_CARDS,
    SNAPSHOT_TYPE_MONTHLY_SUMMARY,
    SNAPSHOT_TYPE_NORMAL_CARTS,
    SNAPSHOT_TYPE_REFRESH_STATE,
    SNAPSHOT_TYPE_STORE_CONNECTION,
    SNAPSHOT_TYPE_SUMMARY,
    SNAPSHOT_TYPE_WHATSAPP_READINESS,
    SNAPSHOT_TYPE_WIDGET_PANEL,
    STATUS_ACTIVE,
    decode_snapshot_payload,
    fetch_latest_snapshot_row,
    snapshot_row_is_stale,
    snapshot_ttl_seconds,
    touch_dashboard_snapshot_freshness,
    upsert_dashboard_snapshot,
)
from models import DashboardSnapshot

# ---------------------------------------------------------------------------
# SG-6 — volatile fields excluded from the semantic fingerprint.
#
# These are per-build / relative-to-now fields whose change carries no meaning
# for the merchant read: excluding them is what makes "fingerprint unchanged"
# mean "the merchant sees the same thing". Changing this set is a governed
# decision (SG-12) — it is documented in the governance file's §4.3.
#
# Verified against the six builder payloads:
#   summary / normal_carts : merchant_counter_health.{counter_generated_at,
#                            counter_snapshot_age_seconds},
#                            merchant_counter_generated_at
#   normal_carts rows      : merchant_time_relative_ar (relative "time ago"),
#                            merchant_followup_next_line_ar (live countdown)
# Absolute timestamps that only change on real events (connected_at_ar,
# merchant_last_seen_display, next_attempt_due_at, widget_last_seen_at_ar) are
# intentionally KEPT so genuine changes still trigger a write.
# ---------------------------------------------------------------------------
VOLATILE_SNAPSHOT_KEYS: frozenset[str] = frozenset(
    {
        # generation / freshness metadata
        "generated_at",
        "merchant_counter_generated_at",
        "counter_generated_at",
        "counter_snapshot_age_seconds",
        "snapshot_generated_at",
        "data_freshness_seconds",
        "measured_at",
        "server_time",
        "as_of",
        "as_of_iso",
        "now_iso",
        "now_utc",
        "uptime_seconds",
        "elapsed_ms",
        "duration_ms",
        "seconds_ago",
        "age_seconds",
        # relative-to-now display strings (absolute counterparts are kept)
        "merchant_time_relative_ar",
        "merchant_followup_next_line_ar",
    }
)


def _canonicalize(obj: Any) -> Any:
    """Recursively drop volatile keys; preserve list order and scalar values."""
    if isinstance(obj, dict):
        return {
            k: _canonicalize(v)
            for k, v in obj.items()
            if k not in VOLATILE_SNAPSHOT_KEYS
        }
    if isinstance(obj, (list, tuple)):
        return [_canonicalize(v) for v in obj]
    return obj


def semantic_snapshot_fingerprint(
    payload: dict[str, Any],
    *,
    snapshot_type: str,
) -> str:
    """
    Stable SHA-256 over the canonical semantic projection of a payload.

    Equal fingerprint ⇔ the merchant read would return the same content.
    """
    canon = _canonicalize(payload if isinstance(payload, dict) else {})
    blob = json.dumps(
        canon,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# SG-5 / SG-11 — per-type generation policy (source of truth mirrors §3).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SnapshotGenerationPolicy:
    snapshot_type: str
    importance: str            # critical / operational / informational
    trigger_mode: str          # event / schedule / hybrid
    change_gate_enabled: bool  # apply the SG-2 identical-rewrite gate
    freshness_touch_enabled: bool  # SG-7 in-place touch when stale + unchanged
    max_staleness_s: int
    failsafe_age_s: int
    derived_from: Optional[str] = None  # SG-9 source type for derived snapshots


_POLICIES: dict[str, SnapshotGenerationPolicy] = {
    SNAPSHOT_TYPE_NORMAL_CARTS: SnapshotGenerationPolicy(
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        importance="critical",
        trigger_mode="hybrid",
        change_gate_enabled=True,
        freshness_touch_enabled=True,
        max_staleness_s=45,
        failsafe_age_s=300,
    ),
    SNAPSHOT_TYPE_SUMMARY: SnapshotGenerationPolicy(
        snapshot_type=SNAPSHOT_TYPE_SUMMARY,
        importance="critical",
        trigger_mode="hybrid",
        change_gate_enabled=True,
        freshness_touch_enabled=True,
        max_staleness_s=60,
        failsafe_age_s=300,
    ),
    SNAPSHOT_TYPE_DASHBOARD_CARDS: SnapshotGenerationPolicy(
        snapshot_type=SNAPSHOT_TYPE_DASHBOARD_CARDS,
        importance="operational",
        trigger_mode="hybrid",
        change_gate_enabled=True,
        freshness_touch_enabled=True,
        max_staleness_s=60,
        failsafe_age_s=300,
        derived_from=SNAPSHOT_TYPE_SUMMARY,
    ),
    SNAPSHOT_TYPE_REFRESH_STATE: SnapshotGenerationPolicy(
        snapshot_type=SNAPSHOT_TYPE_REFRESH_STATE,
        importance="operational",
        trigger_mode="event",
        change_gate_enabled=True,
        freshness_touch_enabled=True,
        max_staleness_s=30,
        failsafe_age_s=300,
    ),
    SNAPSHOT_TYPE_WIDGET_PANEL: SnapshotGenerationPolicy(
        snapshot_type=SNAPSHOT_TYPE_WIDGET_PANEL,
        importance="informational",
        trigger_mode="event",
        change_gate_enabled=True,
        freshness_touch_enabled=True,
        max_staleness_s=60,
        failsafe_age_s=900,
    ),
    SNAPSHOT_TYPE_STORE_CONNECTION: SnapshotGenerationPolicy(
        snapshot_type=SNAPSHOT_TYPE_STORE_CONNECTION,
        importance="informational",
        trigger_mode="event",
        change_gate_enabled=True,
        freshness_touch_enabled=True,
        max_staleness_s=120,
        failsafe_age_s=900,
    ),
    SNAPSHOT_TYPE_WHATSAPP_READINESS: SnapshotGenerationPolicy(
        snapshot_type=SNAPSHOT_TYPE_WHATSAPP_READINESS,
        importance="operational",
        trigger_mode="event",
        change_gate_enabled=True,
        freshness_touch_enabled=True,
        max_staleness_s=60,
        failsafe_age_s=900,
    ),
    SNAPSHOT_TYPE_MONTHLY_SUMMARY: SnapshotGenerationPolicy(
        snapshot_type=SNAPSHOT_TYPE_MONTHLY_SUMMARY,
        importance="operational",
        trigger_mode="hybrid",
        change_gate_enabled=True,
        freshness_touch_enabled=True,
        max_staleness_s=120,
        failsafe_age_s=1800,
    ),
    SNAPSHOT_TYPE_ABANDONED_CANDIDATES: SnapshotGenerationPolicy(
        snapshot_type=SNAPSHOT_TYPE_ABANDONED_CANDIDATES,
        importance="operational",
        trigger_mode="event",
        change_gate_enabled=True,
        freshness_touch_enabled=True,
        max_staleness_s=45,
        failsafe_age_s=300,
    ),
}

_DEFAULT_POLICY = SnapshotGenerationPolicy(
    snapshot_type="_default",
    importance="operational",
    trigger_mode="hybrid",
    change_gate_enabled=True,
    freshness_touch_enabled=True,
    max_staleness_s=60,
    failsafe_age_s=300,
)


def generation_policy_for(snapshot_type: str) -> SnapshotGenerationPolicy:
    return _POLICIES.get((snapshot_type or "").strip(), _DEFAULT_POLICY)


def _env_flag(name: str) -> Optional[bool]:
    raw = (os.environ.get(name) or "").strip().lower()
    if raw == "":
        return None
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return None


def change_gate_enabled_for(snapshot_type: str) -> bool:
    """
    Per-type SG-2 gate enablement with env kill-switches (reversible per §7).

    Precedence: per-type env > global env > policy default.
      CARTFLOW_SNAPSHOT_CHANGE_GATE            (global)
      CARTFLOW_SNAPSHOT_CHANGE_GATE_<TYPE>     (per type)
    """
    stype = (snapshot_type or "").strip()
    per_type = _env_flag(f"CARTFLOW_SNAPSHOT_CHANGE_GATE_{stype.upper()}")
    if per_type is not None:
        return per_type
    global_flag = _env_flag("CARTFLOW_SNAPSHOT_CHANGE_GATE")
    if global_flag is not None:
        return global_flag
    return generation_policy_for(stype).change_gate_enabled


@dataclass
class SnapshotWriteOutcome:
    mode: str                     # write / touch / skip
    reason: str                   # SG-4 generation reason
    snapshot_type: str
    changed: bool                 # content differed from previous latest row
    change_checked: bool          # gate ran a fingerprint comparison
    fingerprint: str
    row: Optional[DashboardSnapshot] = None

    @property
    def wrote_new_row(self) -> bool:
        return self.mode == MODE_WRITE


def write_dashboard_snapshot_guarded(
    *,
    store_id: Optional[int],
    store_slug: str,
    snapshot_type: str,
    payload: dict[str, Any],
    payload_json: Optional[str] = None,
    status: str = STATUS_ACTIVE,
    ttl_seconds: Optional[int] = None,
    apply_change_gate: Optional[bool] = None,
) -> SnapshotWriteOutcome:
    """
    Governed snapshot generation — the single production write path (SG-1/2/6/7).

    Decision:
      * no gate / no previous row      -> WRITE (append; reason first_build)
      * fingerprint differs            -> WRITE (append; reason content_change)
      * identical + latest row stale   -> TOUCH (in-place freshness; SG-7)
      * identical + latest row fresh    -> SKIP  (no write at all; SG-2)
    """
    stype = (snapshot_type or "").strip()

    # Semantic fingerprint of the payload that would actually be stored.
    if payload_json is not None:
        try:
            stored = json.loads(payload_json)
            if not isinstance(stored, dict):
                stored = {}
        except (TypeError, ValueError, json.JSONDecodeError):
            stored = {}
    else:
        stored = payload if isinstance(payload, dict) else {}
    cand_fp = semantic_snapshot_fingerprint(stored, snapshot_type=stype)

    gate_on = (
        change_gate_enabled_for(stype)
        if apply_change_gate is None
        else bool(apply_change_gate)
    )
    prev = fetch_latest_snapshot_row(store_slug=store_slug, snapshot_type=stype)

    def _finish(mode: str, reason: str, changed: bool, checked: bool,
                row: Optional[DashboardSnapshot]) -> SnapshotWriteOutcome:
        record_generation_decision(
            snapshot_type=stype,
            mode=mode,
            reason=reason,
            change_checked=checked,
            content_changed=changed,
        )
        return SnapshotWriteOutcome(
            mode=mode,
            reason=reason,
            snapshot_type=stype,
            changed=changed,
            change_checked=checked,
            fingerprint=cand_fp,
            row=row,
        )

    if stype == SNAPSHOT_TYPE_SUMMARY and prev is not None:
        from services.merchant_home_experience_activation_v1 import (  # noqa: PLC0415
            summary_snapshot_contract_stale,
        )

        prev_payload = decode_snapshot_payload(prev)
        if summary_snapshot_contract_stale(prev_payload):
            row = upsert_dashboard_snapshot(
                store_id=store_id,
                store_slug=store_slug,
                snapshot_type=stype,
                payload=payload,
                payload_json=payload_json,
                status=status,
                ttl_seconds=ttl_seconds,
                generation_reason="summary_contract_upgrade",
            )
            return _finish(
                MODE_WRITE,
                "summary_contract_upgrade",
                changed=True,
                checked=True,
                row=row,
            )

    if not gate_on:
        row = upsert_dashboard_snapshot(
            store_id=store_id,
            store_slug=store_slug,
            snapshot_type=stype,
            payload=payload,
            payload_json=payload_json,
            status=status,
            ttl_seconds=ttl_seconds,
            generation_reason="gate_disabled",
        )
        return _finish(MODE_WRITE, "gate_disabled", changed=True, checked=False, row=row)

    if prev is None:
        row = upsert_dashboard_snapshot(
            store_id=store_id,
            store_slug=store_slug,
            snapshot_type=stype,
            payload=payload,
            payload_json=payload_json,
            status=status,
            ttl_seconds=ttl_seconds,
            generation_reason="first_build",
        )
        return _finish(MODE_WRITE, "first_build", changed=True, checked=False, row=row)

    prev_fp = semantic_snapshot_fingerprint(
        decode_snapshot_payload(prev), snapshot_type=stype
    )

    if cand_fp != prev_fp:
        row = upsert_dashboard_snapshot(
            store_id=store_id,
            store_slug=store_slug,
            snapshot_type=stype,
            payload=payload,
            payload_json=payload_json,
            status=status,
            ttl_seconds=ttl_seconds,
            generation_reason="content_change",
        )
        return _finish(MODE_WRITE, "content_change", changed=True, checked=True, row=row)

    # Identical content — no new version.
    policy = generation_policy_for(stype)
    if policy.freshness_touch_enabled and snapshot_row_is_stale(prev):
        touched = touch_dashboard_snapshot_freshness(
            prev, ttl_seconds=ttl_seconds, status=status
        )
        return _finish(MODE_TOUCH, "failsafe_touch", changed=False, checked=True, row=touched)

    return _finish(MODE_SKIP, "identical_skip", changed=False, checked=True, row=prev)


__all__ = [
    "SnapshotGenerationPolicy",
    "SnapshotWriteOutcome",
    "VOLATILE_SNAPSHOT_KEYS",
    "change_gate_enabled_for",
    "generation_policy_for",
    "semantic_snapshot_fingerprint",
    "write_dashboard_snapshot_guarded",
]
