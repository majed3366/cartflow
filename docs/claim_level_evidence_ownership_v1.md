# CartFlow Claim-Level Evidence Ownership V1

**Date (UTC):** 2026-07-04  
**Status:** Implemented — presentation architecture  
**Governance:** Proof of Value PG-3, PG-8; Merchant Evidence Registry Foundation

---

## Architectural principle

> **Evidence belongs to the claim, not to the section.**

Each merchant-visible insight owns:

- Confidence  
- Evidence source (`evidence_id` → registry label)  
- Optional claim footnote (`claim_evidence_source_ar`)

Cards remain truthful if moved to another page (Daily Brief, Understanding, etc.).

---

## Implementation

| Layer | Module | Role |
|-------|--------|------|
| Registry (unchanged entries) | `merchant_evidence_registry_v1.py` | Single label authority |
| Claim mapping | `merchant_claim_evidence_v1.py` | `insight_key` → `evidence_id` |
| API | `routes/knowledge.py` | `enrich_knowledge_report_claim_evidence_v1()` |
| UI | `merchant_knowledge_layer.js` | Per-card الثقة + المصدر; **no section footnote** |

### Insight → evidence mapping (examples)

| insight_key | evidence_id | Label |
|-------------|-------------|-------|
| `conversion_cart_to_purchase` | `purchase_record` | سجل الشراء |
| `hesitation_top_reason` | `customer_response` | سبب التردد أو رد العميل |
| `recovery_bottleneck` | `recovery_record` | سجل الاسترجاع |
| `traffic_visitor_unavailable` | `visitor_behavior` | حركة الزيارات |
| `store_health_overview` | `store_activity` | بيانات المتجر |

Future insights: add one row to `INSIGHT_CLAIM_EVIDENCE_ID` or use category fallback.

---

## Card contract (JSON)

Each insight in `/api/knowledge/report`:

```json
{
  "insight_key": "recovery_bottleneck",
  "confidence": "medium",
  "evidence_id": "recovery_record",
  "evidence_label_ar": "سجل الاسترجاع",
  "claim_evidence_source_ar": "مصدر الدليل: سجل الاسترجاع"
}
```

Registry catalog attached without `section_source_ar`.

---

## Regression

No changes to KL insight generation, metrics, confidence computation, or truth layers.

Tests: `tests/test_merchant_claim_evidence_v1.py`
