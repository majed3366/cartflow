# -*- coding: utf-8 -*-
"""
Merchant Home Experience M1 activation — transport-independent summary contract.

Ensures ``merchant_home_experience_v1`` is present on every valid dashboard summary
response regardless of live builder, snapshot read, or degraded fallback path.

Uses the certified ``compose_merchant_home_experience_v1`` only — no composition changes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.merchant_home_composition_v1 import (
    COMPOSITION_VERSION,
    compose_merchant_home_experience_v1,
)

log = logging.getLogger("cartflow")

SUMMARY_CONTRACT_SCHEMA_VERSION = "merchant_home_m1_v1"

TRANSPORT_LIVE = "live"
TRANSPORT_SNAPSHOT = "snapshot"
TRANSPORT_CACHE = "cache"
TRANSPORT_DEGRADED = "degraded"

_HOME_ATTACH_PRESENT = "present"
_HOME_ATTACH_COMPOSED = "composed_from_summary"
_HOME_ATTACH_DEGRADED = "degraded_empty"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def merchant_home_experience_attached(body: Mapping[str, Any]) -> bool:
    home = body.get("merchant_home_experience_v1")
    return isinstance(home, Mapping) and bool(home.get("ok"))


def summary_contract_schema_satisfied(body: Mapping[str, Any]) -> bool:
    if _norm(body.get("summary_contract_schema_version")) != SUMMARY_CONTRACT_SCHEMA_VERSION:
        return False
    return merchant_home_experience_attached(body)


def summary_snapshot_contract_stale(payload: Mapping[str, Any]) -> bool:
    """True when a stored summary snapshot predates the M1 home contract."""
    if not isinstance(payload, Mapping):
        return True
    if merchant_home_experience_attached(payload):
        return _norm(payload.get("summary_contract_schema_version")) != SUMMARY_CONTRACT_SCHEMA_VERSION
    return True


def _nav_metadata_from_summary(body: Mapping[str, Any]) -> dict[str, int]:
    stats = body.get("normal_carts_stats")
    if not isinstance(stats, Mapping):
        stats = {}
    store_counts = body.get("merchant_store_cart_counts")
    active = int(stats.get("normal_cart_count") or 0)
    if active <= 0 and isinstance(store_counts, Mapping):
        active = int(store_counts.get("active") or store_counts.get("normal") or 0)
    return {
        "active_carts": active,
        "waiting_send": int(body.get("merchant_nav_badge_abandoned") or 0),
    }


def _merchant_name_from_summary(body: Mapping[str, Any]) -> str:
    setup = body.get("merchant_setup_experience")
    if isinstance(setup, Mapping):
        name = _norm(setup.get("merchant_store_display_name"))
        if name:
            return name
    return "متجرك"


def _store_slug_from_summary(body: Mapping[str, Any]) -> str:
    snap = body.get("_snapshot")
    if isinstance(snap, Mapping):
        slug = _norm(snap.get("store_slug"))
        if slug:
            return slug
    return _norm(body.get("store_slug"))


def compose_home_api_payload_from_summary_context(
    body: Mapping[str, Any],
    *,
    store_slug: str = "",
    attach_mode: str = _HOME_ATTACH_COMPOSED,
) -> dict[str, Any]:
    """Build home API payload from summary fields only (snapshot-safe, no hot-path DB)."""
    brief = body.get("merchant_daily_brief_v1")
    if not isinstance(brief, Mapping):
        brief = {}
    slug = _norm(store_slug) or _store_slug_from_summary(body)
    composed = compose_merchant_home_experience_v1(
        merchant_name_ar=_merchant_name_from_summary(body),
        date_ar=_norm(body.get("merchant_ar_date_header")),
        brief_date=_norm(brief.get("brief_date")),
        daily_brief=brief,
        kl_insights=(),
        nav_metadata=_nav_metadata_from_summary(body),
    )
    home: dict[str, Any] = dict(composed)
    home["ok"] = True
    home["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    home["store_slug"] = slug
    home["daily_brief_v1"] = dict(brief) if brief else {}
    home["_activation"] = {
        "attach_mode": attach_mode,
        "transport_safe": True,
    }
    return home


def stamp_summary_contract_fields(body: dict[str, Any]) -> dict[str, Any]:
    body["summary_contract_schema_version"] = SUMMARY_CONTRACT_SCHEMA_VERSION
    return body


def build_merchant_home_transport_diagnostics(
    body: Mapping[str, Any],
    *,
    summary_source: str,
    home_attach_mode: str,
    cache_hit: bool = False,
) -> dict[str, Any]:
    snap = body.get("_snapshot") if isinstance(body.get("_snapshot"), Mapping) else {}
    home = body.get("merchant_home_experience_v1")
    composition_version = COMPOSITION_VERSION
    if isinstance(home, Mapping):
        composition_version = _norm(home.get("version")) or COMPOSITION_VERSION
    return {
        "summary_source": _norm(summary_source) or TRANSPORT_LIVE,
        "cache_hit": bool(cache_hit),
        "merchant_home_experience_attached": merchant_home_experience_attached(body),
        "home_attach_mode": _norm(home_attach_mode) or _HOME_ATTACH_PRESENT,
        "composition_version": composition_version,
        "summary_contract_schema_version": _norm(body.get("summary_contract_schema_version"))
        or SUMMARY_CONTRACT_SCHEMA_VERSION,
        "snapshot_version": int(snap.get("version") or 0) if isinstance(snap, Mapping) else 0,
        "snapshot_degraded": bool(body.get("snapshot_degraded")),
        "snapshot_stale": bool(body.get("snapshot_stale")),
    }


def ensure_merchant_home_experience_on_summary(
    body: dict[str, Any],
    *,
    summary_source: str,
    store_slug: str = "",
    cache_hit: bool = False,
) -> dict[str, Any]:
    """
    Guarantee ``merchant_home_experience_v1`` on a summary body.

    Idempotent: never replaces an existing valid home payload.
    """
    if not isinstance(body, dict):
        body = dict(body or {})

    attach_mode = _HOME_ATTACH_PRESENT
    if merchant_home_experience_attached(body):
        pass
    else:
        degraded = bool(body.get("snapshot_degraded")) or summary_source == TRANSPORT_DEGRADED
        attach_mode = _HOME_ATTACH_DEGRADED if degraded else _HOME_ATTACH_COMPOSED
        try:
            body["merchant_home_experience_v1"] = compose_home_api_payload_from_summary_context(
                body,
                store_slug=store_slug,
                attach_mode=attach_mode,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("merchant home activation compose failed: %s", exc)
            body["merchant_home_experience_v1"] = compose_home_api_payload_from_summary_context(
                {},
                store_slug=store_slug,
                attach_mode=_HOME_ATTACH_DEGRADED,
            )

        brief = body.get("merchant_daily_brief_v1")
        if not isinstance(brief, Mapping) or not brief:
            embedded = body["merchant_home_experience_v1"].get("daily_brief_v1")
            if isinstance(embedded, Mapping) and embedded:
                body["merchant_daily_brief_v1"] = embedded

    stamp_summary_contract_fields(body)
    body["_merchant_home_transport"] = build_merchant_home_transport_diagnostics(
        body,
        summary_source=summary_source,
        home_attach_mode=attach_mode,
        cache_hit=cache_hit,
    )
    return body


def _attach_commerce_signals_then_pulse(
    body: dict[str, Any],
    *,
    store_slug: str = "",
) -> None:
    """Signals must land on the body before Pulse reads them."""
    try:
        from services.commerce_signals_v1 import (  # noqa: PLC0415
            attach_commerce_signals_v1_to_summary,
        )

        attach_commerce_signals_v1_to_summary(body, store_slug=store_slug)
    except Exception as exc:  # noqa: BLE001
        log.warning("commerce_signals_v1 attach: %s", exc)
    try:
        from services.merchant_pulse_v1 import (  # noqa: PLC0415
            attach_merchant_pulse_v1_to_summary,
        )

        attach_merchant_pulse_v1_to_summary(body, store_slug=store_slug)
    except Exception as exc:  # noqa: BLE001
        log.warning("merchant_pulse_v1 attach: %s", exc)


def finalize_dashboard_summary_payload(
    payload: dict[str, Any],
    *,
    summary_source: str,
    store_slug: str = "",
    cache_hit: bool = False,
) -> dict[str, Any]:
    """Single summary exit contract for live, snapshot, cache, and degraded paths."""
    if not isinstance(payload, dict):
        payload = {"ok": True, **dict(payload or {})}
    body = dict(payload)
    if body.get("ok") is False:
        body["_merchant_home_transport"] = build_merchant_home_transport_diagnostics(
            body,
            summary_source=summary_source,
            home_attach_mode="summary_not_ok",
            cache_hit=cache_hit,
        )
        _attach_commerce_signals_then_pulse(body, store_slug=store_slug)
        return body
    body = ensure_merchant_home_experience_on_summary(
        body,
        summary_source=summary_source,
        store_slug=store_slug,
        cache_hit=cache_hit,
    )
    _attach_commerce_signals_then_pulse(body, store_slug=store_slug)
    return body


__all__ = [
    "SUMMARY_CONTRACT_SCHEMA_VERSION",
    "TRANSPORT_CACHE",
    "TRANSPORT_DEGRADED",
    "TRANSPORT_LIVE",
    "TRANSPORT_SNAPSHOT",
    "build_merchant_home_transport_diagnostics",
    "compose_home_api_payload_from_summary_context",
    "ensure_merchant_home_experience_on_summary",
    "finalize_dashboard_summary_payload",
    "merchant_home_experience_attached",
    "stamp_summary_contract_fields",
    "summary_contract_schema_satisfied",
    "summary_snapshot_contract_stale",
]
