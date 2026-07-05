# CartFlow Knowledge Producer Metadata Implementation V1

**Status:** Implemented — producer-side metadata for Knowledge Routing consumption  
**Date (UTC):** 2026-07-05  
**Scope:** Standardized publisher metadata on governed producers only — **not** Knowledge Routing  
**Authority:** Implements [`knowledge_production_standardization_v1.md`](knowledge_production_standardization_v1.md) (KPUB-1…KPUB-10)  
**Audience:** Engineering  

---

## Executive summary

Every governed producer now emits the **Knowledge Publisher Contract** as additive metadata. Merchant wording, decision logic, insight generation, and surface behavior are **unchanged**.

Knowledge Routing Implementation V1 can consume standardized items without producer-specific integration logic.

---

## What changed

### New module

| Module | Role |
|--------|------|
| `services/knowledge_producer_metadata_v1.py` | Shared `knowledge_id` minting, traceability, validation, enrich helpers |

### Producer wiring

| Producer | Attach point | Metadata added |
|----------|--------------|----------------|
| **Merchant Explanation V1** | `attach_merchant_explanation_v1` | Full contract on `merchant_explanation_v1` |
| **Merchant Decision Layer V1** | `build_cart_row_merchant_decisions_v1`, `build_kl_observation_decision_v1` | Full contract on each published decision |
| **Knowledge Layer API** | `routes/knowledge.py` → `enrich_knowledge_report_producer_metadata_v1` | Full contract on each insight + report marker |

### Enrichment order (KL API)

```
build_knowledge_report
  → enrich_knowledge_report_claim_evidence_v1
  → enrich_knowledge_report_producer_metadata_v1   ← insight knowledge_id
  → enrich_knowledge_report_merchant_decisions_v1  ← links insight knowledge_id
```

---

## Publisher contract (implemented fields)

All items include:

`knowledge_version`, `knowledge_id`, `knowledge_type`, `source_domain`, `evidence_ids`, `proof_sources`, `decision_ids`, `explanation_id`, `confidence`, `merchant_visibility`, `admin_visibility`, `eligible_surfaces`, `action_required`, `attention_level`, `aggregation_key`, `narrative_role`, `expiration_rule`, `traceability`

**Not implemented (Routing scope):** `routing_priority` — assigned by future Knowledge Routing engine only.

---

## Knowledge ID examples (live)

| Producer | Example |
|----------|---------|
| Explanation | `expl:return_without_purchase:demo-store:rk_abc123` |
| Decision | `dec:decision_monitor_return:demo-store:monitor:rk_abc123` |
| KL insight | `kl:hesitation_top_reason:demo-store:7d` |

Rules: deterministic, reproducible, no random IDs — per standardization §3.

---

## Traceability block

```json
{
  "origin_layer": "merchant_explanation",
  "origin_identifier": "return_without_purchase",
  "source_records": ["rk_abc123"],
  "producer_version": "v1",
  "created_from": ["customer_lifecycle_state", "merchant_proof_surface_v1", "merchant_explanation_v1"],
  "published_at": "2026-07-05T16:00:00+00:00"
}
```

Decisions may include `linked_explanation_id` or `linked_insight_knowledge_id` in traceability.

---

## Backward compatibility

- All existing payload fields preserved  
- Metadata is **additive** — consumers ignoring new fields continue to work  
- Snapshot slim allowlist extended with metadata keys on `merchant_explanation_v1`  
- No UI, Brief, Composer, or routing behavior changes  

---

## Tests

| File | Coverage |
|------|----------|
| `tests/test_knowledge_producer_metadata_v1.py` | ID stability, traceability, all three producers, KL decision link |
| `tests/test_merchant_explanation_v1.py` | Attach metadata presence |
| `tests/test_merchant_decision_execution_v1.py` | Existing decision tests (unchanged behavior) |

Run:

```bash
python -m pytest tests/test_knowledge_producer_metadata_v1.py tests/test_merchant_explanation_v1.py tests/test_merchant_decision_execution_v1.py -q
```

---

## Explicitly out of scope (unchanged)

- Knowledge Routing engine  
- `routing_priority` assignment  
- Daily Brief Composer migration  
- KL JS selection (`pickTopInsights`)  
- Cart detail presentation  
- Notifications / monthly summary  

---

## Next step

**Knowledge Routing Implementation V1** — consume `knowledge_id`-standardized producer output; assign `routing_priority`; migrate Composer V2 as first surface consumer.

---

## Related documents

| Document | Role |
|----------|------|
| [`knowledge_production_standardization_v1.md`](knowledge_production_standardization_v1.md) | Ratified standard |
| [`knowledge_routing_foundation_v1.md`](knowledge_routing_foundation_v1.md) | Routing contract |
| [`knowledge_routing_readiness_review_v1.md`](knowledge_routing_readiness_review_v1.md) | Pre-implementation gate |
