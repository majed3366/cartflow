# Commerce Intelligence → Knowledge Integration V1 — Production Closure Evidence

**Status:** Pending production probe after merge  
**Date (UTC):** 2026-07-22  
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

## Deployment artifacts

| Item | Value |
|------|--------|
| Flag | `CARTFLOW_COMMERCE_INTELLIGENCE_KNOWLEDGE_INTEGRATION_V1` (default on) |
| Intake registry | `ciknow_v1` |
| Input contract | `commerce_intelligence_synthesis_v1` |
| Alembic | `f5a6b7c8d9e0` (+ runtime additive column ensure) |
| Probe | `GET /dev/commerce-intelligence-knowledge?store=demo` |
| Arch doc | `docs/architecture/commerce_intelligence_knowledge_integration_v1.md` |

---

## Tests

`pytest tests/test_commerce_intelligence_knowledge_v1.py` — **13 passed**

---

## Deferred dependencies

D-CISYN-01 / D-CISYN-02 remain non-qualifying for established Knowledge (`outcome=deferred`).

---

## Forbidden scope

No Guidance, Routing, Presentation, Surface Composition, Home UI, AI, or automatic actions.

---

## Production probe (fill on deploy)

| Field | Result |
|-------|--------|
| `ok` | _(pending)_ |
| `deterministic` | |
| `unaccounted` | |
| `failed` | |
| `claim_boundary_ok` | |
| `lineage_ok` | |
| `duplicate_current` | |
| eligible / ineligible | |
| created / abstained / rejected / deferred | |

---

## Final recommendation

_(Set after live probe)_
