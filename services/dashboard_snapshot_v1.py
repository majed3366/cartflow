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
_PREFIX_WRITE = "[DASHBOARD SNAPSHOT WRITE]"
_PREFIX_DEGRADED = "[DASHBOARD DEGRADED]"
_PREFIX_VIOLATION = "[DASHBOARD HOT PATH VIOLATION]"
_PREFIX_STORE = "[DASHBOARD SNAPSHOT STORE]"
_PREFIX_COVERAGE = "[DASHBOARD SNAPSHOT COVERAGE]"

# Audit/diagnostic slugs — never snapshot (compete with real merchants on updated_at).
_SNAPSHOT_BUILD_EXCLUDED_PREFIXES = (
    "stuckj-",
    "stuckaudit-",
)


def _env_truthy(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def dashboard_snapshot_mode_enabled() -> bool:
    return _env_truthy(ENV_SNAPSHOT_MODE)


def canonical_snapshot_store_slug(
    store: Any = None,
    *,
    store_slug: Optional[str] = None,
) -> str:
    """Single canonical key for dashboard_snapshots.store_slug (write + read)."""
    from services.dashboard_store_context import normalize_merchant_store_slug

    if store is not None:
        zid = normalize_merchant_store_slug(getattr(store, "zid_store_id", None))
        if zid:
            return zid
    if store_slug:
        normalized = normalize_merchant_store_slug(store_slug)
        if normalized:
            return normalized
    return ""


def resolve_merchant_store_slug_for_snapshot() -> str:
    """Authenticated merchant slug for snapshot reads — matches builder write key."""
    from services.dashboard_store_context import DEFAULT_MERCHANT_DASHBOARD_STORE_SLUG
    from services.merchant_auth_context import get_merchant_auth_store_slug
    from services.merchant_auth_v1 import development_dashboard_bypass_active

    slug = canonical_snapshot_store_slug(store_slug=get_merchant_auth_store_slug())
    if slug:
        return slug
    if development_dashboard_bypass_active():
        return DEFAULT_MERCHANT_DASHBOARD_STORE_SLUG
    return ""


def snapshot_db_identity_fingerprint() -> str:
    """Safe fingerprint of DATABASE_URL host/db for write/read audit (no secrets)."""
    import hashlib

    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        return "no_database_url"
    try:
        from sqlalchemy.engine.url import make_url

        parsed = make_url(url)
        host = (parsed.host or "local").strip()
        database = (parsed.database or "?").strip()
        digest = hashlib.sha256(f"{host}/{database}".encode()).hexdigest()
        return digest[:12]
    except Exception:  # noqa: BLE001
        return hashlib.sha256(url.encode()).hexdigest()[:12]


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


_DEFAULT_SNAPSHOT_JSON_CAP = 65_000
_NORMAL_CARTS_SNAPSHOT_JSON_CAP = 512_000


def snapshot_payload_json_cap(snapshot_type: str) -> int:
    """Max JSON bytes for persisted snapshot payloads (Text column; type-specific caps)."""
    stype = (snapshot_type or "").strip()
    if stype == SNAPSHOT_TYPE_NORMAL_CARTS:
        raw = (os.environ.get("CARTFLOW_NORMAL_CARTS_SNAPSHOT_JSON_CAP") or "").strip()
        if raw:
            try:
                return max(_DEFAULT_SNAPSHOT_JSON_CAP, min(2_000_000, int(raw)))
            except (TypeError, ValueError):
                pass
        return _NORMAL_CARTS_SNAPSHOT_JSON_CAP
    raw = (os.environ.get("CARTFLOW_DASHBOARD_SNAPSHOT_JSON_CAP") or "").strip()
    if raw:
        try:
            return max(10_000, min(2_000_000, int(raw)))
        except (TypeError, ValueError):
            pass
    return _DEFAULT_SNAPSHOT_JSON_CAP


def encode_snapshot_payload_json(
    payload: dict[str, Any],
    *,
    snapshot_type: str,
) -> str:
    cap = snapshot_payload_json_cap(snapshot_type)
    return json.dumps(payload, ensure_ascii=False, default=str)[:cap]


def snapshot_builder_failsafe_seconds() -> int:
    raw = (os.environ.get("CARTFLOW_DASHBOARD_SNAPSHOT_FAILSAFE_SECONDS") or "").strip()
    try:
        return max(60, min(3600, int(raw or "300")))
    except (TypeError, ValueError):
        return 300


def any_store_needs_failsafe_snapshot_build(
    *,
    store_pairs: list[tuple[int, str]],
) -> tuple[bool, str]:
    """True when any store lacks or has stale normal_carts/summary snapshots."""
    if not store_pairs:
        return False, ""
    cutoff = _utcnow() - timedelta(seconds=snapshot_builder_failsafe_seconds())
    for _store_id, slug in store_pairs:
        s = (slug or "").strip()
        if not s:
            continue
        nc_row = fetch_latest_snapshot_row(
            store_slug=s,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        )
        if nc_row is None:
            return True, f"no_normal_carts_snapshot store_slug={s}"
        if snapshot_row_is_stale(nc_row):
            gen = _as_utc(nc_row.generated_at)
            age_s = int((_utcnow() - gen).total_seconds()) if gen else -1
            return True, f"stale_normal_carts_snapshot store_slug={s} age_s={age_s}"
        row = fetch_latest_snapshot_row(store_slug=s, snapshot_type=SNAPSHOT_TYPE_SUMMARY)
        if row is None:
            return True, f"no_summary_snapshot store_slug={s}"
        gen = _as_utc(row.generated_at)
        if gen is None or gen < cutoff:
            age_s = int((_utcnow() - gen).total_seconds()) if gen else -1
            return True, f"stale_summary_snapshot store_slug={s} age_s={age_s}"
    return False, ""


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
        f"{_PREFIX_READ} store_slug={store_slug} snapshot_type={snapshot_type}{ep_part} "
        f"stale={str(stale).lower()} version={version} read_ms={round(read_ms, 1)} "
        f"db_fp={snapshot_db_identity_fingerprint()}"
    )


