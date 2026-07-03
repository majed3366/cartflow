# Dashboard Snapshot Archive v1 — Production Activation

**Date:** 2026-07-03  
**Goal:** Enable bounded archive job on **scheduler only**; keep API read-only.

---

## Prerequisites

1. Phase 3 code deployed to **both** API and scheduler (endpoint + migration file in image).
2. Shared Postgres accessible from scheduler shell.

---

## Activation checklist

### 1. Migration (once)

On **scheduler** Railway shell or `railway run`:

```bash
alembic upgrade r4s5t6u7v8w9
# or: alembic upgrade head
```

Confirm table:

```sql
SELECT COUNT(*) FROM dashboard_snapshots_archive;
-- expect 0 rows initially
```

### 2. Environment — scheduler ONLY

| Variable | Value |
|----------|-------|
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED` | `1` |
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_RETENTION_DAYS` | `30` |
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_BATCH_SIZE` | `100` (conservative first run) |
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_MAX_BATCHES_PER_TICK` | `1` |
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_TICK_MAX_SECONDS` | `60` |
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_INTERVAL_SECONDS` | `3600` |

### 3. Environment — API service (explicit off)

| Variable | Value |
|----------|-------|
| `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED` | `0` or unset |

Operator script: `scripts/railway_dashboard_snapshot_archive_scheduler_v1.ps1`

### 4. Redeploy scheduler

Expect startup log:

```text
[RUNTIME STARTUP] dashboard_snapshot_archive_loop_started=true
dashboard_snapshot_archive_loop=enabled interval_s=3600
```

---

## Verification (dry first)

**Read-only** (no archive writes on API):

```bash
python scripts/dashboard_snapshot_archive_deploy_verify_v1.py
# or
curl https://smartreplyai.net/dev/dashboard-snapshot-archive
```

Expected fields:

- `archive_enabled`: **false** on API probe (correct)
- `total_snapshot_rows_hot`: current hot count
- `rows_eligible_for_archive`: > 0 after retention
- `latest_rows_kept`: ~468 (production baseline)
- `total_snapshot_rows_archive`: 0 before first scheduler tick

Archive **runs on scheduler loop**, not via public API `run_tick` when API has archive disabled.

### After ~1h (or check scheduler logs)

Re-run verify; expect:

- `total_snapshot_rows_hot` decreasing
- `total_snapshot_rows_archive` increasing
- `[DASHBOARD SNAPSHOT ARCHIVE] moved=N ...` in scheduler logs

---

## Acceptance

| Check | How |
|-------|-----|
| Historical rows moving | `rows_eligible` drops; `archive_table_rows` rises |
| Latest kept | `latest_rows_kept` stable |
| Dashboard loads | `/api/dashboard/summary` reachable |
| normal_carts latest | Merchant dashboard loads; snapshot read unchanged |
| No corruption | Archive payloads match via spot-check `source_snapshot_id` |

---

## Rollback

1. Set `CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED=0` on scheduler; redeploy.
2. Hot table still valid (latest never archived).
3. Restore rows from `dashboard_snapshots_archive` only if needed (manual SQL; not automated in v1).

---

## Related

- `docs/dashboard_snapshot_archive_v1_report.md`
- `scripts/dashboard_snapshot_archive_deploy_verify_v1.py`
