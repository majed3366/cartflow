# Observation Foundation V1

**Status:** Foundation (canonical observations + correlations)  
**Date (UTC):** 2026-07-24  
**Flag:** `CARTFLOW_OBSERVATION_FOUNDATION_V1` (default ON)  
**Module:** `services/observation_foundation_v1/`

## Law

- Observe and correlate only.
- **No UI. No Home. No Decision wording. No AI.**
- Consumes Product Signal Collection (and derived repeats).
- Does not create Business Findings.

```text
Platform truth / Product Signal Collection
        ↓
Observation Foundation V1   ← THIS LAYER
  • Observation Model
  • Correlation Model (Product → Behavior → Reason → Return → Purchase)
        ↓
Observation Reality Validation V1 (COMPLETED & RELEASED)
  • Merchant-visible Home observations (statement + action + confidence)
        ↓
Product Intelligence V1 (not started — separate authorization required)
```

---

## 1. Observation Model

| Observation | Subject | Evidence status | Source |
|-------------|---------|-----------------|--------|
| `product_view_observed_v1` | product | **unavailable** | `product_viewed` deferred |
| `product_open_observed_v1` | product | **unavailable** | no durable open event |
| `cart_add_observed_v1` | product | **wired** | `product_cart_added` |
| `cart_remove_observed_v1` | product | **wired** | `product_cart_removed` |
| `checkout_start_observed_v1` | product | **partial** | `product_checkout_touched` |
| `purchase_observed_v1` | product | **wired** | `product_purchased` |
| `return_to_product_observed_v1` | product | **unavailable** | returns are store-scoped |
| `return_to_store_observed_v1` | customer | **wired** | `product_customer_returned` |
| `time_spent_observed_v1` | product | **unavailable** | no dwell persist |
| `hesitation_reason_observed_v1` | reason | **wired** | `product_interest_hesitation` |
| `whatsapp_interaction_observed_v1` | customer | **partial** | recovery timeline signals |
| `repeat_visit_observed_v1` | customer | **derived** | ≥2 returns / customer |
| `repeat_purchase_observed_v1` | customer | **derived** | ≥2 purchases / customer |

API: `observation_catalog_dict_v1()` · assembly: `assemble_observation_foundation_v1(store_slug)`.

---

## 2. Correlation Model

**Chain:** Product → Customer behavior → Reason → Return → Purchase

| Kind | Meaning |
|------|---------|
| `product_customer_behavior_v1` | Product linked to cart/return behavior |
| `behavior_reason_v1` | Behavior linked to hesitation reason |
| `reason_return_v1` | Reason linked to return |
| `return_purchase_v1` | Return linked to purchase outcome |
| `product_interest_conversion_v1` | Interest (ATC) vs purchase |
| `reason_strength_compare_v1` | Shipping vs price reason mass |
| `repeat_return_without_purchase_v1` | ≥2 returns, 0 purchases |
| `absent_reason_evidence_v1` | Reason family present, quality tokens absent |

---

## 3. Supported evidence (statement capability)

| Capability | Example statement | Requires |
|------------|-------------------|----------|
| `high_interest_low_conversion` | The product has high interest but low conversion. | ATC≥2, purchase=0 |
| `shipping_stronger_than_price` | Shipping evidence is stronger than price evidence. | Hesitation tokens shipping > price |
| `repeated_return_without_purchase` | Customers repeatedly return without purchasing. | return≥2, purchase=0 |
| `no_quality_issue_evidence` | No evidence currently supports a quality issue. | Hesitation present, quality tokens=0 |

These are **correlation capabilities**, not merchant UI copy.

---

## 4. Readiness assessment — Product Intelligence V1

| Verdict | Meaning |
|---------|---------|
| **GO** | Structural catalog OK + store has observations + ≥1 statement capability ready |
| **CONDITIONAL** | Catalog OK; store lacks correlated mass |
| **NO-GO** | Foundation disabled or catalog insufficient |

**Blockers for full Product Intelligence V1 (even on GO):**

1. No durable product views  
2. No time-spent / dwell  
3. No return-to-product (only return-to-store)  
4. No distinct product-open  

**Assessment rule:** Product Intelligence V1 may speak only from wired/derived correlations. It must not invent view/dwell/quality claims without those observations.

Probe (code): `assess_product_intelligence_readiness_v1(store_slug)`.

---

## 5. Explicit non-goals

- Home / Decision Experience / MEIF changes  
- Findings generation  
- Scoring, ranking, recommendations  
- New capture pipelines for views/dwell (catalog marks gaps only)

## STOP