def emit_snapshot_miss(*, store_slug: str, snapshot_type: str) -> None:
    _emit(
        f"{_PREFIX_MISS} store_slug={store_slug} snapshot_type={snapshot_type} "
        f"db_fp={snapshot_db_identity_fingerprint()}"
    )


def emit_snapshot_write(
    *,
    store_slug: str,
    snapshot_type: str,
    generated_at: datetime,
    version: int,
    generation_reason: str = "",
) -> None:
    gen_s = generated_at.isoformat() if isinstance(generated_at, datetime) else str(generated_at)
    reason_part = f" reason={generation_reason}" if generation_reason else ""
    _emit(
        f"{_PREFIX_WRITE} store_slug={store_slug} snapshot_type={snapshot_type} "
        f"generated_at={gen_s} version={version}{reason_part} "
        f"db_fp={snapshot_db_identity_fingerprint()}"
    )


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
    slug = canonical_snapshot_store_slug(store_slug=store_slug)
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
    payload_json: Optional[str] = None,
    generation_reason: str = "",
) -> DashboardSnapshot:
    """
    Append a new snapshot version (raw, unconditional write primitive).

    This is the low-level append. Production generation goes through
    ``services.dashboard_snapshot_change_v1.write_dashboard_snapshot_guarded``,
    which applies the SG-2 identical-rewrite gate before delegating the actual
    insert here. Direct callers (tests / migrations / backfill) bypass the gate
    intentionally.
    """
    slug = canonical_snapshot_store_slug(store_slug=store_slug)
    stype = (snapshot_type or "").strip()
    now = _utcnow()
    ttl = int(ttl_seconds if ttl_seconds is not None else snapshot_ttl_seconds(stype))
    expires = now + timedelta(seconds=ttl)

    prev = fetch_latest_snapshot_row(store_slug=slug, snapshot_type=stype)
    version = int(getattr(prev, "version", 0) or 0) + 1

    if payload_json is not None:
        pj = payload_json[: snapshot_payload_json_cap(stype)]
    else:
        pj = encode_snapshot_payload_json(payload, snapshot_type=stype)

    row = DashboardSnapshot(
        store_id=store_id,
        store_slug=slug,
        snapshot_type=stype,
        payload_json=pj,
        generated_at=now,
        expires_at=expires,
        version=version,
        status=(status or STATUS_ACTIVE)[:32],
        created_at=now,
        updated_at=now,
    )
    db.session.add(row)
    db.session.commit()
    emit_snapshot_write(
        store_slug=slug,
        snapshot_type=stype,
        generated_at=now,
        version=version,
        generation_reason=generation_reason,
    )
    return row


