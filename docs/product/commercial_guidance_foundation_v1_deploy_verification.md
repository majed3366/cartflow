# Commercial Guidance Foundation V1 — Deploy Verification

**Host:** https://smartreplyai.net  
**Store:** `demo`

```bash
pytest tests/test_commercial_guidance_v1.py -q
python scripts/_verify_commercial_guidance_v1.py --base https://smartreplyai.net --store demo
```

Expect: `ok: true`, `deterministic: true`, `consumes_guidance_eligibility_only: true`, `registry_valid: true`.

`GET /dev/commercial-guidance?store=demo&assembly_window=d7`

Kill switch: `CARTFLOW_COMMERCIAL_GUIDANCE_FOUNDATION_V1=0`
