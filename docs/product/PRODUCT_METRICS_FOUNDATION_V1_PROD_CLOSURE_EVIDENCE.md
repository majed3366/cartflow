# Product Metrics Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-20  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `af864dcf8947e898c3fbf7009f9e4a94113dfd67` (PR #19)

---

## 1. Pull request merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#19](https://github.com/majed3366/cartflow/pull/19) | Product Metrics Foundation V1 | `af864dcf8947e898c3fbf7009f9e4a94113dfd67` |

**Source commit:** `d7eba08` on `deploy/product-metrics-foundation-v1`

---

## 2. Scope confirmed

| Check | Result |
|-------|--------|
| Consumes Product Signals only | **Pass** — reads `product_signal_events` |
| No UI / dashboard projection reads | **Pass** |
| No trends / health / ranking / decisions | **Pass** |
| One canonical definition per metric | **Pass** — `product_metrics_types_v1` / architecture §2 |
| Deterministic computation | **Pass** — `pmf_v1_count` + fingerprint |
| No new merchant UI | **Pass** — diagnostic `/dev` only |

---

## 3. Production deployment

| Item | Evidence |
|------|----------|
| Railway redeploy | Live probe after PR #19 merge to `main` |
| `/health` | HTTP 200 |
| Home | HTTP 200 |
| `/dev/product-metrics-foundation` | HTTP 200 JSON |
| Kill switch | `CARTFLOW_PRODUCT_METRICS_FOUNDATION_V1=0` |

---

## 4. Verification script

```bash
python scripts/_verify_product_metrics_foundation_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true` (exit 0)

| Field | Value |
|-------|-------|
| `http_status_probe` | 200 |
| `probe.table_exists` | true |
| `probe.deterministic` | true |
| `fingerprint_match` | true (two consecutive probe calls) |
| `probe.signal_row_count` | **16** (final verify run) |
| `probe.migration_satisfied` | true |
| `fingerprint_match` | **true** (`983fd920…`) |

---

## 5. Demo Merchant metrics (final probe)

`GET https://smartreplyai.net/dev/product-metrics-foundation?store=demo`

| Metric | Value |
|--------|------:|
| `cart_added_count` | **7** |
| `cart_abandoned_count` | **1** |
| `evidence_linked_count` | **8** |

| Integrity | Value |
|-----------|-------|
| `deterministic` | **true** |
| `canonical_fingerprint` | `983fd920a75baa173e4943ac37dfa208b6df4a12b2c21feb6e6d87f703f3793e` |
| `materialized_row_count` | **10** |
| `non-allowlisted stores` | blocked (`store_not_allowlisted`) |
| `alembic_stamped_exact` | false (`alembic_version` null) |
| `migration_satisfied` | **true** (table via `create_all`) |

---

## 6. Acceptance checklist

| Criterion | Status |
|-----------|--------|
| Governed platform layer exists | **Yes** |
| One canonical definition per metric | **Yes** |
| Metrics consume only Product Signals | **Yes** |
| Ownership + Signal→Metric mapping documented | **Yes** — `docs/architecture/product_metrics_foundation_v1.md` |
| No trend / decision / presentation logic | **Yes** |
| Production deployment | **Yes** |
| Deterministic generation verified | **Yes** |

---

## 7. Closure

**Product Metrics Foundation V1 is CLOSED in production** with governed Demo evidence on 2026-07-20.

**STOP** — do not start Trends / Health / Ranking / Decision / Home product-performance presentation until owner confirms.
