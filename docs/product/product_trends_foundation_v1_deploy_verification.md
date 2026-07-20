# Product Trends Foundation V1 — Deploy Verification

**Host:** https://smartreplyai.net  
**Store:** `demo`

## Checks

```bash
pytest tests/test_product_trends_foundation_v1.py -q
python scripts/_verify_product_trends_foundation_v1.py --base https://smartreplyai.net --store demo
```

Expect probe `ok: true`, `deterministic: true`, `consumes_metrics_only: true`, `table_exists: true`.

`GET /dev/product-trends-foundation?store=demo&trend_window=d7`

Kill switch: `CARTFLOW_PRODUCT_TRENDS_FOUNDATION_V1=0`
