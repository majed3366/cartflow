# Product Metrics Foundation V1 — Deploy Verification

**Date (UTC):** 2026-07-20  
**Host:** https://smartreplyai.net  
**Store:** `demo`

## Pre-deploy

- [ ] Architecture: `docs/architecture/product_metrics_foundation_v1.md`
- [ ] Tests: `pytest tests/test_product_metrics_foundation_v1.py -q`
- [ ] PR merged to `main`
- [ ] Railway redeploy complete

## Post-deploy

```bash
python scripts/_verify_product_metrics_foundation_v1.py --base https://smartreplyai.net --store demo
```

Expect:

- `ok: true`
- `probe.table_exists: true`
- `probe.deterministic: true`
- `fingerprint_match: true`
- `probe.signal_row_count > 0`
- `probe.by_metric_key` includes cart/evidence counts when Demo signals exist

Probe URL:

`GET /dev/product-metrics-foundation?store=demo`

## Smoke (no merchant UI change)

- `GET /` → 200
- `GET /health` → 200

## Kill switch

```text
CARTFLOW_PRODUCT_METRICS_FOUNDATION_V1=0
```

Does not delete `product_metric_values` or signals.
