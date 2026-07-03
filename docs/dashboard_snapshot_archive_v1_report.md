# Dashboard Snapshot Archive v1 — Report

**Phase:** Data Growth Governance Phase 3  
**Date:** 2026-07-03 (UTC)  
**Priority:** P0  
**Status:** Implemented (env-gated; deploy + migration required)

---

## Problem

Production measurement (Phase 2) showed unbounded append-only growth in `dashboard_snapshots`:

| Metric | Value |
|--------|------:|
| Hot table rows | 137,358 |
| Hot table size | ~387 MB |
| Historical-only rows | 136,894 (99.66%) |
| Rows read in practice | ~468 (latest per store × type) |
| Growth rate | ~4,579 rows/day |

Dashboard reads use `fetch_latest_snapshot_row()` — only the newest row per `(store_slug, snapshot_type)` matters. Historical versions accumulated indefinitely with no TTL or archive path.

---

## Solution

Move **historical-only** rows older than a configurable retention window from `dashboard_snapshots` (hot) to `dashboard_snapshots_archive` (cold).

### Retention rules

1. **Never archive** the latest row per `(store_slug, snapshot_type)` — even if that row is older than retention (e.g. builder paused).
2. **Preserve rollback window:** all versions with `generated_at >= now - retention_days` stay on the hot table.
3. **Archive eligibility:** `generated_at < cutoff` AND row is not the latest for its pair.

Default retention: **30 days** (`CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_RETENTION_DAYS`).

### Move semantics (not hard delete)

Each archived row is:

1. Copied to `dashboard_snapshots_archive` with `source_snapshot_id` + `archived_at`
2. SHA-256 payload integrity verified before commit
3. Removed from `dashboard_snapshots` only after successful archive insert

Data is retained in cold storage; hot table stops growing unbounded.

---

## Components

| Component | Path |
|-----------|------|
| Archive model | `models.py` → `DashboardSnapshotArchive` |
| Migration | `alembic/versions/r4s5t6u7v8w9_add_dashboard_snapshots_archive.py` |
| Archive service | `services/dashboard_snapshot_archive_v1.py` |
| Scheduler loop | `services/dashboard_snapshot_archive_loop_v1.py` |
| Startup wiring | `services/runtime_startup_v1.py` |
| Diagnostics | `GET /dev/dashboard-snapshot-archive` |
| Tests | `tests/test_dashboard_snapshot_archive_v1.py` |

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED` | off | Master switch |
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_RETENTION_DAYS` | 30 | Rollback window |
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_BATCH_SIZE` | 500 | Rows per commit batch |
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_TICK_MAX_SECONDS` | 60 | Wall time per tick |
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_MAX_BATCHES_PER_TICK` | 0 (unlimited) | Cap batches per tick (0 = until time/eligibility) |
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_INTERVAL_SECONDS` | 3600 | Loop interval |

---

## Bounded & resumable job design

Each tick:

- Resolves latest ids once per tick
- Fetches candidates ordered by `id ASC` in batches
- Commits each batch independently (safe partial progress)
- Stops on time limit or exhausted eligibility
- Next tick continues from remaining rows (naturally resumable)

Diagnostics per tick: eligible before/after, rows moved, batches, elapsed ms, `stopped_reason`, `resumable`.

---

## Out of scope (unchanged)

- `fetch_latest_snapshot_row()` — **not modified**
- `upsert_dashboard_snapshot()` / builder — **not modified**
- Dashboard API handlers — **not modified**
- Recovery, lifecycle, purchase truth, widget, scheduler due-scanner — **not modified**

---

## Required diagnostics

`GET /dev/dashboard-snapshot-archive` returns:

- `total_snapshot_rows_hot`
- `total_snapshot_rows_archive`
- `latest_rows_kept`
- `rows_eligible_for_archive`
- `rows_within_rollback_window`
- `remaining_risk` (LOW / MEDIUM / HIGH)
- `last_tick` (when a tick has run in-process)
- Optional `run_tick=1` for one manual bounded tick (dev)

Post-tick fields include `rows_archived_this_tick`, `tick_elapsed_ms`, `archive_duration` equivalent.

---

## Test coverage

| # | Requirement | Test |
|---|-------------|------|
| 1 | Latest never archived | `test_latest_snapshot_is_never_archived` |
| 2 | Rollback window preserved | `test_recent_rollback_window_is_preserved` |
| 3 | Old historical rows archived | `test_old_historical_rows_are_archived` |
| 4 | Dashboard read unchanged | `test_dashboard_read_still_returns_latest_snapshot` |
| 5 | Bounded & resumable | `test_archive_job_is_bounded_and_resumable` |
| 6 | No payload corruption | `test_no_payload_corruption_on_archive` |
| 7 | No fetch/recovery behavior change | `test_archive_does_not_change_fetch_latest_contract` |

Run: `pytest tests/test_dashboard_snapshot_archive_v1.py -q`

---

## Production rollout plan

1. **Deploy migration** `r4s5t6u7v8w9` on scheduler + API (creates archive table).
2. **Enable on scheduler role only** initially:
   ```
   CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED=1
   CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_RETENTION_DAYS=30
   CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_BATCH_SIZE=500
   CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_TICK_MAX_SECONDS=60
   CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_INTERVAL_SECONDS=3600
   ```
3. **Monitor** via `/dev/dashboard-snapshot-archive` and `/dev/data-growth-measurement`.
4. **Expect:** hot row count drops toward `(latest pairs + recent versions)`; archive table grows; dashboard reads unaffected.

### Remaining risk after rollout

| Phase | Hot rows (est.) | Risk |
|-------|-----------------|------|
| Before | 137k+ | HIGH |
| After steady-state | ~latest + 30d versions (~5–15k depending on store count) | LOW–MEDIUM |
| During catch-up | Decreasing batch-by-batch | MEDIUM (I/O) |

First catch-up with ~137k eligible rows at 500/batch/hour ≈ **11 days**; increase batch size or run manual ticks (`run_tick=1`) to accelerate if needed.

---

## Acceptance

**dashboard_snapshots historical-only rows stop growing unbounded** once archive is enabled: new builder inserts are offset by periodic archival of rows outside the retention window, and the hot table retains only latest + rollback window.

---

## Related docs

- `docs/data_growth_governance_v1.md` — Phase 1 governance
- `docs/data_growth_measurement_v1.md` — Phase 2 baseline (137,358 rows)
