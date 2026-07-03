# Data Growth Measurement v1

**Program:** CartFlow Data Growth Governance — Phase 2  
**Date (UTC):** 2026-07-03  
**Status:** Read-only measurement baseline  
**Objective:** Quantify actual growth, accumulation, and storage pressure before any archive jobs.

**Prerequisite:** `docs/data_growth_governance_v1.md` (classification, budgets, archive proposals)  
**Measurement tooling:** `services/data_growth_measurement_v1.py`, `scripts/data_growth_measurement_v1_probe.py`, `GET /dev/data-growth-measurement` (after deploy)

**Non-goals:** archive jobs, deletion, compression, TTL jobs, monitoring dashboards.

---

## Executive summary

| Finding | Detail |
|---------|--------|
| **Current scale** | Production PostgreSQL is active; all major tables are **far below** governance warning thresholds at measured counts (hundreds–low thousands, not millions). |
| **Highest structural risk** | **`dashboard_snapshots`** — append-only write pattern; historical versions accumulate even when only the latest row is read. Risk is **HIGH** on pattern; row count **unknown until full DB probe** (endpoint not yet deployed to production at measurement time). |
| **Highest volume tables (measured)** | **`recovery_truth_timeline_events`** ≥ **492 rows**; **`recovery_schedules`** ≈ **419 rows**; **`cartflow-42b491`** alone holds **101** timeline events. |
| **Growth rate** | Pilot-scale: timeline ~**0.8–16 events/day** implied from partial samples; not yet acceleration-tier. |
| **Archive priority (evidence-based)** | 1) `dashboard_snapshots` 2) `recovery_truth_timeline_events` 3) `cart_recovery_logs` |
| **Dashboard budgets** | Hot slice **≤15 queries** enforced; log bulk **limit(3000)** remains the largest bounded historical read on normal-carts. |

---

## Measurement methodology

### Sources used (2026-07-03 UTC)

| Source | Scope | Notes |
|--------|-------|-------|
| **Production partial probes** | `GET /dev/recovery-health`, `GET /dev/recovery-truth` | No DB credentials required; schedule + timeline partial counts |
| **Production snapshot diagnostics** | `GET /dev/snapshot-truth-diagnostics?store_slug=cartflow-42b491` | Confirms snapshot builder active; 100 rows in latest normal_carts payload |
| **Local SQLite probe** | `scripts/data_growth_measurement_v1_probe.py` | Dev DB nearly empty — not representative of production |
| **Code inventory** | `query_pressure_inventory()` | LIMIT values and budget constants |

### Full production measurement (required for Phase 3)

Run **one** of:

```bash
# Option A — Railway shell (preferred)
railway run python scripts/data_growth_measurement_v1_probe.py

# Option B — after deploy
curl -s https://smartreplyai.net/dev/data-growth-measurement | jq .

# Option C — local with production DATABASE_URL
DATABASE_URL='postgresql://...' python scripts/data_growth_measurement_v1_probe.py
```

Output: `scripts/_data_growth_measurement_v1_out/measurement_report.json`

---

## Step 1 — Table size inventory

### Production (partial + inferred)

Database: **PostgreSQL** (confirmed via `/dev/recovery-truth` persistence block).

| Table | Current count | Est. size | Oldest / newest | Daily growth est. | Data quality |
|-------|---------------|-----------|-----------------|-------------------|--------------|
| **`recovery_truth_timeline_events`** | **≥ 492** (min from max `row_id`) | Unknown | Events observed from **2026-06-06** to **2026-07-03** | ~**16/day** if linear since first event | Partial — full count needs DB probe |
| **`recovery_schedules`** | **≈ 419** (sum of status breakdown) | Unknown | Latest failure **2026-06-13** | ~**14/day** lifetime average (pilot) | Partial from `/dev/recovery-health` |
| **`cart_recovery_logs`** | **Not measured** | Unknown | — | — | Requires full probe |
| **`dashboard_snapshots`** | **Not measured** | Unknown | Latest `cartflow-42b491` generated **2026-07-03T00:16:44Z** | **(stores × types × rebuilds)** — highest structural insert rate | Builder active; row count unknown |
| **`abandoned_carts`** | **Not measured** | Unknown | — | — | Merchant snapshot shows **61** active filter count for one store (not DB row count) |
| **`movement_snapshots`** | **Not measured** | Unknown | — | Upsert-bound | Table may be empty on prod (shadow Phase 1) |
| **`purchase_truth_records`** | **Not measured** | Unknown | — | — | Requires full probe |
| **`cf_behavioral`** | Nested in `abandoned_carts.raw_payload` | — | — | In-place merge | **65 KB** write cap per cart |

### Per-store timeline sample (production)

| Store slug | Timeline rows |
|------------|---------------|
| `cartflow-42b491` | **101** |
| `pvgate-c6e1e1-f19d35` | **12** |

### Local dev SQLite (reference only — not production)

