# Business Facts Contract V1

**Layer:** Business Understanding (first extraction layer)  
**Not:** AI · prediction · recommendations · Product Intelligence

---

## Philosophy

| Layer | Answers |
|-------|---------|
| Observations | What happened? |
| **Business Facts** | **What does this mean for the merchant?** |

CartFlow exposes **business truths**, not platform observations.

---

## Fact types

- `product_demand`
- `conversion`
- `customer_behaviour`
- `recovery`
- `communication`
- `store_health`

---

## Required fields

| Field | Role |
|-------|------|
| `fact_type` | Category |
| `subject` | Product or store (`kind`, `id`, `name_ar`) |
| `business_meaning_ar` | Merchant-readable meaning |
| `evidence` | Source kinds, observation ids, correlation kinds, refs |
| `confidence` | level / ar / score / source |
| `freshness` | status + as_of_utc |
| `impact_category` | revenue / conversion / demand / operations / communication / store_health |

`recommendation` must be **null** in V1.

---

## Extraction sources (only)

1. Validated ORV / admitted observation findings  
2. Correlations (via admitted capabilities)  
3. Operational truth **domain attention** + executive understanding language  

**Forbidden:** generating fact text from bare counters (`waiting_total`, queue size, etc.).

---

## Routing

| Surface | Consumes |
|---------|----------|
| Home | Product + store facts → teasers / sections |
| Decision Workspace | Workspace-eligible facts as evidence cards |
| Decision Composition | Attaches facts package into Business Understanding |

---

## Module

`services/business_facts_v1/` — flag · contract · extract · registry · route · attach  
Probe: `GET /dev/business-facts?store=demo`
