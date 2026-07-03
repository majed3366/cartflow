# -*- coding: utf-8 -*-
"""
Dashboard snapshot archive — Data Growth Governance Phase 3.

Moves historical-only snapshot rows older than retention off dashboard_snapshots
into dashboard_snapshots_archive. Latest per (store_slug, snapshot_type) is never
archived. Does not change fetch_latest_snapshot_row or builder behavior.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func

from extensions import db
from models import DashboardSnapshot, DashboardSnapshotArchive

_log = logging.getLogger(__name__)

ENV_ARCHIVE_ENABLED = "CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED"
ENV_RETENTION_DAYS = "CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_RETENTION_DAYS"
ENV_BATCH_SIZE = "CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_BATCH_SIZE"
ENV_TICK_MAX_SECONDS = "CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_TICK_MAX_SECONDS"
ENV_MAX_BATCHES_PER_TICK = "CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_MAX_BATCHES_PER_TICK"

_DEFAULT_RETENTION_DAYS = 30
_DEFAULT_BATCH_SIZE = 500
_DEFAULT_TICK_MAX_SECONDS = 60.0

_last_tick_result: dict[str, Any] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def dashboard_snapshot_archive_enabled() -> bool:
    raw = (os.environ.get(ENV_ARCHIVE_ENABLED) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def dashboard_snapshot_archive_retention_days() -> int:
    raw = (os.environ.get(ENV_RETENTION_DAYS) or "").strip()
    try:
        v = int(raw or _DEFAULT_RETENTION_DAYS)
    except (TypeError, ValueError):
        v = _DEFAULT_RETENTION_DAYS
    return max(1, min(v, 365))


def dashboard_snapshot_archive_batch_size() -> int:
    raw = (os.environ.get(ENV_BATCH_SIZE) or "").strip()
    try:
        v = int(raw or _DEFAULT_BATCH_SIZE)
    except (TypeError, ValueError):
        v = _DEFAULT_BATCH_SIZE
    return max(1, min(v, 5000))


def dashboard_snapshot_archive_tick_max_seconds() -> float:
    raw = (os.environ.get(ENV_TICK_MAX_SECONDS) or "").strip()
    try:
        v = float(raw or _DEFAULT_TICK_MAX_SECONDS)
    except (TypeError, ValueError):
        v = _DEFAULT_TICK_MAX_SECONDS
    return max(5.0, min(v, 300.0))


def dashboard_snapshot_archive_max_batches_per_tick() -> int:
    """0 = unlimited batches per tick (until time limit or eligibility exhausted)."""
    raw = (os.environ.get(ENV_MAX_BATCHES_PER_TICK) or "").strip()
    try:
        v = int(raw or 0)
    except (TypeError, ValueError):
        v = 0
    return max(0, v)


def _payload_digest(payload_json: str) -> str:
    return hashlib.sha256((payload_json or "").encode("utf-8")).hexdigest()


def resolve_latest_snapshot_ids(db_session: Any) -> set[int]:
    """Id of newest row per (store_slug, snapshot_type) by generated_at."""
    pair_rows = (
        db_session.query(
            DashboardSnapshot.store_slug,
            DashboardSnapshot.snapshot_type,
            func.max(DashboardSnapshot.generated_at).label("max_generated_at"),
        )
        .group_by(DashboardSnapshot.store_slug, DashboardSnapshot.snapshot_type)
        .all()
    )
    latest_ids: set[int] = set()
    for slug, stype, max_gen in pair_rows:
        if max_gen is None:
            continue
        row = (
            db_session.query(DashboardSnapshot.id)
            .filter(
                DashboardSnapshot.store_slug == slug,
                DashboardSnapshot.snapshot_type == stype,
                DashboardSnapshot.generated_at == max_gen,
            )
            .order_by(DashboardSnapshot.id.desc())
            .limit(1)
            .first()
        )
        if row is not None:
            latest_ids.add(int(row[0]))
    return latest_ids


def retention_cutoff(*, now: Optional[datetime] = None) -> datetime:
    now_u = _as_utc(now) or _utcnow()
    return now_u - timedelta(days=dashboard_snapshot_archive_retention_days())


def count_archive_eligible_rows(
    db_session: Any,
    *,
    latest_ids: Optional[set[int]] = None,
    cutoff: Optional[datetime] = None,
) -> int:
    latest = latest_ids if latest_ids is not None else resolve_latest_snapshot_ids(db_session)
    cut = _as_utc(cutoff) or retention_cutoff()
    q = db_session.query(func.count(DashboardSnapshot.id)).filter(
        DashboardSnapshot.generated_at < cut,
    )
    if latest:
        q = q.filter(~DashboardSnapshot.id.in_(latest))
    return int(q.scalar() or 0)


def _archive_row_from_snapshot(
    row: DashboardSnapshot,
    *,
    archived_at: datetime,
) -> DashboardSnapshotArchive:
    return DashboardSnapshotArchive(
        source_snapshot_id=int(row.id),
        store_id=row.store_id,
        store_slug=row.store_slug,
        snapshot_type=row.snapshot_type,
        payload_json=row.payload_json or "{}",
        generated_at=row.generated_at,
        expires_at=row.expires_at,
        version=int(row.version or 1),
        status=str(row.status or "active"),
        created_at=row.created_at,
        updated_at=row.updated_at,
        archived_at=archived_at,
    )


def _fetch_archive_candidate_batch(
    db_session: Any,
    *,
    latest_ids: set[int],
    cutoff: datetime,
    batch_size: int,
    after_id: int = 0,
) -> list[DashboardSnapshot]:
    q = (
        db_session.query(DashboardSnapshot)
        .filter(DashboardSnapshot.id > after_id)
        .filter(DashboardSnapshot.generated_at < cutoff)
        .order_by(DashboardSnapshot.id.asc())
    )
    if latest_ids:
        q = q.filter(~DashboardSnapshot.id.in_(latest_ids))
    return list(q.limit(batch_size).all())


def _move_batch_to_archive(
    db_session: Any,
    rows: list[DashboardSnapshot],
    *,
    archived_at: datetime,
) -> dict[str, Any]:
    if not rows:
        return {"moved": 0, "payload_mismatch": 0}

    source_ids = [int(r.id) for r in rows]
    archives: list[DashboardSnapshotArchive] = []
    digests_before: dict[int, str] = {}
    for row in rows:
        digests_before[int(row.id)] = _payload_digest(row.payload_json or "")
        archives.append(_archive_row_from_snapshot(row, archived_at=archived_at))

    db_session.add_all(archives)
    db_session.flush()

    payload_mismatch = 0
    for arch in archives:
        if _payload_digest(arch.payload_json or "") != digests_before.get(
            int(arch.source_snapshot_id), ""
        ):
            payload_mismatch += 1

    if payload_mismatch:
        db_session.rollback()
        raise RuntimeError(
            f"archive payload integrity check failed mismatch={payload_mismatch}"
        )

    deleted = (
        db_session.query(DashboardSnapshot)
        .filter(DashboardSnapshot.id.in_(source_ids))
        .delete(synchronize_session=False)
    )
    if int(deleted) != len(rows):
        db_session.rollback()
        raise RuntimeError(
            f"archive hot-table delete count mismatch expected={len(rows)} got={deleted}"
        )

    db_session.commit()
    return {"moved": len(rows), "payload_mismatch": 0}


def run_dashboard_snapshot_archive_tick(
    *,
    db_session: Any | None = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Bounded archive tick: move eligible historical rows to cold table.

    Resumable — each batch commits independently; next tick continues by id order.
    """
    global _last_tick_result

    session = db_session or db.session
    if not dashboard_snapshot_archive_enabled():
        out = {"skipped": True, "reason": "archive_disabled"}
        _last_tick_result = out
        return out

    t0 = time.perf_counter()
    tick_max = dashboard_snapshot_archive_tick_max_seconds()
    batch_size = dashboard_snapshot_archive_batch_size()
    max_batches = dashboard_snapshot_archive_max_batches_per_tick()
    cut = retention_cutoff(now=now)
    archived_at = _as_utc(now) or _utcnow()

    try:
        latest_ids = resolve_latest_snapshot_ids(session)
        eligible_before = count_archive_eligible_rows(
            session, latest_ids=latest_ids, cutoff=cut
        )
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        out = {"ok": False, "error": str(exc)[:500]}
        _last_tick_result = out
        return out

    moved_total = 0
    batches = 0
    last_id = 0
    stopped_reason = "eligible_exhausted"

    while (time.perf_counter() - t0) < tick_max:
        try:
            batch = _fetch_archive_candidate_batch(
                session,
                latest_ids=latest_ids,
                cutoff=cut,
                batch_size=batch_size,
                after_id=last_id,
            )
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            out = {
                "ok": False,
                "error": str(exc)[:500],
                "rows_archived_this_tick": moved_total,
                "batches_committed": batches,
            }
            _last_tick_result = out
            return out

        if not batch:
            break

        try:
            batch_ids = [int(r.id) for r in batch]
            move_out = _move_batch_to_archive(session, batch, archived_at=archived_at)
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            _log.warning("dashboard snapshot archive batch failed: %s", exc, exc_info=True)
            out = {
                "ok": False,
                "error": str(exc)[:500],
                "rows_archived_this_tick": moved_total,
                "batches_committed": batches,
            }
            _last_tick_result = out
            return out

        moved = int(move_out.get("moved") or 0)
        moved_total += moved
        batches += 1
        last_id = max(batch_ids)

        if moved < batch_size:
            break

        if max_batches > 0 and batches >= max_batches:
            stopped_reason = "max_batches"
            break

        if (time.perf_counter() - t0) >= tick_max:
            stopped_reason = "time_limit"
            break
    else:
        stopped_reason = "time_limit"

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    try:
        hot_total = session.query(DashboardSnapshot).count()
        archive_total = session.query(DashboardSnapshotArchive).count()
        latest_kept = len(resolve_latest_snapshot_ids(session))
        eligible_after = count_archive_eligible_rows(session, cutoff=cut)
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        hot_total = None
        archive_total = None
        latest_kept = len(latest_ids)
        eligible_after = None
        _log.warning("archive tick post-count failed: %s", exc)

    out = {
        "ok": True,
        "skipped": False,
        "retention_days": dashboard_snapshot_archive_retention_days(),
        "retention_cutoff": cut.isoformat(),
        "rows_eligible_before_tick": eligible_before,
        "rows_eligible_after_tick": eligible_after,
        "rows_archived_this_tick": moved_total,
        "batches_committed": batches,
        "latest_rows_kept": latest_kept,
        "hot_table_rows": hot_total,
        "archive_table_rows": archive_total,
        "tick_elapsed_ms": elapsed_ms,
        "tick_max_seconds": tick_max,
        "batch_size": batch_size,
        "max_batches_per_tick": max_batches,
        "stopped_reason": stopped_reason,
        "resumable": eligible_after is not None and eligible_after > 0,
    }
    _last_tick_result = out
    _log.info(
        "[DASHBOARD SNAPSHOT ARCHIVE] moved=%s eligible_after=%s hot=%s archive=%s ms=%s",
        moved_total,
        eligible_after,
        hot_total,
        archive_total,
        elapsed_ms,
    )
    return out


