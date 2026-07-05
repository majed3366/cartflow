# CartFlow Knowledge Routing Implementation V1

**Status:** Implemented — first production routing layer  
**Date (UTC):** 2026-07-05  
**Scope:** Platform-owned routing of standardized knowledge to surfaces — Phase 1: Daily Brief  
**Authority:** Implements [`knowledge_routing_foundation_v1.md`](knowledge_routing_foundation_v1.md) and consumes [`knowledge_producer_metadata_implementation_v1.md`](knowledge_producer_metadata_implementation_v1.md)  
**Audience:** Engineering  

---

## Executive summary

Knowledge Routing V1 is the **single platform-owned routing layer**. It consumes standardized published knowledge only, assigns **`routing_priority`**, aggregates by producer **`aggregation_key`**, and distributes routed items to eligible surfaces.

**Phase 1 consumer:** Daily Brief Composer V2 — now **projection-only** (no select/rank/filter).

Routing is **domain-neutral** — no purchase/return/hesitation business rules.

---

## Architecture

```
Knowledge Producers (standardized metadata)
        ↓
Knowledge Routing v1  ← services/knowledge_routing_v1.py
        ↓
Surface Composition
        ↓
Daily Brief (Phase 1)
```

---

## Module: `services/knowledge_routing_v1.py`

### Responsibilities (only)

| Responsibility | Function |
|----------------|----------|
| Eligibility | `is_surface_eligible_v1`, `is_merchant_visible_v1` |
| Routing priority | `compute_routing_priority_v1` (attention_level + confidence + narrative_role metadata) |
| Surface visibility | Filter by `eligible_surfaces` |
| Lifetime | Reads `expiration_rule` (pass-through; no mutation) |
| Distribution | `route_knowledge_for_surface_v1` |
| Publication | Routed item contract output |

### Routing priority (deterministic, metadata-only)

```
routing_priority = ATTENTION_RANK[attention_level]
                 + CONFIDENCE_RANK[confidence]
                 + NARRATIVE_RANK[narrative_role]
```

No decision class, no cart value, no timestamps, no domain branching.

### Section assignment (Daily Brief)

Uses **`narrative_role`** + **`attention_level`** + **`action_required`** metadata only:

- `achievement`, `closure`, `trend` → achievement section (unless urgent attention)
- `attention`, `diagnostic`, urgent/attention levels, `action_required` → attention section

### Routed item contract

Each routed item includes:

`knowledge_id`, `routing_priority`, `eligible_surfaces`, `merchant_visibility`, `admin_visibility`, `attention_level`, `aggregation_key`, `narrative_role`, `expiration_rule`, `traceability`, `producer_reference`, `knowledge_payload`, `routing_version`, `section`, `member_count`, `member_payloads`

---

## Phase 1: Daily Brief integration

### Composer V2 (`merchant_daily_brief_composer_v2.py`)

**Before:** Selected, ranked, filtered, aggregated decisions locally.  
**After:** Calls `route_daily_brief_knowledge_v1` → `project_routed_topic_v2` (layout/copy projection only).

Removed from compose path:

- `is_achievement_decision` business branching
- `group_decisions_into_topics` priority sorts
- Domain-specific headline templates (`DECISION_ID_MONITOR_RETURN`, etc.)

Headlines projected from `knowledge_payload.decision_explanation.rationale_ar` + member count.

### API path (`build_merchant_daily_brief_api_payload`)

1. Collect decision bundles (KL + cart rows)  
2. Enrich KL with producer metadata  
3. Route via Composer → Routing  
4. Brief payload includes `knowledge_routing_v1` observability block  

---

## Producer adjustment (aggregation key)

Decision producer metadata now sets **`aggregation_key`** via cross-cart metadata fields (`decision_id` family + `action_key` + `commercial_goal` + `evidence_id`) in `knowledge_producer_metadata_v1._decision_aggregation_key_v1` — enables routing aggregation without domain logic in routing.

---

## Routing neutrality verification

`knowledge_routing_v1.py` contains **no** business-domain conditionals (`purchase`, `return`, `hesitation`, etc.). Enforced by unit test.

---

## Tests

| File | Coverage |
|------|----------|
| `tests/test_knowledge_routing_v1.py` | Priority determinism, eligibility, aggregation, neutrality, traceability |
| `tests/test_merchant_daily_brief_composer_v2.py` | Composer consumes routed feed |
| `tests/test_knowledge_producer_metadata_v1.py` | Producer contract (unchanged behavior) |

```bash
python -m pytest tests/test_knowledge_routing_v1.py tests/test_merchant_daily_brief_composer_v2.py -q
```

---

## Explicitly out of scope (future phases)

| Phase | Surface |
|-------|---------|
| 2 | Knowledge Layer JS |
| 2 | Dashboard Home |
| 2 | Cart Detail |
| 3 | Notifications |
| 3 | Monthly Summary |

---

## Related documents

| Document | Role |
|----------|------|
| [`knowledge_routing_foundation_v1.md`](knowledge_routing_foundation_v1.md) | KR/KP principles |
| [`knowledge_production_standardization_v1.md`](knowledge_production_standardization_v1.md) | Producer contract |
| [`merchant_daily_brief_composer_v2.md`](merchant_daily_brief_composer_v2.md) | Composer (update: projection-only) |

---

## Success criteria

- [x] Knowledge Routing V1 module implemented  
- [x] `routing_priority` assigned centrally  
- [x] Daily Brief Composer projection-only  
- [x] Domain-neutral routing (metadata-only)  
- [x] Full routed item traceability  
- [x] Tests pass  
- [x] No Truth/Decision/Explanation changes  
