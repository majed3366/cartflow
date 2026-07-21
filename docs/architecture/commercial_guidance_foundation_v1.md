# CartFlow Commercial Guidance Integration Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-22  
**Registry / versions:** `cguide_v1` / `cguide_v1_gen`  
**Feature flag:** `CARTFLOW_COMMERCIAL_GUIDANCE_V1`  
**Audience:** Product, engineering, architecture  

> **Law:** Commercial Guidance answers only *what CartFlow is allowed to advise the merchant* from governed Knowledge.  
> It does not decide placement, presentation, notifications, AI wording, or automatic actions.

---

## 0. Architectural position

```text
Canonical Domain Truth
        ↓
Evidence
        ↓
Commerce Intelligence Synthesis
        ↓
Knowledge
        ↓
Commercial Guidance   ← THIS LAYER (cguide_v1)
        ↓
Guidance Routing
        ↓
Merchant Presentation
```

**Input:** current Knowledge records only (`knowledge_statements`).  
**Output:** governed Commercial Guidance records in existing `commercial_guidance_records`.

---

## 1. Existing architecture inventory

| Component | Status | Reuse decision |
|-----------|--------|----------------|
| Knowledge Registry / `knowledge_statements` | Exists (ECF + ciknow) | **Read current ciknow Knowledge only** |
| Commercial Guidance Foundation (`cgf_v1`) | PRODUCTION CLOSED — Eligibility → Guidance | **Preserved**; not deleted |
| Guidance Eligibility (`gef_v1`) | Exists | **Not consumed** by cguide intake |
| Guidance Routing / Merchant Presentation | Exists | **Untouched** in this task |
| Merchant Recommendations / Decision Registry | Separate merchant-decision stack | **Not duplicated** |
| Confidence | Owned by Knowledge / ECF | **Reused** via `confidence_level` handoff |

### Implementation decision

Dedicated Knowledge intake adapter `cguide_v1` — mirrors `ciknow_v1`:

- Does **not** replace `generate_commercial_guidance_v1` (eligibility path).
- Does **not** create a second guidance table.
- Writes into `commercial_guidance_records` with `guidance_version=cguide_v1`, `guidance_scope=cguide_commercial_v1`.
- Additive lineage columns via Alembic `g6a7b8c9d0e1`.

---

## 2. Integration ownership

| Concern | Owner |
|---------|-------|
| Knowledge → Guidance mapping policies | `commercial_guidance_knowledge_registry_v1.py` |
| Intake / materialize / accounting | `commercial_guidance_knowledge_intake_v1.py` |
| Eligibility permission (ECF path) | Guidance Eligibility (unchanged) |
| Surface placement | Guidance Routing (future consumer; not changed here) |
| Merchant wording / layout | Presentation (forbidden in this task) |

---

## 3. Input contract

```text
knowledge_statements_current_v1
```

Allowed reads:

- Current `KnowledgeStatement` rows for the store
- Filter: `knowledge_version=ciknow_v1` and approved ciknow knowledge types

Forbidden reads:

- Widget / WhatsApp / movement / cart / product / purchase tables
- Provider payloads
- Storefront events
- Commerce Intelligence Synthesis APIs directly
- Guidance Eligibility evaluations
- Page / dashboard APIs

---

## 4. Intake policy registry (`cguide_v1`)

Each policy defines:

- `knowledge_type`
- eligible outcome when current (`eligible` / `observe_only` / `insufficient_evidence` / `conflicting`)
- `guidance_key`
- `merchant_objective`
- minimum confidence / freshness
- evidence requirements
- contradiction + abstention policies
- lifecycle / expiry
- `eligible_actions` / `forbidden_actions`
- routing eligibility (false in V1)
- active + version

No mapping logic in page code or ad-hoc services.

---

## 5. Eligibility rules

| Knowledge state | Guidance behavior |
|-----------------|-------------------|
| Current + mapped + not expired | Per policy (`eligible`, `observe_only`, gap, conflict) |
| Expired (`valid_until < as_of`) | `expired` — no commercial conclusion retained as current |
| Missing policy | `rejected` (`intake_policy_missing`) — isolated |
| Unsupported type | `rejected` |
| Claim boundary fail | `rejected` |

Truthful abstention is valid. Guidance never forces advice.

---

## 6. Knowledge mappings (initial)