def touch_dashboard_snapshot_freshness(
    row: DashboardSnapshot,
    *,
    ttl_seconds: Optional[int] = None,
    status: str = STATUS_ACTIVE,
) -> DashboardSnapshot:
    """
    Refresh an existing latest row's freshness in place (no new version).

    Snapshot Generation Governance SG-2 / §5.5: when a rebuild produces content
    that is semantically identical to the current latest row, freshness is a
    bookkeeping concern — extend ``expires_at``/``generated_at`` on the existing
    row instead of appending an identical version. Read-equivalent: reads always
    fetch the latest row and see the same content, now marked fresh.
    """
    stype = str(getattr(row, "snapshot_type", "") or "").strip()
    now = _utcnow()
    ttl = int(ttl_seconds if ttl_seconds is not None else snapshot_ttl_seconds(stype))
    row.generated_at = now
    row.expires_at = now + timedelta(seconds=ttl)
    row.updated_at = now
    row.status = (status or STATUS_ACTIVE)[:32]
    db.session.commit()
    return row


def emit_snapshot_store_selection(*, store_slug: str, reason: str) -> None:
    _emit(f"{_PREFIX_STORE} store_slug={store_slug} reason={reason}")


def emit_snapshot_coverage_summary(
    *,
    eligible: int,
    selected: int,
    limit: int,
    excluded_inactive: int = 0,
    excluded_no_merchant: int = 0,
    excluded_test_prefix: int = 0,
    excluded_placeholder: int = 0,
) -> None:
    _emit(
        f"{_PREFIX_COVERAGE} eligible={eligible} selected={selected} limit={limit} "
        f"excluded_inactive={excluded_inactive} excluded_no_merchant={excluded_no_merchant} "
        f"excluded_test_prefix={excluded_test_prefix} excluded_placeholder={excluded_placeholder}"
    )


def is_snapshot_build_eligible_store(
    *,
    zid_store_id: Optional[str],
    merchant_user_id: Optional[int],
    is_active: bool,
) -> tuple[bool, str]:
    """Active merchant-owned store eligible for dashboard snapshot builder."""
    from services.recovery_store_lookup import is_widget_recovery_zid

    slug = canonical_snapshot_store_slug(store_slug=zid_store_id)
    if not slug:
        return False, "missing_slug"
    if not is_active:
        return False, "inactive"
    if merchant_user_id is None:
        return False, "no_merchant_user"
    if is_widget_recovery_zid(slug):
        return False, "widget_placeholder_slug"
    lower = slug.casefold()
    for prefix in _SNAPSHOT_BUILD_EXCLUDED_PREFIXES:
        if lower.startswith(prefix):
            return False, "test_audit_prefix"
    return True, "active_merchant"


def _normal_carts_snapshot_build_tier(
    *,
    store_slug: str,
) -> Optional[tuple[int, datetime, str]]:
    """Tier 0 when normal_carts snapshot missing or expired — dashboard carts depend on it."""
    nc_row = fetch_latest_snapshot_row(
        store_slug=store_slug,
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
    )
    if nc_row is None:
        return 0, datetime.min.replace(tzinfo=timezone.utc), "missing_normal_carts"
    gen = _as_utc(nc_row.generated_at) or datetime.min.replace(tzinfo=timezone.utc)
    if snapshot_row_is_stale(nc_row):
        return 0, gen, "stale_normal_carts"
    return None


def _snapshot_build_priority(
    *,
    store_slug: str,
    failsafe_cutoff: datetime,
) -> tuple[int, datetime, str]:
    """Lower tier sorts first; oldest generated_at within tier rotates coverage."""
    nc_tier = _normal_carts_snapshot_build_tier(store_slug=store_slug)
    if nc_tier is not None:
        return nc_tier
    summary_row = fetch_latest_snapshot_row(
        store_slug=store_slug,
        snapshot_type=SNAPSHOT_TYPE_SUMMARY,
    )
    if summary_row is None:
        return 1, datetime.min.replace(tzinfo=timezone.utc), "missing_summary"
    gen = _as_utc(summary_row.generated_at)
    if gen is None or gen < failsafe_cutoff:
        return 2, gen or datetime.min.replace(tzinfo=timezone.utc), "stale_summary"
    return 3, gen or datetime.min.replace(tzinfo=timezone.utc), "rotate_oldest_summary"


