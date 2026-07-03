# Data Growth Measurement v1

**Program:** CartFlow Data Growth Governance — Phase 2  
**Date (UTC):** 2026-07-03  
**Status:** Complete — production row counts measured  
**Endpoint:** `GET /dev/data-growth-measurement` (read-only, production allowlisted)

**Prerequisite:** `docs/data_growth_governance_v1.md`  
**Tooling:** `services/data_growth_measurement_v1.py`, `scripts/data_growth_measurement_v1_probe.py`

**Non-goals:** archive jobs, deletion, compression, TTL jobs, monitoring dashboards.

---

## Executive summary (production — 2026-07-03T01:00:12Z)

| Metric | Value |
|--------|-------|
| **Platform growth risk** | **HIGH** |
| **Largest table** | `dashboard_snapshots` — **137,358 rows**, **386.7 MB** |
| **Append-only confirmed** | Yes — **99.66%** historical-only (**136,894** ignored rows) |
| **Daily snapshot growth** | **~4,579 rows/day** (~1,796 today) |
| **Threshold breach** | `dashboard_snapshots` at **warning** (100k) — not yet critical (1M) |
| **Archive priority #1** | `dashboard_snapshots` — **136,894** archivable rows |

Source: `scripts/_data_growth_measurement_v1_out/production_measurement_report.json`  
Measurement elapsed: **873 ms** (wall budget 8s) — PostgreSQL production.

---

## Endpoint

```
GET https://smartreplyai.net/dev/data-growth-measurement
```

**Safety:**
- Read-only — no writes, archive, or delete
- Count/metadata only — **no snapshot payloads**, no PII
- 8s wall budget; bounded store_slug top-20 breakdown
- Dev/admin diagnostic route (production allowlist)
- Skips optional tables absent on deploy (e.g. `movement_snapshots`)

**Response fields:** `tables[]`, `cf_behavioral`, `dashboard_snapshot_accumulation`, `growth_risk_score`, `archive_readiness_priority`, `measurement_elapsed_ms`

---

## Step 1 — Production table inventory

Measured **2026-07-03T01:00:12Z** via `/dev/data-growth-measurement`.

| Table | Rows | Size (MB) | Oldest | Newest | 7d growth | 30d growth | Daily est. | Risk |
|-------|-----:|----------:|--------|--------|----------:|-----------:|-----------:|------|
| **`dashboard_snapshots`** | **137,358** | **386.72** | 2026-06-30 | 2026-07-03 | 137,359 | 137,360 | **4,578.7** | **HIGH** |
| **`abandoned_carts`** | 4,218 | 2.87 | 2026-05-11 | 2026-07-02 | 22 | 126 | 4.2 | LOW |
| **`cart_recovery_logs`** | 1,132 | 1.14 | 2026-05-11 | 2026-07-02 | 75 | 189 | 6.3 | LOW |
| **`recovery_truth_timeline_events`** | 538 | 0.46 | 2026-05-26 | 2026-07-02 | 62 | 170 | 5.7 | LOW |
| **`recovery_schedules`** | 419 | 0.61 | 2026-05-21 | 2026-07-02 | 46 | 93 | 3.1 | LOW |
| **`purchase_truth_records`** | 132 | 0.27 | 2026-05-24 | 2026-07-02 | 21 | 24 | 0.8 | LOW |
| **`stores`** | 201 | 0.57 | 2026-05-11 | 2026-07-02 | 13 | 74 | 2.5 | LOW |
| **`movement_snapshots`** | — | — | — | — | — | — | — | Skipped (table not deployed) |

### cf_behavioral (nested)

| Metric | Value |
|--------|-------|
| Storage | `abandoned_carts.raw_payload` |
| Carts with `cf_behavioral` | **211 / 4,218** (5.0%) |
| Avg payload bytes (all carts) | 262 |
| Avg payload bytes (with behavioral) | 688 |
| Write cap | 65,000 bytes |
| Risk | LOW |

---

## Step 2 — Snapshot accumulation (production)

| Metric | Value |
|--------|-------|
| Total rows | **137,362** |
| Rows read in practice | **468** (latest per store × type) |
| Historical-only (ignored) | **136,894** |
| Historical % | **99.66%** |
| Append-only confirmed | **true** |
| Store×type pairs | 468 |
| Avg versions per pair | 293.5 |
| Max versions per pair | **892** |
| Oldest `generated_at` | 2026-06-30T04:05:52Z |
| Newest `generated_at` | 2026-07-03T01:00:12Z |

### By snapshot type

| Type | Rows |
|------|-----:|
| dashboard_cards | 22,929 |
| summary | 22,929 |
| refresh_state | 22,928 |
| store_connection | 22,928 |
| widget_panel | 22,928 |
| normal_carts | 22,720 |

### Top stores by snapshot row count

| Store slug | Snapshot rows |
|------------|--------------:|
| wa-verify-e3fbe611-72ea77 | 5,352 |
| wa-mode-4a2f33ad-e67c87 | 5,352 |
| wa-e8663d7c-e5fc74 | 5,346 |
| cartflow-42b491 | 2,313 |
| cartflow3-91bd2e | 2,023 |

**Finding:** Continuous builder since 2026-06-30 produces ~**892 versions/store/type** for active test stores. Only **468** rows are ever read on the merchant path.

---

## Step 3 — Log growth (production)

| Table | Total | 30d growth | Daily est. |
|-------|------:|-----------:|-----------:|
| `cart_recovery_logs` | 1,132 | 189 | 6.3 |
| `recovery_truth_timeline_events` | 538 | 170 | 5.7 |

Timeline avg ~5 events per recovery path; logs avg ~2 per recovery key at current scale.

---

## Step 4 — Health thresholds

| Table | Current | Warning | Critical | Status |
|-------|--------:|--------:|---------:|--------|
| **`dashboard_snapshots`** | **137,358** | 100,000 | 1,000,000 | **WARNING** |
| `abandoned_carts` | 4,218 | 500,000 | 2,000,000 | OK |
| `cart_recovery_logs` | 1,132 | 5,000,000 | 20,000,000 | OK |
| `recovery_truth_timeline_events` | 538 | 5,000,000 | 20,000,000 | OK |

At ~4.6k snapshots/day, critical (1M) in ~**188 days** if unchecked.

---

## Step 5 — Query pressure

Hot slice ≤15 queries enforced; log bulk limit 3000 remains largest bounded historical read. Measurement endpoint: **873 ms**, metadata-only.

---

## Step 6 — Risk scores

| Area | Score |
|------|-------|
| **Platform** | **HIGH** |
| **`dashboard_snapshots`** | **HIGH** |
| All other measured tables | LOW |

---

## Step 7 — Archive priority

1. **`dashboard_snapshots`** — 136,894 archivable rows (append-only confirmed)
2. `recovery_truth_timeline_events` — after 180d policy
3. `cart_recovery_logs` — after 365d policy

---

## Step 8 — Phase 3 recommendations

1. Implement `dashboard_snapshots_archive` (superseded >30d)
2. Weekly curl/probe; alert at 200k snapshot rows
3. Deploy `movement_snapshots` when migration lands

---

## Success criteria

| Criterion | Status |
|-----------|--------|
| Production row counts measured | ✅ |
| Growth quantified | ✅ |
| Archive priority evidence-based | ✅ |

**Artifacts:** `scripts/_data_growth_measurement_v1_out/production_measurement_report.json`  
**Commits:** `c06b7c0`, `7438512`
