# -*- coding: utf-8 -*-
"""
Dashboard snapshot storage — Reliability Foundation P0.

API hot path reads ``dashboard_snapshots`` only when
``CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1``.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import desc

from extensions import db
from models import DashboardSnapshot

log = logging.getLogger("cartflow")

ENV_SNAPSHOT_MODE = "CARTFLOW_DASHBOARD_SNAPSHOT_MODE"

SNAPSHOT_TYPE_SUMMARY = "summary"
SNAPSHOT_TYPE_NORMAL_CARTS = "normal_carts"
SNAPSHOT_TYPE_ABANDONED_CANDIDATES = "abandoned_candidates"
SNAPSHOT_TYPE_WHATSAPP_READINESS = "whatsapp_readiness"
SNAPSHOT_TYPE_MONTHLY_SUMMARY = "monthly_summary"
SNAPSHOT_TYPE_DASHBOARD_CARDS = "dashboard_cards"
SNAPSHOT_TYPE_REFRESH_STATE = "refresh_state"
SNAPSHOT_TYPE_WIDGET_PANEL = "widget_panel"
SNAPSHOT_TYPE_STORE_CONNECTION = "store_connection"

STATUS_ACTIVE = "active"
STATUS_STALE = "stale"
STATUS_BUILDING = "building"
STATUS_FAILED = "failed"

_PREFIX_READ = "[DASHBOARD SNAPSHOT READ]"
_PREFIX_MISS = "[DASHBOARD SNAPSHOT MISS]"
_PREFIX_DEGRADED = "[DASHBOARD DEGRADED]"
_PREFIX_VIOLATION = "[DASHBOARD HOT PATH VIOLATION]"


def _env_truthy(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def dashboard_snapshot_mode_enabled() -> bool:
    return _env_truthy(ENV_SNAPSHOT_MODE)


def snapshot_ttl_seconds(snapshot_type: str) -> int:
    key = f"CARTFLOW_DASHBOARD_SNAPSHOT_TTL_{(snapshot_type or '').upper()}_S"
    raw = (os.environ.get(key) or "").strip()
    if raw:
        try:
            return max(15, min(600, int(raw)))
        except (TypeError, ValueError):
            pass
    defaults = {
        SNAPSHOT_TYPE_SUMMARY: 60,
        SNAPSHOT_TYPE_NORMAL_CARTS: 45,
        SNAPSHOT_TYPE_REFRESH_STATE: 30,
        SNAPSHOT_TYPE_WIDGET_PANEL: 60,
        SNAPSHOT_TYPE_STORE_CONNECTION: 120,
        SNAPSHOT_TYPE_DASHBOARD_CARDS: 60,
        SNAPSHOT_TYPE_WHATSAPP_READINESS: 60,
        SNAPSHOT_TYPE_MONTHLY_SUMMARY: 120,
        SNAPSHOT_TYPE_ABANDONED_CANDIDATES: 45,
    }
    return int(defaults.get(snapshot_type or "", 60))


def _emit(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def emit_snapshot_read(
    *,
    store_slug: str,
    snapshot_type: str,
    stale: bool,
    version: int,
    read_ms: float,
    endpoint: str = "",
) -> None:
    ep_part = f" endpoint={(endpoint or snapshot_type)[:64]}" if (endpoint or snapshot_type) else ""
    _emit(
        f"{_PREFIX_READ} store_slug={store_slug} type={snapshot_type}{ep_part} "
        f"stale={str(stale).lower()} version={version} read_ms={round(read_ms, 1)}"
    )


def emit_snapshot_miss(*, store_slug: str, snapshot_type: str) -> None:
    _emit(f"{_PREFIX_MISS} store_slug={store_slug} type={snapshot_type}")


def emit_dashboard_degraded(
    *,
    store_slug: str,
    snapshot_type: str,
    reason: str,
) -> None:
    _emit(
        f"{_PREFIX_DEGRADED} store_slug={store_slug} type={snapshot_type} "
        f"reason={reason}"
    )


def emit_hot_path_violation(
    *,
    operation: str,
    path: str = "-",
    endpoint: str = "",
) -> None:
    ep = (endpoint or path or "-")[:64]
    _emit(
        f"{_PREFIX_VIOLATION} operation={(operation or 'unknown')[:128]} "
        f"endpoint={ep} path={(path or '-')[:256]}"
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_latest_snapshot_row(
    *,
    store_slug: str,
    snapshot_type: str,
) -> Optional[DashboardSnapshot]:
    slug = (store_slug or "").strip()
    stype = (snapshot_type or "").strip()
    if not slug or not stype:
        return None
    return (
        db.session.query(DashboardSnapshot)
        .filter(
            DashboardSnapshot.store_slug == slug,
            DashboardSnapshot.snapshot_type == stype,
        )
        .order_by(desc(DashboardSnapshot.generated_at))
        .limit(1)
        .first()
    )


def decode_snapshot_payload(row: DashboardSnapshot) -> dict[str, Any]:
    raw = (row.payload_json or "").strip() or "{}"
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"payload": data}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def snapshot_row_is_stale(row: DashboardSnapshot, *, now: Optional[datetime] = None) -> bool:
    now_u = _as_utc(now) or _utcnow()
    exp = _as_utc(row.expires_at)
    if exp is not None and exp < now_u:
        return True
    return str(row.status or "").lower() in (STATUS_STALE, STATUS_FAILED)


def upsert_dashboard_snapshot(
    *,
    store_id: Optional[int],
    store_slug: str,
    snapshot_type: str,
    payload: dict[str, Any],
    ttl_seconds: Optional[int] = None,
    status: str = STATUS_ACTIVE,
) -> DashboardSnapshot:
    slug = (store_slug or "").strip()
    stype = (snapshot_type or "").strip()
    now = _utcnow()
    ttl = int(ttl_seconds if ttl_seconds is not None else snapshot_ttl_seconds(stype))
    expires = now + timedelta(seconds=ttl)

    prev = fetch_latest_snapshot_row(store_slug=slug, snapshot_type=stype)
    version = int(getattr(prev, "version", 0) or 0) + 1

    row = DashboardSnapshot(
        store_id=store_id,
        store_slug=slug,
        snapshot_type=stype,
        payload_json=json.dumps(payload, ensure_ascii=False, default=str)[:65000],
        generated_at=now,
        expires_at=expires,
        version=version,
        status=(status or STATUS_ACTIVE)[:32],
        created_at=now,
        updated_at=now,
    )
    db.session.add(row)
    db.session.commit()
    return row


def list_store_slugs_for_snapshot_build(*, limit: int = 10) -> list[tuple[int, str]]:
    from models import Store

    rows = (
        db.session.query(Store.id, Store.zid_store_id)
        .filter(Store.zid_store_id.isnot(None))
        .order_by(Store.updated_at.desc())
        .limit(max(1, int(limit)))
        .all()
    )
    out: list[tuple[int, str]] = []
    for sid, slug in rows:
        s = (slug or "").strip()
        if s:
            out.append((int(sid), s))
    return out


__all__ = [
    "ENV_SNAPSHOT_MODE",
    "SNAPSHOT_TYPE_ABANDONED_CANDIDATES",
    "SNAPSHOT_TYPE_DASHBOARD_CARDS",
    "SNAPSHOT_TYPE_MONTHLY_SUMMARY",
    "SNAPSHOT_TYPE_NORMAL_CARTS",
    "SNAPSHOT_TYPE_REFRESH_STATE",
    "SNAPSHOT_TYPE_STORE_CONNECTION",
    "SNAPSHOT_TYPE_WIDGET_PANEL",
    "SNAPSHOT_TYPE_SUMMARY",
    "SNAPSHOT_TYPE_WHATSAPP_READINESS",
    "STATUS_ACTIVE",
    "STATUS_BUILDING",
    "STATUS_FAILED",
    "STATUS_STALE",
    "decode_snapshot_payload",
    "dashboard_snapshot_mode_enabled",
    "emit_dashboard_degraded",
    "emit_hot_path_violation",
    "emit_snapshot_miss",
    "emit_snapshot_read",
    "fetch_latest_snapshot_row",
    "list_store_slugs_for_snapshot_build",
    "snapshot_row_is_stale",
    "snapshot_ttl_seconds",
    "upsert_dashboard_snapshot",
]