def list_all_eligible_merchant_store_pairs() -> list[tuple[int, str]]:
    """All active merchant-linked stores eligible for snapshot builds."""
    from models import Store

    rows = (
        db.session.query(
            Store.id,
            Store.zid_store_id,
            Store.merchant_user_id,
            Store.is_active,
        )
        .filter(
            Store.zid_store_id.isnot(None),
            Store.merchant_user_id.isnot(None),
            Store.is_active.is_(True),
        )
        .all()
    )
    out: list[tuple[int, str]] = []
    seen: set[str] = set()
    for sid, zid, mid, is_active in rows:
        eligible, _reason = is_snapshot_build_eligible_store(
            zid_store_id=zid,
            merchant_user_id=mid,
            is_active=bool(is_active),
        )
        if not eligible:
            continue
        slug = canonical_snapshot_store_slug(store_slug=zid)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append((int(sid), slug))
    return out


def list_store_slugs_for_snapshot_build(*, limit: int = 10) -> list[tuple[int, str]]:
    """
    Select merchant stores for one builder tick.

    Coverage rules (not ``updated_at`` on Store — audit scripts bump test rows):
    - ``merchant_user_id`` present, ``is_active``, canonical ``zid_store_id``
    - Exclude widget placeholders (demo/demo2/default) and audit prefixes
    - Priority: missing/stale normal_carts → missing summary → stale summary → rotation
  """
    from models import Store

    cap = max(1, int(limit))
    rows = (
        db.session.query(
            Store.id,
            Store.zid_store_id,
            Store.merchant_user_id,
            Store.is_active,
        )
        .filter(
            Store.zid_store_id.isnot(None),
            Store.merchant_user_id.isnot(None),
            Store.is_active.is_(True),
        )
        .all()
    )
    failsafe_cutoff = _utcnow() - timedelta(seconds=snapshot_builder_failsafe_seconds())
    excluded_inactive = 0
    excluded_no_merchant = 0
    excluded_test_prefix = 0
    excluded_placeholder = 0
    candidates: list[tuple[int, str, int, datetime, str]] = []

    for sid, zid, mid, is_active in rows:
        eligible, exclude_reason = is_snapshot_build_eligible_store(
            zid_store_id=zid,
            merchant_user_id=mid,
            is_active=bool(is_active),
        )
        slug = canonical_snapshot_store_slug(store_slug=zid) or (zid or "").strip()
        if not eligible:
            if exclude_reason == "inactive":
                excluded_inactive += 1
            elif exclude_reason == "no_merchant_user":
                excluded_no_merchant += 1
            elif exclude_reason == "test_audit_prefix":
                excluded_test_prefix += 1
            elif exclude_reason == "widget_placeholder_slug":
                excluded_placeholder += 1
            continue
        tier, sort_gen, pick_reason = _snapshot_build_priority(
            store_slug=slug,
            failsafe_cutoff=failsafe_cutoff,
        )
        candidates.append((int(sid), slug, tier, sort_gen, pick_reason))

    candidates.sort(key=lambda item: (item[2], item[3], item[0]))
    selected = candidates[:cap]
    for _sid, slug, _tier, _gen, pick_reason in selected:
        emit_snapshot_store_selection(store_slug=slug, reason=pick_reason)
    emit_snapshot_coverage_summary(
        eligible=len(candidates),
        selected=len(selected),
        limit=cap,
        excluded_inactive=excluded_inactive,
        excluded_no_merchant=excluded_no_merchant,
        excluded_test_prefix=excluded_test_prefix,
        excluded_placeholder=excluded_placeholder,
    )
    return [(sid, slug) for sid, slug, _t, _g, _r in selected]


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
    "any_store_needs_failsafe_snapshot_build",
    "canonical_snapshot_store_slug",
    "decode_snapshot_payload",
    "dashboard_snapshot_mode_enabled",
    "emit_dashboard_degraded",
    "emit_hot_path_violation",
    "emit_snapshot_miss",
    "emit_snapshot_read",
    "emit_snapshot_store_selection",
    "emit_snapshot_write",
    "fetch_latest_snapshot_row",
    "is_snapshot_build_eligible_store",
    "list_all_eligible_merchant_store_pairs",
    "list_store_slugs_for_snapshot_build",
    "resolve_merchant_store_slug_for_snapshot",
    "snapshot_builder_failsafe_seconds",
    "snapshot_db_identity_fingerprint",
    "snapshot_row_is_stale",
    "snapshot_ttl_seconds",
    "touch_dashboard_snapshot_freshness",
    "upsert_dashboard_snapshot",
]
