# Commerce Intelligence → Knowledge Integration V1 — Production Closure Evidence

**Status:** PRODUCTION CLOSED  
**Date (UTC):** 2026-07-22  
**Runtime commit:** PR #41 → `main`  
**Environment:** https://smartreplyai.net  
**Store:** `demo` only  

---

## Architecture inventory & decision

| Item | Decision |
|------|----------|
| Knowledge Foundation ECF path | **Unchanged** (`generate_knowledge_v1` remains Evidence Confidence only) |
| Knowledge table | **Reused** `knowledge_statements` with additive lineage columns |
| Second Knowledge registry/table | **Not created** |
| Intake approach | Dedicated adapter `ciknow_v1` |
| Input | `commerce_intelligence_synthesis_v1` only |
| Naming | `ciknow_v1` — no collision with `cisyn_v1` / `kf_v1` |

---

## Deployment

| Item | Value |
|------|--------|
| PR | https://github.com/majed3366/cartflow/pull/41 |
| Flag | `CARTFLOW_COMMERCE_INTELLIGENCE_KNOWLEDGE_INTEGRATION_V1` (enabled) |
| Intake registry | `ciknow_v1` |
| Input contract | `commerce_intelligence_synthesis_v1` |
| Alembic | `f5a6b7c8d9e0` (+ runtime additive column ensure) |
| Probe | `GET /dev/commerce-intelligence-knowledge?store=demo` |

---

## Production probe

| Field | Result |
|-------|--------|
| `ok` | `true` |
| `deterministic` | `true` |
| `eligible_synthesis_count` | `5` |
| `ineligible_synthesis_count` | `9` |
| `knowledge_created` | `5` |
| `knowledge_updated` | `0` |
| `unchanged` | `0` |
| `abstained` | `5` |
| `rejected` | `4` |
| `deferred` | `0` (d7: discount/VIP arrive as `blocked` → rejected; no commercial Knowledge) |
| `failed` | `0` |
| `unaccounted` | `0` |
| `claim_boundary_ok` | `true` |
| `lineage_ok` | `true` |
| `duplicate_current` | `false` |
| `non_demo_writes` | `0` |

Verify script: `ok=true`.

### Knowledge created (Demo)

- `product_interest_conversion_gap` (3 products)
- `traffic_conversion_gap` (1 store)
- `recovery_influence_classification` (1 store)

### Claim / attribution boundaries

Known/unknown/prohibited preserved on samples; no causal wording. Recovery influence knowledge prohibits collapsed recovered-revenue claims.

### Deferred dependencies

D-CISYN-01 / D-CISYN-02 cannot become established Knowledge until synthesis qualifies. On Demo `d7` they are blocked at synthesis → intake reject.

---

## Tests

`pytest tests/test_commerce_intelligence_knowledge_v1.py` — **13 passed**

---

## Forbidden scope

No Guidance, Routing, Presentation, Surface Composition, Home UI, AI, or automatic actions.

---

## Final recommendation

**PRODUCTION CLOSED**

---

## STOP

Do not begin Commercial Guidance integration, Guidance Routing, Merchant Presentation, Surface Composition, Home rollout, or AI until this integration is reviewed and approved.
