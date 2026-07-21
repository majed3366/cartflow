# Merchant Presentation Foundation V1 — Deploy Verification

**Host:** https://smartreplyai.net  
**Store:** `demo`

```bash
pytest tests/test_merchant_presentation_v1.py -q
python scripts/_verify_merchant_presentation_v1.py --base https://smartreplyai.net --store demo
```

Expect: `ok: true`, `deterministic: true`, `consumes_guidance_routing_only: true`, `accounting_ok: true`.

`GET /dev/merchant-presentation?store=demo&assembly_window=d7`

Kill switch: `CARTFLOW_MERCHANT_PRESENTATION_FOUNDATION_V1=0`