def get_last_archive_tick_result() -> dict[str, Any]:
    return dict(_last_tick_result)


def assess_dashboard_snapshot_archive_status(
    db_session: Any,
    *,
    include_last_tick: bool = True,
) -> dict[str, Any]:
    """Read-only diagnostics for archive governance."""
    cut = retention_cutoff()
    try:
        hot_total = int(db_session.query(DashboardSnapshot).count())
        archive_total = int(db_session.query(DashboardSnapshotArchive).count())
        latest_ids = resolve_latest_snapshot_ids(db_session)
        latest_kept = len(latest_ids)
        eligible = count_archive_eligible_rows(
            db_session, latest_ids=latest_ids, cutoff=cut
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": str(exc)[:500],
            "archive_enabled": dashboard_snapshot_archive_enabled(),
        }

    rollback_window_days = dashboard_snapshot_archive_retention_days()
    remaining_risk = "LOW"
    if hot_total >= 100_000:
        remaining_risk = "HIGH"
    elif eligible >= 10_000 or hot_total >= 50_000:
        remaining_risk = "MEDIUM"

    out: dict[str, Any] = {
        "ok": True,
        "archive_enabled": dashboard_snapshot_archive_enabled(),
        "retention_days": rollback_window_days,
        "retention_cutoff": cut.isoformat(),
        "total_snapshot_rows_hot": hot_total,
        "total_snapshot_rows_archive": archive_total,
        "latest_rows_kept": latest_kept,
        "rows_eligible_for_archive": eligible,
        "rows_within_rollback_window": max(0, hot_total - latest_kept - eligible),
        "remaining_risk": remaining_risk,
        "batch_size": dashboard_snapshot_archive_batch_size(),
        "tick_max_seconds": dashboard_snapshot_archive_tick_max_seconds(),
    }
    if include_last_tick and _last_tick_result:
        out["last_tick"] = dict(_last_tick_result)
    return out


__all__ = [
    "ENV_ARCHIVE_ENABLED",
    "ENV_BATCH_SIZE",
    "ENV_RETENTION_DAYS",
    "ENV_MAX_BATCHES_PER_TICK",
    "ENV_TICK_MAX_SECONDS",
    "assess_dashboard_snapshot_archive_status",
    "count_archive_eligible_rows",
    "dashboard_snapshot_archive_batch_size",
    "dashboard_snapshot_archive_enabled",
    "dashboard_snapshot_archive_max_batches_per_tick",
    "dashboard_snapshot_archive_retention_days",
    "dashboard_snapshot_archive_tick_max_seconds",
    "get_last_archive_tick_result",
    "resolve_latest_snapshot_ids",
    "retention_cutoff",
    "run_dashboard_snapshot_archive_tick",
]
