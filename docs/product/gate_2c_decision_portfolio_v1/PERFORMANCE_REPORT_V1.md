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

## 6. Production verification

See `after_verification.json` after deploy — assert `gate_2c`, cache hit on second projection, no status chrome, portfolio landscape present.
