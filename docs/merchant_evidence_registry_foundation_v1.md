# CartFlow Merchant Evidence Registry Foundation V1

**Date (UTC):** 2026-07-04  
**Status:** Implemented — presentation architecture  
**Governance:** [`proof_of_value_governance_v1.md`](proof_of_value_governance_v1.md) PG-3, PG-8, PV-7

---

## Purpose

The **Merchant Evidence Registry** is the permanent, governed source of merchant-visible evidence wording. Every proof surface resolves labels through `services/merchant_evidence_registry_v1.py` — never through hard-coded JavaScript or duplicated Python strings.

**Principle:** One evidence source → one merchant label.

---

## Registry design

Each entry defines:

| Field | Role |
|-------|------|
| `evidence_id` | Stable identifier (e.g. `purchase_record`, `store_activity`) |
| `label_ar` | Merchant-facing label — no internal architecture terms |
| `description_ar` | Maintainer description (not shown in UI by default) |
| `eligible_domains` | Recovery / Understanding / Decision / Operational / Commercial |
| `confidence_compat` | Compatible confidence vocabulary |
| `status` | `active` or `future` (reserved for upcoming surfaces) |
| `tier0_keys` | Optional mapping from engineering Tier-0 keys |
| `evidence_origin` | `store` (merchant-operational) or `platform` (CartFlow-composed intelligence) |

### Active entries (v1)

| evidence_id | Merchant label | Origin | Consumer |
|-------------|----------------|--------|----------|
| `customer_journey` | مسار العميل | store | Proof Surface (lifecycle) |
| `purchase_record` | سجل الشراء | store | Proof Surface (purchase) |
| `recovery_record` | سجل الاسترجاع | store | Proof Surface (recovery steps) |
| `message_delivery` | حالة رسائل WhatsApp | store | Proof Surface (provider step) |
| `customer_response` | سبب التردد أو رد العميل | store | Proof Surface (reason) |
| `store_activity` | بيانات المتجر | store | Knowledge Layer claims (e.g. store health, traffic trends) |

### Future entries (registry-only — no UI until activated)

| evidence_id | Merchant label | Origin | Intended surface |
|-------------|----------------|--------|------------------|
| `cartflow_analytics` | بيانات CartFlow | platform | Daily Brief, Decision Engine |
| `behavior_truth` | سلوك العملاء | store | Merchant Understanding |
| `product_history` | سجل المنتجات | store | Product Intelligence |
| `campaign_data` | بيانات الحملات | store | Operational |
| `visitor_behavior` | حركة الزيارات | store | Traffic insights |
| `pricing_history` | سجل الأسعار | store | Product Intelligence |
| `support_history` | سجل الدعم | store | Operational |
| `attribution_record` | ربط الإيراد بالاسترجاع | store | Attribution |

**Distinction:** «بيانات المتجر» = store-operational facts. «بيانات CartFlow» = platform-composed intelligence. Never interchangeable.

Adding a future source = one registry entry + surface wiring to `evidence_id`. No presentation rewrite.

---

## Consumption contract

### Backend

```python
from services.merchant_evidence_registry_v1 import (
    merchant_evidence_for_tier0_key,
    attach_merchant_evidence_registry_v1,
)
```

- **Proof Surface:** `enrich_proof_evidence_fields()` / `enrich_step_evidence_fields()` on bundle compose
- **Knowledge Layer API:** `enrich_knowledge_report_claim_evidence_v1(payload)` — each insight owns `evidence_id`; registry catalog attached without section-level proof (see **`docs/claim_level_evidence_ownership_v1.md`**)

### Merchant UI

JSON field: `merchant_evidence_registry_v1` on `/api/knowledge/report`  
Proof rows: `merchant_proof_surface_v1.evidence_id`, `evidence_label_ar`, `evidence_source_ar`

**Rule:** JavaScript reads labels from payload — never defines evidence source strings.

---

## Governance compliance

| Rule | Status |
|------|--------|
| PG-3 Presentation composes proof | **Pass** — registry is presentation layer |
| PV-7 proof source traceability | **Pass** — `evidence_id` + `proof_source` |
| No internal terminology | **Pass** — Tier-0 keys internal only |
| One label per evidence source | **Pass** — single registry module |
| Claim-level evidence ownership | **Pass** — each KL insight resolves its own `evidence_id`; no section-owned proof |

---

## Files

| File | Role |
|------|------|
| `services/merchant_evidence_registry_v1.py` | Canonical registry |
| `services/merchant_claim_evidence_v1.py` | Maps KL `insight_key` → `evidence_id`; enriches per claim |
| `services/merchant_proof_surface_v1.py` | Consumes registry on compose |
| `routes/knowledge.py` | Enriches KL report with claim-level evidence |
| `static/merchant_knowledge_layer.js` | Per-card الثقة · المصدر from claim + registry |
| `static/merchant_dashboard_lazy.js` | Reads `evidence_label_ar` from row bundle |
| `tests/test_merchant_evidence_registry_v1.py` | Registry + integration tests |

---

## Verification

- Single registry module — no duplicated evidence labels in proof surface
- No `Knowledge Layer` / `Lifecycle Truth` in merchant JSON labels
- Proof logic unchanged — confidence, steps, domains identical
- Future extensibility — `status=future` entries pre-registered