| Table | Rows | 7d growth | 30d growth |
|-------|------|-----------|------------|
| `recovery_truth_timeline_events` | 24 | 24 | 24 |
| `stores` | 3 | 3 | 3 |
| All others | 0 | 0 | 0 |

---

## Step 2 — Snapshot accumulation

### What we know (production)

| Metric | Value |
|--------|-------|
| Snapshot mode | **Enabled** (`snapshot_mode_enabled: true`) |
| Latest normal_carts snapshot | Exists for `cartflow-42b491`; **stale** at probe time |
| Payload row count | **100** rows in snapshot JSON |
| Merchant filter counts (from snapshot) | all **61**, waiting **2**, sent **12**, attention **47** |
| Read pattern | **Latest row only** per `(store_slug, snapshot_type)` |
| Write pattern | **Append-only** — new row every rebuild (`version` increment) |

### What full probe measures

| Metric | Formula |
|--------|---------|
| Total rows | `COUNT(*)` on `dashboard_snapshots` |
| Versions per store | `GROUP BY store_slug, snapshot_type` |
| Historical-only rows | `SUM(count - 1)` per group |
| Rows read in practice | One per `(store_slug, snapshot_type)` |
| Rows ignored | `total - read_in_practice` |
| Historical % | `ignored / total × 100` |

### Validated locally (test fixture)

3 versions for one store/type → **2 historical-only rows (66.7%)** — confirms accumulation math in `assess_dashboard_snapshot_accumulation()`.

### Production expectation

With continuous scheduler builder loop (since 2026-06-30) and **~9 snapshot types × N stores × rebuild every 30–120s**, historical-only percentage will climb toward **>90%** unless archive is implemented. **This is the primary storage pressure vector even at pilot row counts.**

---

## Step 3 — Log growth

### Timeline events (production partial)

| Metric | Value |
|--------|-------|
| Minimum total rows | **492** |
| Max `row_id` observed | **492** |
| Avg rows per recovery (sample) | **5** events for one complete send path (`cartflow-42b491:cf_cart_3fa…`) |
| Largest merchant (sampled) | `cartflow-42b491` — **101** timeline rows |
| Est. monthly growth (pilot) | **~500 rows/month** if current send volume holds |

### Recovery logs (production)

**Not directly measured** in this phase. From governance v1 and code paths, expect **~2–8 rows per recovery** (steps, skips, provider events).

### Recovery schedules (production partial)

Status breakdown from `/dev/recovery-health`:

| Status | Count |
|--------|------:|
| completed | 216 |
| cancelled | 130 |
| skipped_resume_unsafe | 28 |
| ignored_demo_startup | 17 |
| scheduled | 10 |
| skipped_no_reason | 7 |
| skipped_demo_resume | 7 |
| failed_resume_stale | 3 |
| whatsapp_failed | 1 |
| **Total (estimated)** | **419** |

Demo/loadtest rows (`ignored_demo_startup`, `skipped_demo_resume`) = **24** — should stay isolated from merchant KPIs.

---

## Step 4 — Health thresholds

Thresholds from `docs/data_growth_governance_v1.md`. Status uses **production partial counts** where available.

| Table | Current | Warning | Critical | Status | Distance to warning |
|-------|---------|---------|----------|--------|---------------------|
| `dashboard_snapshots` | Unknown | 100,000 | 1,000,000 | **Unknown** | Run full probe |
| `recovery_truth_timeline_events` | ≥ 492 | 5,000,000 | 20,000,000 | **OK** | 99.99% headroom |
| `cart_recovery_logs` | Unknown | 5,000,000 | 20,000,000 | **Unknown** | Run full probe |
| `recovery_schedules` | ≈ 419 | 100,000 | 500,000 | **OK** | 99.6% headroom |
| `abandoned_carts` | Unknown | 500,000 | 2,000,000 | **Unknown** | Run full probe |
| `movement_snapshots` | Unknown | 100,000 | 500,000 | **Unknown** | Run full probe |
| `purchase_truth_records` | Unknown | 200,000 | 1,000,000 | **Unknown** | Run full probe |
| `cf_behavioral` | Nested | — | — | **Pattern risk** | Payload cap 65 KB |

**Approaching thresholds:** None at measured counts. **Approaching structural limits:** `dashboard_snapshots` write pattern.

---

## Step 5 — Query pressure

Verified from code (`services/data_growth_measurement_v1.py` → `query_pressure_inventory()`).

### Largest scans (bounded)

| Path | LIMIT / budget | Risk |
|------|----------------|------|
| Normal-carts log bulk | **3000** | **HIGH** — scales with store send history |
| VIP augment | **4000** | **MEDIUM** |
| Sent logs enrich | **250** | **MEDIUM** |
| Admin store scan | **400** | **LOW** |
| Due scanner | **25**/tick | **LOW** |
| Normal-carts row materialization | **50+50** | **LOW** |
| Timeline per-key | **12** | **LOW** |

### Dashboard budget compliance

