# Guidance Routing Foundation V1 — Deploy Verification

**Host:** https://smartreplyai.net  
**Store:** `demo`

```bash
pytest tests/test_guidance_routing_v1.py -q
python scripts/_verify_guidance_routing_v1.py --base https://smartreplyai.net --store demo
```

Expect: `ok: true`, `deterministic: true`, `consumes_commercial_guidance_only: true`, `accounting_ok: true`.

`GET /dev/guidance-routing?store=demo&assembly_window=d7`

Kill switch: `CARTFLOW_GUIDANCE_ROUTING_FOUNDATION_V1=0`
