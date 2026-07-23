# Evidence Confidence Foundation V1 — Deploy Verification

**Host:** https://smartreplyai.net  
**Store:** `demo`

```bash
pytest tests/test_evidence_confidence_v1.py -q
python scripts/_verify_evidence_confidence_v1.py --base https://smartreplyai.net --store demo
```

Expect: `ok: true`, `deterministic: true`, `inputs_evidence_assembly_only: true`, `evaluation_count > 0`.

`GET /dev/evidence-confidence?store=demo&assembly_window=d7`

Kill switch: `CARTFLOW_EVIDENCE_CONFIDENCE_V1=0`
