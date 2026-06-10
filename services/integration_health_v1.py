# -*- coding: utf-8 -*-
"""
Integration Health Foundation v1 — single read-only composer.

Composes existing truth providers only (IH-C1). No parallel truth, no writes.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import (
    AbandonedCart,
    CartLineSnapshot,
    CartRecoveryReason,
    PurchaseTruthRecord,
    RecoveryEvent,
    RecoveryTruthTimelineEvent,
    Store,
)
from services.merchant_store_connection_v1 import is_merchant_store_platform_connected

VERSION = "integration_health_v1"
INTEGRATION_PATH_LEGACY_ZID = "legacy_zid"
INTEGRATION_PATH_ADAPTER_SCAFFOLD = "adapter_scaffold_only"
INTEGRATION_PATH_NOT_IMPLEMENTED = "not_implemented"

# --- Approved diagnosis codes (v1) ---
DIAG_ZID_NOT_CONNECTED = "zid_not_connected"
DIAG_ZID_OAUTH_MISSING = "zid_oauth_missing"
DIAG_ZID_OAUTH_EXPIRED = "zid_oauth_expired"
DIAG_ZID_WEBHOOK_STALE = "zid_webhook_stale"
DIAG_ZID_WEBHOOK_SIGNATURE_MISCONFIGURED = "zid_webhook_signature_misconfigured"
DIAG_ZID_CART_EVENTS_MISSING = "zid_cart_events_missing"
DIAG_ZID_PURCHASE_EVENTS_MISSING = "zid_purchase_events_missing"
DIAG_ZID_WIDGET_PENDING_PARTNER = "zid_widget_pending_partner_snippet"
DIAG_ZID_WIDGET_INSTALL_FAILED = "zid_widget_install_failed"

DIAG_WIDGET_RUNTIME_MISSING = "widget_runtime_missing"
DIAG_WIDGET_NOT_SEEN = "widget_not_seen"
DIAG_WIDGET_IDENTITY_LINES_MISSING = "widget_identity_lines_missing"
DIAG_WIDGET_SETTINGS_MISMATCH = "widget_settings_mismatch"
DIAG_STORE_IDENTITY_MISMATCH = "store_identity_mismatch"

DIAG_WHATSAPP_PROVIDER_MISSING = "whatsapp_provider_missing"
DIAG_WHATSAPP_MERCHANT_NOT_CONNECTED = "whatsapp_merchant_not_connected"
DIAG_WHATSAPP_TEMPLATE_NOT_READY = "whatsapp_template_not_ready"
DIAG_META_PRODUCTION_BLOCKED = "meta_production_blocked"
DIAG_WHATSAPP_WEBHOOK_STALE = "whatsapp_webhook_stale"

DIAG_PLATFORM_ADAPTER_SCAFFOLD = "platform_adapter_scaffold_only"
DIAG_PAYMENT_SIGNAL_MISSING = "payment_signal_missing"
DIAG_CHECKOUT_SIGNAL_MISSING = "checkout_signal_missing"
DIAG_PROVIDER_UNAVAILABLE = "provider_unavailable"
DIAG_PROVIDER_RATE_LIMITED = "provider_rate_limited"

STATUS_HEALTHY = "healthy"
STATUS_DEGRADED = "degraded"
STATUS_DISCONNECTED = "disconnected"
STATUS_MISCONFIGURED = "misconfigured"
STATUS_STALE = "stale"
STATUS_UNKNOWN = "unknown"
STATUS_PROVIDER_UNAVAILABLE = "provider_unavailable"
STATUS_MERCHANT_ACTION_REQUIRED = "merchant_action_required"
STATUS_CARTFLOW_ACTION_REQUIRED = "cartflow_action_required"
STATUS_NOT_IMPLEMENTED = "not_implemented"
STATUS_PRODUCTION_BLOCKED = "production_blocked"

_CHECKOUT_HINTS = frozenset(
    {"checkout_started", "checkout_push", "ready_for_checkout"}
)

_WIDGET_ISSUE_TO_DIAG: dict[str, str] = {
    "runtime_beacon_missing": DIAG_WIDGET_RUNTIME_MISSING,
    "widget_not_seen": DIAG_WIDGET_NOT_SEEN,
    "widget_settings_mismatch": DIAG_WIDGET_SETTINGS_MISMATCH,
    "store_identity_mismatch": DIAG_STORE_IDENTITY_MISMATCH,
}

_STATUS_RANK = {
    STATUS_UNKNOWN: 0,
    STATUS_HEALTHY: 1,
    STATUS_PRODUCTION_BLOCKED: 2,
    STATUS_NOT_IMPLEMENTED: 3,
    STATUS_STALE: 4,
    STATUS_DEGRADED: 5,
    STATUS_MERCHANT_ACTION_REQUIRED: 6,
    STATUS_MISCONFIGURED: 7,
    STATUS_DISCONNECTED: 8,
    STATUS_PROVIDER_UNAVAILABLE: 9,
    STATUS_CARTFLOW_ACTION_REQUIRED: 10,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        d = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat()
    return None


def _store_slug(store: Any) -> str:
    return (getattr(store, "zid_store_id", None) or getattr(store, "slug", None) or "").strip()[:255]


def _integration_record(
    *,
    name: str,
    status: str,
    diagnosis_codes: list[str],
    action_owner: str,
    last_success_at: Optional[str] = None,
    last_failure_at: Optional[str] = None,
    evidence: Optional[dict[str, Any]] = None,
    health_source: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "diagnosis_codes": list(diagnosis_codes),
        "action_owner": action_owner,
        "last_success_at": last_success_at,
        "last_failure_at": last_failure_at,
        "evidence": dict(evidence or {}),
        "health_source": health_source,
    }


def _worst_status(*statuses: str) -> str:
    best = STATUS_HEALTHY
    best_rank = -1
    for st in statuses:
        rank = _STATUS_RANK.get(st, 0)
        if rank > best_rank:
            best_rank = rank
            best = st
    return best if statuses else STATUS_UNKNOWN


def _zid_webhook_secret_configured() -> bool:
    return bool((os.getenv("ZID_WEBHOOK_SECRET") or "").strip())


def _query_zid_webhook_timestamps(
    window_start: datetime,
) -> tuple[Optional[datetime], int]:
    try:
        count = (
            db.session.query(func.count(RecoveryEvent.id))
            .filter(
                RecoveryEvent.created_at >= window_start,
                RecoveryEvent.event_type.ilike("%zid%"),
            )
            .scalar()
            or 0
        )
        last_at = db.session.query(func.max(RecoveryEvent.created_at)).filter(
            RecoveryEvent.created_at >= window_start,
            RecoveryEvent.event_type.ilike("%zid%"),
        )
        last = last_at.scalar()
        return last, int(count)
    except SQLAlchemyError:
        db.session.rollback()
        return None, 0


def _query_store_activity(
    store: Store,
    *,
    slug: str,
    window_start: datetime,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "cart_event_count": 0,
        "last_cart_event_at": None,
        "purchase_count": 0,
        "last_purchase_at": None,
        "hesitation_count": 0,
        "checkout_signal_count": 0,
        "snapshot_rows": 0,
    }
    try:
        if store.id:
            out["cart_event_count"] = int(
                db.session.query(func.count(AbandonedCart.id))
                .filter(
                    AbandonedCart.store_id == store.id,
                    AbandonedCart.first_seen_at >= window_start,
                )
                .scalar()
                or 0
            )
            last_cart = (
                db.session.query(func.max(AbandonedCart.first_seen_at))
                .filter(AbandonedCart.store_id == store.id)
                .scalar()
            )
            out["last_cart_event_at"] = _iso(last_cart)
        if slug:
            out["purchase_count"] = int(
                db.session.query(func.count(PurchaseTruthRecord.id))
                .filter(
                    PurchaseTruthRecord.store_slug == slug,
                    PurchaseTruthRecord.purchase_time >= window_start,
                )
                .scalar()
                or 0
            )
            last_pt = (
                db.session.query(func.max(PurchaseTruthRecord.purchase_time))
                .filter(PurchaseTruthRecord.store_slug == slug)
                .scalar()
            )
            out["last_purchase_at"] = _iso(last_pt)
            out["hesitation_count"] = int(
                db.session.query(func.count(CartRecoveryReason.id))
                .filter(
                    CartRecoveryReason.store_slug == slug,
                    CartRecoveryReason.created_at >= window_start,
                )
                .scalar()
                or 0
            )
            out["checkout_signal_count"] = int(
                db.session.query(func.count(RecoveryTruthTimelineEvent.id))
                .filter(
                    RecoveryTruthTimelineEvent.store_slug == slug,
                    RecoveryTruthTimelineEvent.created_at >= window_start,
                    RecoveryTruthTimelineEvent.status.in_(tuple(_CHECKOUT_HINTS)),
                )
                .scalar()
                or 0
            )
            out["snapshot_rows"] = int(
                db.session.query(func.count(CartLineSnapshot.id))
                .filter(
                    CartLineSnapshot.store_slug == slug,
                    CartLineSnapshot.captured_at >= window_start,
                )
                .scalar()
                or 0
            )
    except SQLAlchemyError:
        db.session.rollback()
    return out


def _build_platform_zid_health(
    *,
    window_start: datetime,
    connected_store_count: int,
) -> dict[str, Any]:
    codes: list[str] = []
    action_owner = "unknown"
    status = STATUS_UNKNOWN
    evidence: dict[str, Any] = {"integration_path": INTEGRATION_PATH_LEGACY_ZID}

    webhook_last, webhook_count = _query_zid_webhook_timestamps(window_start)
    evidence["webhook_events_in_window"] = webhook_count
    evidence["webhook_secret_configured"] = _zid_webhook_secret_configured()

    if not _zid_webhook_secret_configured():
        codes.append(DIAG_ZID_WEBHOOK_SIGNATURE_MISCONFIGURED)
        status = STATUS_CARTFLOW_ACTION_REQUIRED
        action_owner = "cartflow"

    if connected_store_count == 0:
        codes.append(DIAG_ZID_NOT_CONNECTED)
        status = _worst_status(status, STATUS_DISCONNECTED)
        action_owner = "merchant"
    elif webhook_count == 0:
        codes.append(DIAG_ZID_WEBHOOK_STALE)
        status = _worst_status(status, STATUS_STALE)

    if not codes:
        status = STATUS_HEALTHY
        action_owner = "none"

    return _integration_record(
        name="zid",
        status=status,
        diagnosis_codes=codes,
        action_owner=action_owner,
        last_success_at=_iso(webhook_last),
        last_failure_at=None,
        evidence=evidence,
        health_source=INTEGRATION_PATH_LEGACY_ZID,
    )


def _build_store_zid_health(
    store: Store,
    *,
    window_start: datetime,
    widget_row: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    slug = _store_slug(store)
    codes: list[str] = []
    action_owner = "unknown"
    status = STATUS_UNKNOWN
    connected = is_merchant_store_platform_connected(store)
    activity = _query_store_activity(store, slug=slug, window_start=window_start)

    widget_status = (getattr(store, "widget_installation_status", None) or "").strip()
    evidence: dict[str, Any] = {
        "integration_path": INTEGRATION_PATH_LEGACY_ZID,
        "store_slug": slug,
        "connected": connected,
        "widget_installation_status": widget_status or None,
        **activity,
    }

    last_success_candidates: list[Optional[str]] = []
    if activity.get("last_cart_event_at"):
        last_success_candidates.append(str(activity["last_cart_event_at"]))
    if activity.get("last_purchase_at"):
        last_success_candidates.append(str(activity["last_purchase_at"]))

    if not connected:
        codes.append(DIAG_ZID_OAUTH_MISSING)
        status = STATUS_DISCONNECTED
        action_owner = "merchant"
    else:
        token_exp = getattr(store, "token_expires_at", None)
        if isinstance(token_exp, datetime) and token_exp.replace(tzinfo=timezone.utc) < _utc_now():
            codes.append(DIAG_ZID_OAUTH_EXPIRED)
            status = STATUS_DEGRADED
            action_owner = "merchant"

        if widget_status == "pending_partner_snippet":
            codes.append(DIAG_ZID_WIDGET_PENDING_PARTNER)
            status = _worst_status(status, STATUS_CARTFLOW_ACTION_REQUIRED)
            action_owner = "cartflow"
        elif widget_status == "failed":
            codes.append(DIAG_ZID_WIDGET_INSTALL_FAILED)
            status = _worst_status(status, STATUS_DEGRADED)
            action_owner = "merchant"

        if connected and activity["cart_event_count"] == 0:
            codes.append(DIAG_ZID_CART_EVENTS_MISSING)
            status = _worst_status(status, STATUS_STALE)
            action_owner = "merchant"

        if (
            connected
            and activity["cart_event_count"] > 0
            and activity["snapshot_rows"] == 0
        ):
            codes.append(DIAG_WIDGET_IDENTITY_LINES_MISSING)
            status = _worst_status(status, STATUS_DEGRADED)

        if widget_row:
            for kind in widget_row.get("issue_kinds") or []:
                diag = _WIDGET_ISSUE_TO_DIAG.get(str(kind))
                if diag and diag not in codes:
                    codes.append(diag)
            wh_status = str(widget_row.get("status") or "")
            if wh_status in ("warning", "critical"):
                status = _worst_status(status, STATUS_DEGRADED)
            elif wh_status == "healthy" and not codes:
                status = STATUS_HEALTHY

    if not codes and connected:
        status = STATUS_HEALTHY
        action_owner = "none"

    last_success = max((s for s in last_success_candidates if s), default=None)

    return _integration_record(
        name="zid",
        status=status,
        diagnosis_codes=codes,
        action_owner=action_owner,
        last_success_at=last_success,
        last_failure_at=None,
        evidence=evidence,
        health_source=INTEGRATION_PATH_LEGACY_ZID,
    )


def _build_scaffold_platform(name: str) -> dict[str, Any]:
    return _integration_record(
        name=name,
        status=STATUS_NOT_IMPLEMENTED,
        diagnosis_codes=[DIAG_PLATFORM_ADAPTER_SCAFFOLD],
        action_owner="none",
        last_success_at=None,
        last_failure_at=None,
        evidence={"implementation": INTEGRATION_PATH_ADAPTER_SCAFFOLD},
        health_source=INTEGRATION_PATH_ADAPTER_SCAFFOLD,
    )


def _build_whatsapp_architecture_health() -> dict[str, Any]:
    try:
        from services.cartflow_provider_readiness import (  # noqa: PLC0415
            FAILURE_PROVIDER_NOT_CONFIGURED,
            FAILURE_RATE_LIMITED,
            FAILURE_UNAVAILABLE,
            get_twilio_readiness,
            get_whatsapp_provider_readiness,
        )

        provider = get_whatsapp_provider_readiness()
        twilio = get_twilio_readiness()
    except Exception as exc:  # noqa: BLE001
        return _integration_record(
            name="whatsapp_architecture",
            status=STATUS_UNKNOWN,
            diagnosis_codes=[],
            action_owner="unknown",
            evidence={"error": str(exc)[:200]},
            health_source="cartflow_provider_readiness",
        )

    codes: list[str] = []
    fc = str(provider.get("failure_class") or "")
    twilio_ready = bool(twilio.get("ready") or twilio.get("ready_env_credentials"))
    status = STATUS_HEALTHY if twilio_ready else STATUS_DEGRADED
    action_owner = "cartflow"

    if fc == FAILURE_PROVIDER_NOT_CONFIGURED or not twilio.get("configured"):
        codes.append(DIAG_WHATSAPP_PROVIDER_MISSING)
        status = STATUS_MISCONFIGURED
    elif fc == FAILURE_RATE_LIMITED:
        codes.append(DIAG_PROVIDER_RATE_LIMITED)
        status = STATUS_PROVIDER_UNAVAILABLE
    elif fc == FAILURE_UNAVAILABLE:
        codes.append(DIAG_PROVIDER_UNAVAILABLE)
        status = STATUS_PROVIDER_UNAVAILABLE

    evidence = {
        "twilio_send_ready": twilio_ready,
        "provider": provider.get("provider"),
        "configured": provider.get("configured"),
        "ready": provider.get("ready"),
        "failure_class": fc,
        "mode": provider.get("mode"),
    }

    return _integration_record(
        name="whatsapp_architecture",
        status=status,
        diagnosis_codes=codes,
        action_owner=action_owner,
        last_success_at=None,
        last_failure_at=None,
        evidence=evidence,
        health_source="cartflow_provider_readiness",
    )


def _build_meta_production_health() -> dict[str, Any]:
    try:
        from services.cartflow_provider_readiness import get_meta_readiness  # noqa: PLC0415

        meta = get_meta_readiness()
    except Exception as exc:  # noqa: BLE001
        return _integration_record(
            name="meta_production",
            status=STATUS_UNKNOWN,
            diagnosis_codes=[],
            action_owner="unknown",
            evidence={"error": str(exc)[:200]},
            health_source="cartflow_provider_readiness",
        )

    # Meta approval pending is production_blocked — NOT provider failure (IH-C3).
    return _integration_record(
        name="meta_production",
        status=STATUS_PRODUCTION_BLOCKED,
        diagnosis_codes=[DIAG_META_PRODUCTION_BLOCKED],
        action_owner="cartflow",
        last_success_at=None,
        last_failure_at=None,
        evidence={
            "meta_production_approved": False,
            "meta_configured": bool(meta.get("configured")),
            "note": meta.get("note") or "meta_path_not_active",
        },
        health_source="cartflow_provider_readiness",
    )


def _build_store_whatsapp_health(store: Store) -> dict[str, Any]:
    try:
        from services.merchant_whatsapp_connection_readiness_v1 import (  # noqa: PLC0415
            CONNECTION_STATE_CONNECTED,
            evaluate_whatsapp_connection_readiness,
        )

        readiness = evaluate_whatsapp_connection_readiness(store)
    except Exception as exc:  # noqa: BLE001
        return _integration_record(
            name="whatsapp",
            status=STATUS_UNKNOWN,
            diagnosis_codes=[],
            action_owner="unknown",
            evidence={"error": str(exc)[:200], "store_slug": _store_slug(store)},
            health_source="merchant_whatsapp_connection_readiness_v1",
        )

    state = str(readiness.get("connection_state") or "")
    codes: list[str] = []
    if state != CONNECTION_STATE_CONNECTED:
        codes.append(DIAG_WHATSAPP_MERCHANT_NOT_CONNECTED)
        status = STATUS_MERCHANT_ACTION_REQUIRED
        action_owner = "merchant"
    else:
        status = STATUS_HEALTHY
        action_owner = "none"

    return _integration_record(
        name="whatsapp",
        status=status,
        diagnosis_codes=codes,
        action_owner=action_owner,
        last_success_at=None,
        last_failure_at=None,
        evidence={
            "store_slug": _store_slug(store),
            "connection_state": state,
            "readiness_overall": readiness.get("readiness_overall"),
        },
        health_source="merchant_whatsapp_connection_readiness_v1",
    )


def _build_widget_event_flow_health(
    widget_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    codes: list[str] = []
    for row in widget_rows:
        for kind in row.get("issue_kinds") or []:
            diag = _WIDGET_ISSUE_TO_DIAG.get(str(kind))
            if diag and diag not in codes:
                codes.append(diag)

    if not widget_rows:
        status = STATUS_UNKNOWN
    elif not codes:
        status = STATUS_HEALTHY
    elif DIAG_WIDGET_RUNTIME_MISSING in codes or DIAG_WIDGET_NOT_SEEN in codes:
        status = STATUS_DEGRADED
    else:
        status = STATUS_DEGRADED

    return _integration_record(
        name="widget_event_flow",
        status=status,
        diagnosis_codes=codes,
        action_owner="merchant" if codes else "none",
        last_success_at=None,
        last_failure_at=None,
        evidence={"stores_assessed": len(widget_rows)},
        health_source="widget_health_v1",
    )


def _build_signal_readiness(
    *,
    slug: str,
    window_start: datetime,
    store_id: Optional[int],
) -> dict[str, Any]:
    """IH-C4 — independent signal classes; readiness only, no inference."""
    activity = {}
    if store_id and slug:
        try:
            store = db.session.get(Store, store_id)
            if store:
                activity = _query_store_activity(store, slug=slug, window_start=window_start)
        except SQLAlchemyError:
            db.session.rollback()

    hesitation_count = int(activity.get("hesitation_count") or 0)
    checkout_count = int(activity.get("checkout_signal_count") or 0)
    purchase_count = int(activity.get("purchase_count") or 0)
    cart_count = int(activity.get("cart_event_count") or 0)

    hesitation = _integration_record(
        name="hesitation",
        status=STATUS_HEALTHY if hesitation_count > 0 else STATUS_UNKNOWN,
        diagnosis_codes=[] if hesitation_count > 0 else [],
        action_owner="none",
        evidence={"event_count": hesitation_count, "health_source_table": "cart_recovery_reasons"},
        health_source="cart_recovery_reasons",
    )

    checkout = _integration_record(
        name="checkout_friction",
        status=STATUS_HEALTHY if checkout_count > 0 else STATUS_UNKNOWN,
        diagnosis_codes=[] if checkout_count > 0 else [DIAG_CHECKOUT_SIGNAL_MISSING],
        action_owner="none",
        evidence={
            "signal_count": checkout_count,
            "health_source_table": "recovery_truth_timeline_events",
        },
        health_source="recovery_truth_timeline_events",
    )

    payment = _integration_record(
        name="payment_failure",
        status=STATUS_NOT_IMPLEMENTED,
        diagnosis_codes=[DIAG_PAYMENT_SIGNAL_MISSING],
        action_owner="none",
        evidence={"implemented": False, "note": "payment_failure_signals_not_wired_v1"},
        health_source=INTEGRATION_PATH_NOT_IMPLEMENTED,
    )

    purchase = _integration_record(
        name="purchase_confirmation",
        status=STATUS_HEALTHY if purchase_count > 0 else STATUS_UNKNOWN,
        diagnosis_codes=[]
        if purchase_count > 0
        else ([DIAG_ZID_PURCHASE_EVENTS_MISSING] if cart_count > 0 else []),
        action_owner="merchant" if cart_count > 0 and purchase_count == 0 else "none",
        evidence={
            "purchase_count": purchase_count,
            "health_source_table": "purchase_truth_records",
        },
        health_source="purchase_truth_records",
    )

    return {
        "hesitation": hesitation,
        "checkout_friction": checkout,
        "payment_failure": payment,
        "purchase_confirmation": purchase,
    }


def _load_stores(*, store_slug: Optional[str] = None, limit: int = 50) -> list[Store]:
    try:
        db.create_all()
        q = db.session.query(Store).order_by(Store.id.asc())
        ss = (store_slug or "").strip()[:255]
        if ss:
            q = q.filter(Store.zid_store_id == ss)
        return q.limit(max(1, limit)).all()
    except SQLAlchemyError:
        db.session.rollback()
        return []


def _widget_rows_for_stores(stores: list[Store]) -> dict[str, dict[str, Any]]:
    rows_by_slug: dict[str, dict[str, Any]] = {}
    try:
        from services.widget_health_v1 import build_store_widget_health_row  # noqa: PLC0415
        from services.admin_operations_center_v1 import _store_readiness_summary  # noqa: PLC0415

        _summary, per_store = _store_readiness_summary()
        lookup = {str(r.get("store_slug") or ""): r for r in (per_store or [])}
        for store in stores:
            slug = _store_slug(store)
            src = lookup.get(slug) or {
                "store_slug": slug,
                "display_name": slug,
                "widget_last_seen_at": getattr(store, "widget_last_seen_at", None),
                "widget_last_beacon_json": getattr(store, "widget_last_beacon_json", None),
                "widget_runtime_truth_status": getattr(
                    store, "widget_runtime_truth_status", None
                ),
                "widget_last_runtime_slug": getattr(store, "widget_last_runtime_slug", None),
            }
            rows_by_slug[slug] = build_store_widget_health_row(src)
    except Exception:  # noqa: BLE001
        for store in stores:
            slug = _store_slug(store)
            rows_by_slug[slug] = {"store_slug": slug, "status": STATUS_UNKNOWN, "issue_kinds": []}
    return rows_by_slug


def build_integration_health(
    *,
    store_slug: Optional[str] = None,
    window_days: int = 7,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Single read-only Integration Health composer (IH-C1).

    Fail-isolated per store and per platform subsection (IH-C5).
    """
    generated = (now or _utc_now()).isoformat()
    end = _naive(now or _utc_now())
    window_start = end - timedelta(days=max(1, int(window_days)))

    stores = _load_stores(store_slug=store_slug)
    widget_by_slug = _widget_rows_for_stores(stores)
    widget_rows = list(widget_by_slug.values())

    connected_count = sum(
        1 for s in stores if is_merchant_store_platform_connected(s)
    )

    platform: dict[str, Any] = {}
    try:
        platform["zid"] = _build_platform_zid_health(
            window_start=window_start,
            connected_store_count=connected_count,
        )
    except Exception as exc:  # noqa: BLE001
        platform["zid"] = _integration_record(
            name="zid",
            status=STATUS_UNKNOWN,
            diagnosis_codes=[],
            action_owner="unknown",
            evidence={"error": str(exc)[:200]},
            health_source=INTEGRATION_PATH_LEGACY_ZID,
        )

    platform["salla"] = _build_scaffold_platform("salla")
    platform["shopify"] = _build_scaffold_platform("shopify")

    try:
        platform["whatsapp_architecture"] = _build_whatsapp_architecture_health()
    except Exception as exc:  # noqa: BLE001
        platform["whatsapp_architecture"] = _integration_record(
            name="whatsapp_architecture",
            status=STATUS_UNKNOWN,
            diagnosis_codes=[],
            action_owner="unknown",
            evidence={"error": str(exc)[:200]},
            health_source="cartflow_provider_readiness",
        )

    platform["meta_production"] = _build_meta_production_health()

    store_rows: list[dict[str, Any]] = []
    primary_slug = (store_slug or "").strip()[:255]
    primary_store_id: Optional[int] = None

    for store in stores:
        slug = _store_slug(store)
        if not slug:
            continue
        if primary_slug and slug == primary_slug:
            primary_store_id = int(store.id) if store.id else None
        if not primary_slug and primary_store_id is None and store.id:
            primary_slug = slug
            primary_store_id = int(store.id)

        row: dict[str, Any] = {"store_slug": slug}
        try:
            row["zid"] = _build_store_zid_health(
                store,
                window_start=window_start,
                widget_row=widget_by_slug.get(slug),
            )
        except Exception as exc:  # noqa: BLE001
            row["zid"] = _integration_record(
                name="zid",
                status=STATUS_UNKNOWN,
                diagnosis_codes=[],
                action_owner="unknown",
                evidence={"error": str(exc)[:200]},
                health_source=INTEGRATION_PATH_LEGACY_ZID,
            )
        try:
            row["whatsapp"] = _build_store_whatsapp_health(store)
        except Exception as exc:  # noqa: BLE001
            row["whatsapp"] = _integration_record(
                name="whatsapp",
                status=STATUS_UNKNOWN,
                diagnosis_codes=[],
                action_owner="unknown",
                evidence={"error": str(exc)[:200]},
                health_source="merchant_whatsapp_connection_readiness_v1",
            )
        store_rows.append(row)

    try:
        widget_event_flow = _build_widget_event_flow_health(widget_rows)
    except Exception as exc:  # noqa: BLE001
        widget_event_flow = _integration_record(
            name="widget_event_flow",
            status=STATUS_UNKNOWN,
            diagnosis_codes=[],
            action_owner="unknown",
            evidence={"error": str(exc)[:200]},
            health_source="widget_health_v1",
        )

    try:
        signal_readiness = _build_signal_readiness(
            slug=primary_slug,
            window_start=window_start,
            store_id=primary_store_id,
        )
    except Exception as exc:  # noqa: BLE001
        signal_readiness = {
            "error": str(exc)[:200],
            "status": STATUS_UNKNOWN,
        }

    return {
        "ok": True,
        "version": VERSION,
        "generated_at": generated,
        "window_days": window_days,
        "platform": platform,
        "stores": store_rows,
        "widget_event_flow": widget_event_flow,
        "signal_readiness": signal_readiness,
    }


__all__ = [
    "VERSION",
    "build_integration_health",
    "DIAG_META_PRODUCTION_BLOCKED",
    "DIAG_PLATFORM_ADAPTER_SCAFFOLD",
    "DIAG_ZID_NOT_CONNECTED",
    "INTEGRATION_PATH_LEGACY_ZID",
    "STATUS_PRODUCTION_BLOCKED",
]
