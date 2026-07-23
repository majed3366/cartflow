# Knowledge Foundation V1 — Deploy Verification

**Host:** https://smartreplyai.net  
**Store:** `demo`

```bash
pytest tests/test_knowledge_foundation_v1.py -q
python scripts/_verify_knowledge_foundation_v1.py --base https://smartreplyai.net --store demo
```

Expect: `ok: true`, `deterministic: true`, `inputs_evidence_confidence_only: true`, `all_statements_reference_confidence: true`.

`GET /dev/knowledge-foundation?store=demo&assembly_window=d7`

Kill switch: `CARTFLOW_KNOWLEDGE_FOUNDATION_V1=0`
