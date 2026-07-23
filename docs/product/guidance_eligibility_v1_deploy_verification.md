# Guidance Eligibility Foundation V1 — Deploy Verification

**Host:** https://smartreplyai.net  
**Store:** `demo`

```bash
pytest tests/test_guidance_eligibility_v1.py -q
python scripts/_verify_guidance_eligibility_v1.py --base https://smartreplyai.net --store demo
```

Expect: `ok: true`, `deterministic: true`, `inputs_knowledge_foundation_only: true`, `one_status_per_subject: true`, store sample status present.

`GET /dev/guidance-eligibility?store=demo&assembly_window=d7`

Kill switch: `CARTFLOW_GUIDANCE_ELIGIBILITY_V1=0`
