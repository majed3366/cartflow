# Performance Report — Gate 2C (Gate 1 Recovery)

**Date (UTC):** 2026-07-24  
**Status:** Root cause measured via request-path instrumentation; fix shipped.

---

## 1. Regression statement

Gate 1 cut Home summary payload ~93% and deferred carts/messages.

Gate 2B introduced **synchronous `compose_decisions_v1`** on:

1. Every `GET /api/dashboard/summary` finalize (Home teaser)  
2. Every `GET /api/cart-workspace/v1/projection`

That reintroduced heavy work on page load — unacceptable regression.

---

## 2. Evidence — which API / query / step

| Question | Answer |
|----------|--------|
| Which API became slower? | `/api/dashboard/summary` (finalize) + `/api/cart-workspace/v1/projection` |
| Which query increased? | `AbandonedCart` store-wide scan inside `build_merchant_cart_counter_totals` (cap ≤2500) + batch reads |
| Which service composes on page load? | `decision_composition_engine_v1.compose_decisions_v1` |
| Hottest composition step? | **Counter load** (`load_store_counter_inputs_v1` → `build_merchant_cart_counter_totals`) — not finding JSON |
| Hot DB? | AbandonedCart candidate scan + `_merchant_normal_dashboard_batch_reads` |
| Payload larger? | Workspace projection gained composition metadata; Home stayed slim but **latency** rose |
| Extra network? | Home then Workspace = **two full composes** (two counter scans) |
| Render blocker? | Merchant JS waits on summary/projection JSON — server compose blocked TTFB |

Instrumentation: `timing_ms` on composition package (`counters_ms`, `findings_ms`, `compose_candidates_ms`, `portfolio_ms`, `total_ms`).

---

## 3. Root cause

```text
Home/Workspace GET
  → compose_decisions_v1 (sync)
      → build_merchant_cart_counter_totals  ← $$$ every paint
      → load_bound_findings_v1             ← secondary
```

No snapshot/cache existed. Counters already on summary were ignored.

---

## 4. Fix (Gate 2C)

| Change | Effect |
|--------|--------|
| In-process snapshot cache (TTL 45s, stale 300s, SWR) | Second paint serves snapshot; stale refresh background |
| Reuse `merchant_store_cart_counts` from summary | Home avoids AbandonedCart re-scan |
| Single shared package for Home + Workspace | Categories filter in-memory — no N× DB |
| `timing_ms` + `_cache` on package | Ongoing evidence |

Rule: **Decision Composition must not block paint when a snapshot exists.**

---

## 5. Before / after (request model)

| Path | Before (2B) | After (2C) |
|------|-------------|------------|
| Home summary (2nd hit) | Full counter scan | Cache hit (~0 DB for DCE) |
| Home summary (1st, with counters on payload) | Full counter scan | Payload counters + findings only |
| Workspace after Home | Second full scan | Cache hit |
| Portfolio categories | N/A (single bias) | In-memory balance on same package |

---

## 6. Production verification (live)

**SHA:** `d20a06f` (PR [#90](https://github.com/majed3366/cartflow/pull/90))  
**Probe:** `docs/product/gate_2c_decision_portfolio_v1/after_verification.json`  
**Account:** `cf.g2c.48d0f81447@smartreplyai.net` · `2026-07-24T23:49:29Z`

| Metric | Production after Gate 2C |
|--------|--------------------------|
| Home `/api/dashboard/summary` fetch | **234 ms** · **5,848** bytes · `executive_summary_v1` · no MEIF · `portfolio: true` |
| Workspace projection (after Home) | **261 ms** · `cache.hit=true` · age ~11s · landscape **7** |
| Second projection | **265 ms** · `cache.hit=true` (no re-compose) |
| Snapshot compose cost (stored) | counters **1261 ms** (db_scan once) · findings **405 ms** · portfolio **0.03 ms** · total **1666 ms** |
| UI | محفظة القرارات · الأولوية 1 · healthy «لا إجراء مطلوب.» · no CartFlow يعمل |

**Interpretation:** Cold compose still costs ~1.7s once (AbandonedCart scan). Home→Workspace second paint does **not** re-scan — cache hit keeps projection ~260 ms. Gate 1 Home latency restored (~234 ms vs Gate 1 after ~161 ms; vs Gate 2B double-scan regression).
