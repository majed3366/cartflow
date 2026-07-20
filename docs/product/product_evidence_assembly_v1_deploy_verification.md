# Product Evidence Assembly Foundation V1 — Deploy Verification

**Host:** https://smartreplyai.net  
**Store:** `demo`

```bash
pytest tests/test_product_evidence_assembly_v1.py -q
python scripts/_verify_product_evidence_assembly_v1.py --base https://smartreplyai.net --store demo
```

Expect: `ok: true`, `deterministic: true`, `inputs_metrics_and_trends_only: true`, bundles/items > 0.

`GET /dev/product-evidence-assembly?store=demo&assembly_window=d7`

Kill switch: `CARTFLOW_PRODUCT_EVIDENCE_ASSEMBLY_V1=0`