| Path | Budget | Enforced |
|------|--------|----------|
| Hot slice merge | ≤ **15** queries, **25** rows, **36h** window | Yes — `dashboard_hot_slice_v1.py` |
| Snapshot read | Latest row only | Yes |
| Full live normal-carts | Soft **80** / hard **150** queries | Logged; partial on 12s wall timeout |
| Widget public-config | ≤ **2** queries (target) | Single store lookup |
| Scheduler health | ≤ **5** queries (target) | Count queries with filters |

**Historical reads on hot path:** Log bulk `limit(3000)` is the main concern — bounded but can grow heavy for high-send stores. **No unbounded `.all()`** on timeline/logs in dashboard batch path.

---

## Step 6 — Risk scores

Based on **measured growth + read frequency + hot-path exposure** (governance v1 matrix).

| Table / area | Growth | Hot-path exposure | Risk | Rationale |
|--------------|--------|-------------------|------|-----------|
| **`dashboard_snapshots`** | Unknown count; **high insert rate** | Every dashboard read (latest row) | **HIGH** | Append-only; historical bloat latent |
| **`cart_recovery_logs`** | Unknown; multi-row per recovery | Normal-carts bulk **3000** | **HIGH** | No retention; send-volume coupled |
| **`recovery_truth_timeline_events`** | ≥492; ~5/recovery | Timeline ensure, visibility | **MEDIUM** | Volume low today; append pattern |
| **`recovery_schedules`** | ≈419 | Due scanner (25/tick) | **LOW** | Bounded scanner; terminal rows accumulate slowly |
| **`abandoned_carts`** | Unknown | Every cart-event + dashboard | **MEDIUM** | Core hot table; `raw_payload` bloat |
| **`cf_behavioral`** | In-row merge | Movement visibility fallback | **MEDIUM** | 65 KB cap mitigates |
| **`movement_snapshots`** | Upsert (1/rk) | Optional bulk read | **LOW** | Good pattern if adopted |
| **`purchase_truth_records`** | ~1/conversion | Bulk by recovery_key | **LOW** | Naturally bounded |

---

## Step 7 — Archive readiness

Evidence-based priority for Phase 3:

| Priority | Table | Why first | Archivable estimate |
|----------|-------|-----------|---------------------|
| **1** | `dashboard_snapshots` | Only latest row read; continuous builder; **100% of superseded versions are cold** | All but latest per `(store_slug, type)` after **30d** |
| **2** | `recovery_truth_timeline_events` | Append-only; **≥492** rows; ~5/recovery; no retention | Rows **> 180d** |
| **3** | `cart_recovery_logs` | Multi-row per recovery; dashboard uses **≤3250** logs max per request | Rows **> 365d** |
| 4 | Terminal `recovery_schedules` | **≈419** total; ~346 terminal | Rows **> 180d** after terminal |
| 5 | Demo/loadtest rows | **24** schedule rows tagged | **30d** isolation archive |

---

## Step 8 — Recommended Phase 3

### Immediate (before archive jobs)

1. **Deploy** `GET /dev/data-growth-measurement` to production and capture baseline JSON.
2. **Run weekly probe** via Railway shell; store reports with date stamp.
3. **Add PostgreSQL size columns** to report (`pg_total_relation_size`) — already supported when dialect is PostgreSQL.

### Archive implementation order

1. **`dashboard_snapshots_archive`** — move superseded versions > 30d; keep latest online.
2. **`recovery_truth_timeline_events_archive`** — batch move > 180d.
3. **`cart_recovery_logs_archive`** — batch move > 365d.

### Query hardening (parallel)

1. Narrow log bulk from **3000** to **page recovery_key set** only.
2. Add VIP wall guard + snapshot layer (match normal-carts discipline).

### Success criteria (Phase 2 — this document)

| Criterion | Status |
|-----------|--------|
| Growth is measurable | ✅ Tooling + methodology; full prod counts pending deploy/DB URL |
| Biggest risks quantified | ✅ Structural HIGH on snapshots/logs; partial row counts |
| Archive priorities evidence-based | ✅ Ordered 1–3 with rationale |

---

## Appendix

### Artifacts

| File | Purpose |
|------|---------|
| `scripts/_data_growth_measurement_v1_out/production_partial_report.json` | Production partial probes (2026-07-03) |
| `scripts/_data_growth_measurement_v1_out/measurement_report.json` | Local DB full report |
| `services/data_growth_measurement_v1.py` | Measurement logic |
| `tests/test_data_growth_measurement_v1.py` | Accumulation + endpoint tests (3/3 pass) |

### Production probe commands used

```bash
python scripts/data_growth_measurement_v1_probe.py
# Fetches partial production + local DB report
```

### Related contracts

- **C-DATA-3** — Growth must be measurable → Phase 2 tooling satisfies intent; operationalize with weekly probe.
- **C-DATA-4** — Query cost visible → `query_pressure` block in measurement report.
