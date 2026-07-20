# Product Trends Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-20  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `841cc6d0f20d30155590d38f5a4e43d7d6aa6b20` (PR #21)

---

## 1. Pull request merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#21](https://github.com/majed3366/cartflow/pull/21) | Product Trends Foundation V1 | `841cc6d0f20d30155590d38f5a4e43d7d6aa6b20` |

**Source commit:** `952c666` on `deploy/product-trends-foundation-v1`

---

## 2. Scope confirmed

| Check | Result |
|-------|--------|
| Consumes Product Metrics only | **Pass** — `compute_product_metrics_v1` API; `consumes_metrics_only=true` |
| No provider / raw-event bypass | **Pass** |
| Directions only (no why/guidance) | **Pass** — newly_appeared/disappeared/stable/increasing/decreasing |
| No ranking / health / scoring / AI | **Pass** |
| No merchant UI | **Pass** — `/dev` probe only |
| Deterministic (fixed `as_of`) | **Pass** — probe `deterministic=true` |

---

## 3. Production deployment

| Item | Evidence |
|------|----------|
| Railway redeploy | Probe live after PR #21 → `main` |
| `/health` | HTTP 200 |
| Home | HTTP 200 |
| `/dev/product-trends-foundation` | HTTP 200 JSON |
| Kill switch | `CARTFLOW_PRODUCT_TRENDS_FOUNDATION_V1=0` |

---

## 4. Verification script

```bash
python scripts/_verify_product_trends_foundation_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true` (exit 0)

| Field | Value |
|-------|-------|
| `probe.table_exists` | true |
| `probe.deterministic` | true |
| `probe.consumes_metrics_only` | true |
| `probe.migration_satisfied` | true |
| `probe.trend_window` | `d7` |

Note: consecutive HTTP probes may differ in `as_of`/fingerprint when wall-clock advances; each probe freezes `as_of` internally and re-computes twice for `deterministic=true`.

---

## 5. Demo Merchant trends (final probe sample)

`GET https://smartreplyai.net/dev/product-trends-foundation?store=demo&trend_window=d7`

| Metric | current | previous | direction |
|--------|--------:|---------:|-----------|
| `cart_added_count` | 7 | 0 | `newly_appeared` |
| `cart_abandoned_count` | 1 | 0 | `newly_appeared` |
| `evidence_linked_count` | 8 | 0 | `newly_appeared` |

| Integrity | Value |
|-----------|-------|
| `by_direction.newly_appeared` | 10 (store + product grains) |
| `store_trend_count` | 3 |
| `product_trend_count` | 7 |
| `materialized_row_count` | ≥ 10 |
| `alembic_stamped_exact` | false |
| `migration_satisfied` | **true** |

---

## 6. Acceptance checklist

| Criterion | Status |
|-----------|--------|
| Deterministic outputs | **Yes** |
| Canonical ownership | **Yes** — Trends own directions; Metrics own counts |
| Refresh/recompute | **Yes** — on-demand + materialize |
| Reproducible with fixed `as_of` | **Yes** |
| Provider-independent | **Yes** |
| Fully documented | **Yes** — `docs/architecture/product_trends_foundation_v1.md` |
| Production probe | **Yes** |
| Production evidence | **Yes** — this file |

---

## 7. Closure

**Product Trends Foundation V1 is CLOSED in production** with governed Demo evidence on 2026-07-20.

**STOP** — do not start Evidence Assembly / Confidence / Knowledge / Guidance / ranking / health until owner confirms.