| Knowledge type | Guidance key | Merchant objective |
|----------------|--------------|--------------------|
| `hesitation_recovery_pattern` | `investigate_shipping_checkout_friction` | Investigate checkout friction related to shipping |
| `product_interest_conversion_gap` | `review_product_interest_conversion_gap` | Review interest vs weak completion |
| `communication_return_without_purchase` | `review_whatsapp_return_journey` | Review journey after WhatsApp engagement |
| `traffic_conversion_gap` | `investigate_conversion_bottlenecks` | Investigate conversion bottlenecks |
| `repeated_interest_unresolved` | `review_unresolved_hesitation` | Review unresolved hesitation |
| `recovery_influence_classification` | `preserve_recovery_influence_boundary` | Review influence classes without collapse |
| `commercial_evidence_gap` | `collect_additional_evidence` | Collect more evidence before strategy change |
| `commercial_evidence_conflict` | `delay_until_evidence_clearer` | Delay decisions until evidence clarifies |

Forbidden examples (registry-enforced): reduce shipping cost; lower the price; increase advertising; claim WhatsApp ineffective; collapse attribution into recovered revenue.

---

## 7. Claim-boundary preservation

Invariant:

```text
Commercial Guidance claims ⊆ Knowledge claims
```

Guidance may normalize structure and assign lifecycle.  
Guidance must not delete unknowns, weaken prohibited claims, invent causes/solutions, or strengthen Knowledge.

---

## 8. Confidence handoff

Reuse Knowledge `confidence_level` (and related fields on the Knowledge record).  
No independent confidence framework.

---

## 9. Source identity & deterministic identity

Each guidance record preserves:

- `knowledge_id`, `knowledge_type`
- Knowledge fingerprint
- source lineage (synthesis ids/keys when present on Knowledge)
- known / unknown / prohibited
- merchant objective, eligible / forbidden actions
- confidence_level
- lifecycle + version

Deterministic `guidance_id` inputs: store, knowledge_id, knowledge_type, subject, guidance_key, scope, policy version.

Unchanged Knowledge → unchanged guidance identity (idempotent rerun).

---

## 10. Lifecycle

| Event | Behavior |
|-------|----------|
| New eligible Knowledge | Create current guidance |
| Unchanged Knowledge | Preserve identity / fingerprint (`unchanged`) |
| Material Knowledge change | Supersede old current; activate new |
| Knowledge expires | Expire / do not keep strong conclusion current |
| Downgrade to gap/conflict | Truthful transition; no silent retention of stronger advice |

---

## 11. Full accounting

```text
current Knowledge inputs
=
created + updated + unchanged
+ observe_only + evidence_gap + conflicting
+ abstained + rejected + expired + failed
```

`unaccounted` must be 0. Every reject/abstain exposes a reason code.

---

## 12. Failure isolation & performance

- One Knowledge intake failure does not block others.
- Missing policy for one type does not stop the run.
- Store isolation enforced; Demo probe writes Demo only.
- Reads current Knowledge only — no history scan / no raw commerce recompute.
- No merchant-facing request path for reconstruction (probe/materialize only).

---

## 13. Deferred dependencies

D-CISYN-01 / D-CISYN-02 remain blocked at Synthesis/Knowledge.  
cguide does not bypass them; absent Knowledge ⇒ no established guidance.

---

## 14. Feature flag & probe

- Flag: `CARTFLOW_COMMERCIAL_GUIDANCE_V1` (default on; `0` disables writes)
- Probe: `GET /dev/commercial-guidance?store=demo`

Approval requires: `unaccounted=0`, `failed=0`, `claim_boundary_ok=true`, `lineage_ok=true`, `duplicate_current=false`, `non_demo_writes=0`, `deterministic=true`.

---

## 15. Forbidden scope

Do **not** implement in this layer:

- Merchant Presentation / Home / Surface Composition
- Decision Workspace / Carts / Communication / Settings UI
- Guidance Routing changes
- AI wording, notifications, automatic actions
- Campaigns, discounts, WhatsApp/Widget behavior
- Direct CIS or raw provider reads

---

## 16. Relationship to cgf_v1

`cgf_v1` (Eligibility → Guidance) remains deployed and available to existing Routing consumers.  
`cguide_v1` is the Knowledge-integration path required for Commerce Intelligence Knowledge.  
Scopes/versions are isolated so the two paths do not silently supersede each other.
