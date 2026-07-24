# -*- coding: utf-8 -*-
"""
Governed historical input contract for WP-ET-10.6 materialization.

Eligible demo sources are normalized through Observation (never bypassed).
Non-demo stores are rejected. No Zid remapping. No fabricated Knowledge.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from services.evidence_truth.durable_shadow_store_v1 import (
    DEMO_STORE_SLUG,
    assert_demo_store_slug_v1,
)
from services.evidence_truth.observation_types_v1 import (
    CHANNEL_API,
    CHANNEL_WIDGET,
    RAW_KIND_CART_EVENT,
    RAW_KIND_PURCHASE,
    RAW_KIND_RECOVERY,
)

# Eligible source type ids (governed allowlist)
SOURCE_PURCHASE_TRUTH = "purchase_truth_record"
SOURCE_CART_RECOVERY_LOG = "cart_recovery_log"
SOURCE_ABANDONED_CART = "abandoned_cart"
SOURCE_VALIDATION_FIXTURE = "validation_fixture"

ELIGIBLE_SOURCE_TYPES_V1 = frozenset(
    {
        SOURCE_PURCHASE_TRUTH,
        SOURCE_CART_RECOVERY_LOG,
        SOURCE_ABANDONED_CART,
        SOURCE_VALIDATION_FIXTURE,
    }
)

REPLAY_POLICY_V1 = "idempotent_raw_ref_v1"
UNSUPPORTED_POLICY_V1 = "account_and_skip"
CONFLICT_POLICY_V1 = "fail_closed_identity"
INCOMPLETE_POLICY_V1 = "reject_at_observation"


@dataclass(frozen=True)
class MaterializationSourceCandidateV1:
    """One governed source record eligible for Observation ingress."""

    source_type: str
    source_id: str
    store_slug: str
    raw_kind: str
    source_channel: str
    dedupe_key: str
    observed_at: str
    payload: Mapping[str, Any]
    timestamp_authority: str = "platform_record"
    replay_policy: str = REPLAY_POLICY_V1
    lineage: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "store_slug": self.store_slug,
            "raw_kind": self.raw_kind,
            "source_channel": self.source_channel,
            "dedupe_key": self.dedupe_key,
            "observed_at": self.observed_at,
            "timestamp_authority": self.timestamp_authority,
            "replay_policy": self.replay_policy,
            "payload": dict(self.payload or {}),
            "lineage": dict(self.lineage or {}),
        }


@dataclass
class MaterializationDiscoveryReportV1:
    store_slug: str
    discovered: int = 0
    eligible: list[MaterializationSourceCandidateV1] = field(default_factory=list)
    unsupported: list[dict[str, Any]] = field(default_factory=list)
    duplicated: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "store_slug": self.store_slug,
            "discovered": self.discovered,
            "eligible_count": len(self.eligible),
            "unsupported_count": len(self.unsupported),
            "duplicated_count": len(self.duplicated),
            "rejected_count": len(self.rejected),
            "eligible": [c.to_dict() for c in self.eligible],
            "unsupported": list(self.unsupported),
            "duplicated": list(self.duplicated),
            "rejected": list(self.rejected),
            "contract": {
                "eligible_source_types": sorted(ELIGIBLE_SOURCE_TYPES_V1),
                "replay_policy": REPLAY_POLICY_V1,
                "unsupported_policy": UNSUPPORTED_POLICY_V1,
                "conflict_policy": CONFLICT_POLICY_V1,
                "incomplete_policy": INCOMPLETE_POLICY_V1,
                "observation_required": True,
                "bypass_evidence_forbidden": True,
                "demo_only": True,
                "zid_remap_forbidden": True,
            },
        }


def _iso(dt: Any) -> str:
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    if isinstance(dt, str) and dt.strip():
        return dt.strip()
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validation_fixture_candidates_v1(
    *,
    store_slug: str = DEMO_STORE_SLUG,
    count: int = 2,
) -> list[MaterializationSourceCandidateV1]:
    """Deterministic fixtures that still pass through the real pipeline."""
    slug = assert_demo_store_slug_v1(store_slug)
    out: list[MaterializationSourceCandidateV1] = []
    n = max(1, min(int(count), 10))
    for i in range(n):
        sid = f"fixture_purchase_{i+1}"
        rk = f"{slug}:mat_fixture:{i+1}"
        payload = {
            "store_slug": slug,
            "recovery_key": rk,
            "session_id": f"mat_fixture_session_{i+1}",
            "cart_id": f"mat_fixture_cart_{i+1}",
            "purchase_completed": True,
            "observed_at": f"2026-07-01T12:{i:02d}:00+00:00",
            "materialization_fixture": True,
        }
        out.append(
            MaterializationSourceCandidateV1(
                source_type=SOURCE_VALIDATION_FIXTURE,
                source_id=sid,
                store_slug=slug,
                raw_kind=RAW_KIND_PURCHASE,
                source_channel=CHANNEL_API,
                dedupe_key=f"{SOURCE_VALIDATION_FIXTURE}:{sid}",
                observed_at=str(payload["observed_at"]),
                payload=payload,
                lineage={
                    "source_type": SOURCE_VALIDATION_FIXTURE,
                    "source_id": sid,
                    "fixture": True,
                },
            )
        )
        # Pair with a cart abandon signal for richer Bundle family presence
        cart_sid = f"fixture_cart_{i+1}"
        cart_payload = {
            "store_slug": slug,
            "session_id": f"mat_fixture_session_{i+1}",
            "cart_id": f"mat_fixture_cart_{i+1}",
            "event": "cart_abandoned",
            "observed_at": f"2026-07-01T11:{i:02d}:00+00:00",
            "materialization_fixture": True,
        }
        out.append(
            MaterializationSourceCandidateV1(
                source_type=SOURCE_VALIDATION_FIXTURE,
                source_id=cart_sid,
                store_slug=slug,
                raw_kind=RAW_KIND_CART_EVENT,
                source_channel=CHANNEL_WIDGET,
                dedupe_key=f"{SOURCE_VALIDATION_FIXTURE}:{cart_sid}",
                observed_at=str(cart_payload["observed_at"]),
                payload=cart_payload,
                lineage={
                    "source_type": SOURCE_VALIDATION_FIXTURE,
                    "source_id": cart_sid,
                    "fixture": True,
                },
            )
        )
    return out


def discover_materialization_sources_v1(
    *,
    store_slug: str,
    batch_limit: int = 50,
    include_validation_fixtures: bool = False,
    fixture_count: int = 2,
) -> MaterializationDiscoveryReportV1:
    """
    Discover bounded eligible source records for demo materialization.

    Does not write. Does not scan unbounded history (ORDER BY id DESC + LIMIT).
    """
    from extensions import db
    from models import AbandonedCart, CartRecoveryLog, PurchaseTruthRecord, StoreIdentityAlias

    slug = assert_demo_store_slug_v1(store_slug)
    limit = max(1, min(int(batch_limit), 500))
    report = MaterializationDiscoveryReportV1(store_slug=slug)
    seen_dedupe: set[str] = set()
    eligible: list[MaterializationSourceCandidateV1] = []

    def _accept(cand: MaterializationSourceCandidateV1) -> None:
        nonlocal eligible
        report.discovered += 1
        if cand.store_slug != DEMO_STORE_SLUG:
            report.rejected.append(
                {
                    "source_type": cand.source_type,
                    "source_id": cand.source_id,
                    "reason": "non_demo_store_forbidden",
                    "store_slug": cand.store_slug,
                }
            )
            return
        if cand.source_type not in ELIGIBLE_SOURCE_TYPES_V1:
            report.unsupported.append(
                {
                    "source_type": cand.source_type,
                    "source_id": cand.source_id,
                    "reason": "unsupported_source_type",
                }
            )
            return
        if cand.dedupe_key in seen_dedupe:
            report.duplicated.append(
                {
                    "source_type": cand.source_type,
                    "source_id": cand.source_id,
                    "dedupe_key": cand.dedupe_key,
                    "reason": "duplicate_dedupe_key",
                }
            )
            return
        if not cand.payload.get("store_slug"):
            report.rejected.append(
                {
                    "source_type": cand.source_type,
                    "source_id": cand.source_id,
                    "reason": "incomplete_store_slug",
                }
            )
            return
        seen_dedupe.add(cand.dedupe_key)
        eligible.append(cand)

    # 1) Purchase Truth (canonical commerce purchase evidence)
    try:
        rows = (
            db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.store_slug == slug)
            .order_by(PurchaseTruthRecord.id.desc())
            .limit(limit)
            .all()
        )
    except Exception:  # noqa: BLE001
        db.session.rollback()
        rows = []
    for row in rows:
        rk = str(row.recovery_key or "").strip()
        if not rk:
            report.discovered += 1
            report.rejected.append(
                {
                    "source_type": SOURCE_PURCHASE_TRUTH,
                    "source_id": str(row.id),
                    "reason": "incomplete_recovery_key",
                }
            )
            continue
        payload = {
            "store_slug": slug,
            "recovery_key": rk,
            "session_id": str(row.session_id or ""),
            "cart_id": str(row.cart_id or "") or None,
            "purchase_completed": True,
            "order_id": str(row.order_id or "") or None,
            "purchase_source": str(row.purchase_source or ""),
            "observed_at": _iso(row.purchase_time or row.created_at),
        }
        _accept(
            MaterializationSourceCandidateV1(
                source_type=SOURCE_PURCHASE_TRUTH,
                source_id=str(row.id),
                store_slug=slug,
                raw_kind=RAW_KIND_PURCHASE,
                source_channel=CHANNEL_API,
                dedupe_key=f"{SOURCE_PURCHASE_TRUTH}:{row.id}",
                observed_at=str(payload["observed_at"]),
                payload=payload,
                lineage={
                    "source_type": SOURCE_PURCHASE_TRUTH,
                    "source_id": str(row.id),
                    "recovery_key": rk,
                    "purchase_source": str(row.purchase_source or ""),
                },
            )
        )

    # 2) Cart recovery logs (demo only)
    remaining = max(0, limit - len(eligible))
    if remaining:
        try:
            logs = (
                db.session.query(CartRecoveryLog)
                .filter(CartRecoveryLog.store_slug == slug)
                .order_by(CartRecoveryLog.id.desc())
                .limit(remaining)
                .all()
            )
        except Exception:  # noqa: BLE001
            db.session.rollback()
            logs = []
        for row in logs:
            sid = str(row.session_id or "").strip()
            rk = str(row.recovery_key or "").strip() or (
                f"{slug}:{sid}" if sid else ""
            )
            if not rk and not sid:
                report.discovered += 1
                report.rejected.append(
                    {
                        "source_type": SOURCE_CART_RECOVERY_LOG,
                        "source_id": str(row.id),
                        "reason": "incomplete_identity",
                    }
                )
                continue
            payload = {
                "store_slug": slug,
                "recovery_key": rk,
                "session_id": sid,
                "cart_id": str(row.cart_id or "") or None,
                "status": str(row.status or ""),
                "timeline_status": str(row.status or ""),
                "step": row.step,
                "message_sid": str(row.provider_message_sid or "") or None,
                "observed_at": _iso(row.created_at or row.sent_at),
            }
            _accept(
                MaterializationSourceCandidateV1(
                    source_type=SOURCE_CART_RECOVERY_LOG,
                    source_id=str(row.id),
                    store_slug=slug,
                    raw_kind=RAW_KIND_RECOVERY,
                    source_channel=CHANNEL_API,
                    dedupe_key=f"{SOURCE_CART_RECOVERY_LOG}:{row.id}",
                    observed_at=str(payload["observed_at"]),
                    payload=payload,
                    lineage={
                        "source_type": SOURCE_CART_RECOVERY_LOG,
                        "source_id": str(row.id),
                        "recovery_key": rk,
                    },
                )
            )

    # 3) Abandoned carts linked to demo via identity alias (no Zid remap)
    remaining = max(0, limit - len(eligible))
    if remaining:
        demo_store_ids: list[int] = []
        try:
            aliases = (
                db.session.query(StoreIdentityAlias)
                .filter(StoreIdentityAlias.alias_value == slug)
                .limit(20)
                .all()
            )
            demo_store_ids = [int(a.store_id) for a in aliases if a.store_id]
        except Exception:  # noqa: BLE001
            db.session.rollback()
            demo_store_ids = []
        carts: list[Any] = []
        if demo_store_ids:
            try:
                carts = (
                    db.session.query(AbandonedCart)
                    .filter(AbandonedCart.store_id.in_(demo_store_ids))
                    .order_by(AbandonedCart.id.desc())
                    .limit(remaining)
                    .all()
                )
            except Exception:  # noqa: BLE001
                db.session.rollback()
                carts = []
        for row in carts:
            session = str(row.recovery_session_id or "").strip()
            cart_id = str(row.zid_cart_id or "").strip()
            # Prefer payload store_slug when present; else require demo alias path
            payload_slug = slug
            raw = {}
            if row.raw_payload:
                try:
                    loaded = json.loads(row.raw_payload)
                    if isinstance(loaded, dict):
                        raw = loaded
                        ps = str(
                            loaded.get("store_slug")
                            or loaded.get("store")
                            or ""
                        ).strip().lower()
                        if ps and ps != DEMO_STORE_SLUG:
                            report.discovered += 1
                            report.rejected.append(
                                {
                                    "source_type": SOURCE_ABANDONED_CART,
                                    "source_id": str(row.id),
                                    "reason": "non_demo_payload_store_slug",
                                    "store_slug": ps,
                                }
                            )
                            continue
                        if ps:
                            payload_slug = ps
                except json.JSONDecodeError:
                    raw = {}
            if not session and not cart_id:
                report.discovered += 1
                report.rejected.append(
                    {
                        "source_type": SOURCE_ABANDONED_CART,
                        "source_id": str(row.id),
                        "reason": "incomplete_identity",
                    }
                )
                continue
            payload = {
                "store_slug": payload_slug,
                "session_id": session or None,
                "cart_id": cart_id or None,
                "event": "cart_abandoned",
                "observed_at": _iso(row.first_seen_at or row.last_seen_at),
                "status": str(row.status or ""),
            }
            if isinstance(raw.get("lines"), list):
                payload["lines"] = raw.get("lines")
            _accept(
                MaterializationSourceCandidateV1(
                    source_type=SOURCE_ABANDONED_CART,
                    source_id=str(row.id),
                    store_slug=payload_slug,
                    raw_kind=RAW_KIND_CART_EVENT,
                    source_channel=CHANNEL_WIDGET,
                    dedupe_key=f"{SOURCE_ABANDONED_CART}:{row.id}",
                    observed_at=str(payload["observed_at"]),
                    payload=payload,
                    lineage={
                        "source_type": SOURCE_ABANDONED_CART,
                        "source_id": str(row.id),
                        "zid_cart_id": cart_id,
                    },
                )
            )

    # 4) Deterministic validation fixtures (explicit opt-in only)
    if include_validation_fixtures:
        for cand in validation_fixture_candidates_v1(
            store_slug=slug, count=fixture_count
        ):
            _accept(cand)

    # Bound eligible list — overflow accounted as duplicated (batch bound)
    report.eligible = eligible[:limit]
    for cand in eligible[limit:]:
        report.duplicated.append(
            {
                "source_type": cand.source_type,
                "source_id": cand.source_id,
                "reason": "batch_limit_overflow",
                "dedupe_key": cand.dedupe_key,
            }
        )

    accounted = (
        len(report.eligible)
        + len(report.unsupported)
        + len(report.duplicated)
        + len(report.rejected)
    )
    if accounted != report.discovered:
        report.rejected.append(
            {
                "reason": "accounting_imbalance",
                "discovered": report.discovered,
                "accounted": accounted,
            }
        )
    return report


__all__ = [
    "ELIGIBLE_SOURCE_TYPES_V1",
    "MaterializationDiscoveryReportV1",
    "MaterializationSourceCandidateV1",
    "SOURCE_ABANDONED_CART",
    "SOURCE_CART_RECOVERY_LOG",
    "SOURCE_PURCHASE_TRUTH",
    "SOURCE_VALIDATION_FIXTURE",
    "discover_materialization_sources_v1",
    "validation_fixture_candidates_v1",
]
