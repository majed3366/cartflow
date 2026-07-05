# CartFlow Knowledge Production Standardization V1

**Status:** Ratified Phase 0 standard — required before Knowledge Routing Implementation V1  
**Date (UTC):** 2026-07-05  
**Scope:** Defines **who may produce knowledge**, **how knowledge is identified**, and **what metadata every knowledge item must carry** — not routing engine implementation  
**Authority:** Closes Phase 0 gaps identified in [`knowledge_routing_readiness_review_v1.md`](knowledge_routing_readiness_review_v1.md) (Verdict C). Subordinate to [`knowledge_routing_foundation_v1.md`](knowledge_routing_foundation_v1.md) (KR/KP).  
**Audience:** Product, engineering, architecture review  

**Explicitly out of scope:** Routing engine, Daily Brief migration, UI redesign, merchant behavior changes, AI.

---

## Executive summary

Knowledge Routing Foundation is ready. Current **producers are not standardized**.

This document ratifies the **Knowledge Production Standard** — the permanent contract governing how CartFlow publishes knowledge **before** routing assigns surface visibility and order.

**Core principle:** Only governed producers may publish knowledge. Surfaces consume knowledge. Surfaces do not produce knowledge.

**Knowledge Routing Implementation V1 must not begin until this standard is ratified** and producer metadata gaps are closed per §6.

---

## Section 1 — Knowledge producer definition

### 1.1 What qualifies as a Knowledge Producer

A **Knowledge Producer** is a **server-side governed module** that:

1. Reads upstream Truth, Evidence, Proof, Decision, or Explanation — never raw UI state  
2. Emits a **published knowledge item** conforming to §2  
3. Is registered in the **Producer Readiness Matrix** (§4)  
4. Does **not** perform surface selection, ordering, or layout  

Knowledge production **composes and labels** governed facts. It **does not** create Truth, change confidence, or decide surface layout.

### 1.2 Allowed producer types

| Producer type | Module (today / future) | Publishes |
|---------------|-------------------------|-----------|
| **Merchant Explanation** | `services/merchant_explanation_v1.py` | Cart-scoped lifecycle explanations |
| **Merchant Decision Layer** | `services/merchant_decision_layer_v1.py` | Governed merchant decisions |
| **Proof Surface** | `services/merchant_proof_surface_v1.py` | Proof bundles (upstream to explanation/decision; may publish proof-scoped items) |
| **Knowledge Layer** | `services/knowledge_insights_v1.py` + `services/knowledge_layer_v1.py` | Store-scoped pattern insights |
| **Future Attribution** | TBD | Recovery/commercial attribution claims |
| **Future Product Intelligence** | TBD | Product-scoped understanding |
| **Future Behavior Truth** | TBD | Behavioral pattern claims |

**Supporting registries (not producers):** `merchant_evidence_registry_v1`, `merchant_decision_registry_v1` — metadata only; they do not publish knowledge items.

**Truth modules (not producers):** `purchase_truth`, `recovery_truth_timeline_v1`, `customer_lifecycle_states_v1`, `knowledge_metrics_v1` — emit state/metrics only; no `knowledge_id`.

### 1.3 Explicitly excluded from producing knowledge

The following **must never publish** `knowledge_id` items:

| Excluded | Examples | Role |
|----------|----------|------|
| **JavaScript surfaces** | `merchant_dashboard_lazy.js`, `merchant_daily_brief.js`, `merchant_knowledge_layer.js` | Consume + layout only |
| **Templates** | `templates/merchant_app.html` | Shell only |
| **Dashboard widgets** | KPI cards, month summary blocks | Metrics display only |
| **Daily Brief UI** | `static/merchant_daily_brief.js` | Presentation only |
| **Notifications UI** | `#ma-gtb-notify` placeholder | Delivery shell only |
| **Daily Brief Composer V2** | `merchant_daily_brief_composer_v2.py` | **Interim aggregator** — must migrate to routed consumption; must not mint new knowledge types |
| **Legacy lifecycle modules** | `cartflow_merchant_lifecycle.py`, `merchant_recovery_lifecycle_truth.py` | Deprecated copy paths |

**Rule:** If code runs in the browser or performs layout/truncation, it **consumes** knowledge — it does not **produce** it.

---

## Section 2 — Knowledge publisher contract

Every **published knowledge item** emitted by a governed producer **must** declare the following fields before Knowledge Routing may consume it.

| Field | Type / notes | Producer supplies | Routing may assign |
|-------|----------------|-------------------|-------------------|
| `knowledge_id` | Stable platform ID (§3) | **Yes** — at publish time | No |
| `knowledge_type` | Canonical enum (foundation §4) | **Yes** | No |
| `source_domain` | `recovery` \| `understanding` \| `decision` \| `operational` \| `commercial` | **Yes** | No |
| `evidence_ids` | From Evidence Registry | **Yes** (copy from upstream) | No |
| `proof_sources` | e.g. `recovery_key`, `insight_key:` | **Yes** | No |
| `decision_ids` | Published decision IDs if applicable | **Yes** (empty if N/A) | No |
| `explanation_id` | From explanation catalog if applicable | **Yes** (empty if N/A) | No |
| `confidence` | `high` \| `medium` \| `low` \| `insufficient` | **Yes** (copy unchanged) | **No (KPUB-9)** |
| `routing_priority` | Integer — attention order | **Placeholder allowed** | **Routing assigns final value** |
| `eligible_surfaces` | Surface ID list | **Producer declares defaults** | Routing may refine |
| `merchant_visibility` | bool or scope | **Yes** | Routing may refine |
| `admin_visibility` | bool or scope | **Yes** | Routing may refine |
| `action_required` | bool | **Yes** | No |
| `attention_level` | `none` \| `informational` \| `attention` \| `urgent` | **Yes** | No |
| `aggregation_key` | Deterministic merge key | **Yes** when aggregatable | Routing may unify |
| `narrative_role` | `fact` \| `achievement` \| `attention` \| `trend` \| `closure` \| `diagnostic` | **Producer declares default** | Routing may refine |
| `expiration_rule` | `{ ttl_hours, resolve_on_purchase, … }` | **Yes** | Routing may refine lifetime |
| `traceability` | `{ knowledge_id, producer, producer_version, upstream_ids, published_at }` | **Yes** | Routing adds `routed_at` only |

### 2.1 Publication vs routing

| Stage | Responsibility |
|-------|----------------|
| **Knowledge Production** (this standard) | Mint `knowledge_id`, attach metadata, declare producer defaults |
| **Knowledge Routing** (future) | Assign final `routing_priority`, surface eligibility refinement, ordered feed per surface |

Producers may emit `routing_priority: null` or a **producer-default priority** until Routing V1 ships. Surfaces **must not** compute priority locally after Routing ships.

### 2.2 Minimum viable publication (Phase 0 target)

Before Routing V1, each governed producer must at minimum add:

- `knowledge_id`  
- `knowledge_type`  
- `traceability`  
- Existing fields already present (`explanation_id`, `eligible_surfaces`, `attention_level` on explanation)

Full contract compliance is required before Routing V1 **consumes** producer output.

---

## Section 3 — Knowledge ID convention

### 3.1 Rules (permanent)

| Rule | Requirement |
|------|-------------|
| **Stable** | Same upstream fact → same `knowledge_id` across requests |
| **Deterministic** | Derived from typed parts; no UUIDs, no random suffixes |
| **Traceable** | Encodes producer kind + primary subject key |
| **Aggregation-safe** | Store-scoped patterns include `store_slug` + bucket key |
| **Re-generation-safe** | Re-running producer on unchanged upstream → identical ID |

**Format:**

```
{producer_prefix}:{type_or_decision_key}:{scope}:{subject_key}
```

- `producer_prefix`: `expl` \| `dec` \| `proof` \| `kl` \| `attr` (future)  
- Segments lowercased; empty segments omitted; `/` and spaces replaced with `_`  
- `subject_key` must use stable upstream identifiers (`recovery_key`, `merge_key`, `insight_key`, `cart_id`)

### 3.2 Ratified examples

| Item | knowledge_id pattern | Example |
|------|---------------------|---------|
| Cart explanation — return without purchase | `expl:{explanation_id}:{store_slug}:{recovery_key}` | `expl:return_without_purchase:my-store:rk_abc123` |
| Cart explanation — purchase confirmed | `expl:purchase_confirmed:{store_slug}:{recovery_key}` | `expl:purchase_confirmed:my-store:rk_abc123` |
| Decision — obtain contact | `dec:{decision_id}:{store_slug}:{merge_key}` | `dec:decision_obtain_contact:my-store:contact:rk_abc123` |
| Decision — monitor return | `dec:{decision_id}:{store_slug}:{merge_key}` | `dec:decision_monitor_return:my-store:monitor:rk_abc123` |
| KL — hesitation top reason | `kl:{insight_key}:{store_slug}:{window_days}d` | `kl:hesitation_top_reason:my-store:7d` |
| KL — shipping hesitation (typed) | `kl:hesitation_shipping:{store_slug}:{date_bucket}` | `kl:hesitation_shipping:my-store:2026-07` |
| KL observation decision | `dec:decision_kl_observation:{store_slug}:{insight_key}` | `dec:decision_kl_observation:my-store:hesitation_top_reason` |
| Proof bundle (cart) | `proof:recovery:{store_slug}:{recovery_key}` | `proof:recovery:my-store:rk_abc123` |

### 3.3 Subject key precedence

| Producer | Primary subject key | Fallback |
|----------|---------------------|----------|
| Merchant Explanation | `recovery_key` | `{store_slug}:{abandoned_cart_id}` |
| Merchant Decision | `merge_key` | `{decision_id}:{proof_source}` |
| Knowledge Layer insight | `insight_key` + window | `insight_key` only |
| Proof Surface | `recovery_key` | `proof_source` |

### 3.4 Forbidden ID patterns

- UUID / random suffix (`kr_a8f3…`)  
- Surface name in ID (`daily_brief:…`)  
- Timestamp-only subject (`…:2026-07-05T19:00:00`)  
- JS-generated IDs  

---

## Section 4 — Producer readiness matrix

| Producer / surface | Produces knowledge today? | Classification | Required action |
|--------------------|---------------------------|----------------|-----------------|
| **Merchant Explanation V1** | Partial — `merchant_explanation_v1` bundle | **Needs metadata** | Add `knowledge_id`, full `traceability`; map `knowledge_event_type` → `knowledge_type` |
| **Merchant Decision Layer V1** | Partial — `merchant_decisions_v1[]` | **Needs metadata** | Add `knowledge_id`, `explanation_id`, `attention_level`, `knowledge_type`, `traceability` per decision |
| **Proof Surface V1** | Partial — proof bundle on row | **Needs metadata** | Add `knowledge_id`; link to explanation/decision; remain upstream to routing |
| **Knowledge Layer API** (`knowledge_insights_v1`) | Yes — insights + KL observation decisions | **Needs metadata** | Add `knowledge_id` per insight; link insight → decision ID; stop JS from re-producing OIA text as knowledge |
| **Knowledge Layer JS** | **Yes (violation)** — OIA builders, `pickTopInsights` | **Should not produce knowledge** | Migrate to consume routed items; retire selection maps |
| **Daily Brief Composer V2** | **Yes (violation)** — headlines, aggregation | **Must migrate to routed consumption** | Phase 1 Routing consumer; becomes projection-only |
| **Daily Brief V1 service** | Eligibility filter only | **Must migrate to routed consumption** | Retire local selection after Routing V1 |
| **Cart Detail JS** | **Yes (violation)** — executability gate, heuristics | **Should not produce knowledge** | Consume `merchant_explanation_v1` + routed slices only |
| **Home dashboard** | Partial — `merchant_reason_insight_ar` in summary | **Needs metadata** | Move insight generation to KL producer; home consumes routed feed |
| **Monthly Summary** | No — metrics only | **Ready now** (metrics) | Future: consume routed `narrative_role: trend` items only |
| **Notifications** | No — placeholder UI | **Ready now** (empty) | Future: consume notification-eligible routed items only |
| **Customer Lifecycle States V1** | Parallel Arabic copy | **Should not produce knowledge** | State key only; narrative via Explanation producer |
| **Legacy lifecycle modules** | Parallel copy | **Should not produce knowledge** | Disable on normal-carts path |
| **Dashboard Attention Semantics** | Intervention presentation fields | **Needs metadata** | Presentation gate only; link to decision `knowledge_id` |

### 4.1 Readiness summary

| Status | Count | Producers |
|--------|-------|-----------|
| **Ready now** | 2 | Monthly metrics path, Notifications shell |
| **Needs metadata** | 4 | Explanation, Decision, Proof, KL API |
| **Should not produce knowledge** | 4 | KL JS, Cart Detail JS, Lifecycle SoT copy, Legacy modules |
| **Must migrate to routed consumption** | 3 | Composer V2, Brief V1 eligibility, Home reason insight |

---

## Section 5 — Surface-owned selection freeze

### 5.1 Permanent freeze rule (effective immediately)

**No new code** in surfaces (JS, templates, widgets) may add **knowledge selection logic** including:

```
if purchase …
if return …
if hesitation …
if delivered …
if reply …
if replied …
if bottleneck …
```

**All new selection logic** must live in:

1. A **governed producer** (§1.2), or  
2. **Knowledge Routing** (future), or  
3. **Truth / Decision / Explanation** upstream layers  

Surfaces may only:

- Truncate to attention budget (after Routing pre-sorts)  
- Apply CSS/layout  
- Map `decision_class` → visual severity (presentation mapping, not selection)

### 5.2 Documented existing violations (migration backlog)

| Location | Violation | Migration owner |
|----------|-----------|-----------------|
| `merchant_daily_brief_composer_v2.py` | Achievement split, aggregation, headlines, sort | Routing V1 → Composer projection |
| `merchant_daily_brief_v1.py` | Eligibility + priority select | Routing V1 |
| `merchant_knowledge_layer.js` | `INSIGHT_PRIORITY`, `pickTopInsights`, OIA builders | Routing V2 + KL producer metadata |
| `merchant_dashboard_lazy.js` | Executability gate, completed heuristics, followup reply | Routing V2 |
| `main.py` summary | `merchant_reason_insight_ar` | KL producer + Routing |

**Dead code (remove during migration, do not extend):**

- `merchant_dashboard_lazy.js` `merchantLifecycleCompact` — never called  

### 5.3 Enforcement

- PRs touching merchant JS must not add selection branches on lifecycle/decision/purchase/return/hesitation keys  
- Grep gate (recommended): `if.*purchase|if.*return|if.*hesitation|pickTopInsights|INSIGHT_PRIORITY` in `static/` — new matches require architecture review  

---

## Section 6 — Metadata gap closure

### 6.1 Field supply matrix

| Field | Merchant Explanation | Merchant Decision | Proof Surface | KL API | Routing (future) |
|-------|---------------------|-------------------|---------------|--------|------------------|
| `knowledge_id` | **Add** | **Add** | **Add** | **Add** | — |
| `knowledge_type` | Map from `knowledge_event_type` | **Add** from registry | `proof_recovery` | Map from `insight_key` | — |
| `explanation_id` | **Have** | **Add** link | — | — | — |
| `decision_ids` | — | Self (`decision_id`) | — | KL obs decision | — |
| `routing_priority` | Placeholder null | Placeholder null | — | Placeholder null | **Assign final** |
| `eligible_surfaces` | **Have** (partial) | **Add** | **Add** | **Add** | Refine |
| `attention_level` | **Have** | **Add** | — | **Add** from severity | — |
| `narrative_role` | Default `fact` / `closure` | **Add** from class+action | — | **Add** (`trend` / `attention`) | Refine |
| `aggregation_key` | `recovery_key` | **Have** (`merge_key`) | — | `insight_key` + window | Unify |
| `traceability` | **Add** | **Add** | **Add** | **Add** | Add `routed_at` |

### 6.2 Producer-specific closure tasks

**Merchant Explanation V1**

- [ ] Mint `knowledge_id` per §3.2  
- [ ] Emit `knowledge_type` aligned to foundation enum  
- [ ] Add `traceability.producer = "merchant_explanation_v1"`  
- [ ] Declare default `narrative_role` per catalog entry  
- [ ] Stop treating lifecycle SoT Arabic as parallel publication — explanation is canonical narrative  

**Merchant Decision Layer V1**

- [ ] Mint `knowledge_id` per decision  
- [ ] Link `explanation_id` where cart-scoped (e.g. `return_without_purchase`)  
- [ ] Copy or derive `attention_level` from linked explanation or decision class  
- [ ] Declare `eligible_surfaces` defaults per decision registry entry  
- [ ] Declare `narrative_role` (`achievement` for observation/monitor; `attention` for intervention)  

**Proof Surface V1**

- [ ] Mint `knowledge_id` for proof bundle  
- [ ] Remain upstream — proof items feed explanation/decision, not merchant JS directly  

**Knowledge Layer API**

- [ ] Mint `knowledge_id` per insight  
- [ ] Link KL observation decisions to insight `knowledge_id` in `traceability`  
- [ ] Declare `eligible_surfaces: [knowledge_layer, daily_brief]` defaults per insight type  

### 6.3 Phase 0 completion gate

Knowledge Routing Implementation V1 may begin when:

- [x] This standard ratified  
- [ ] `knowledge_id` minting implemented in Explanation + Decision + KL API (code task — separate from this doc)  
- [ ] `traceability` block present on all three producers  
- [ ] Surface selection freeze communicated (§5)  
- [ ] `knowledge_routing_implementation_v1.md` design doc drafted  

---

## Section 7 — Migration sequence

Required order **before and during** Knowledge Routing Implementation V1:

| Step | Action | Owner | Routing dependency |
|------|--------|-------|-------------------|
| **1** | Standardize **Merchant Explanation** output (§6.2) | Explanation service | Producer feed |
| **2** | Standardize **Merchant Decision** output (§6.2) | Decision layer | Producer feed |
| **3** | Standardize **KL claim** output — insight `knowledge_id` + traceability | KL insights + claim evidence | Producer feed |
| **4** | Introduce **Knowledge Routing Implementation V1** | New routing service | Reads standardized producers |
| **5** | Convert **Composer V2** to consume routed brief slice | Brief composer | Routing consumer |
| **6** | Remove **surface-owned selection** from JS (KL, cart detail) | Frontend | Routing consumer |
| **7** | Home + notifications + monthly consume routed feeds | Surfaces | Routing consumer |

**Do not reorder:** Steps 1–3 must complete before Step 4. Step 4 must complete before Steps 5–7.

---

## Section 8 — Governance contracts (KPUB)

| ID | Contract |
|----|----------|
| **KPUB-1** | **Only governed producers publish knowledge** — modules in §1.2 only; registries and Truth modules excluded |
| **KPUB-2** | **Every knowledge item has deterministic `knowledge_id`** — per §3; no random IDs |
| **KPUB-3** | **No surface creates knowledge** — JS, templates, widgets, Composer headlines excluded |
| **KPUB-4** | **No surface selects knowledge** — selection freeze §5; truncation-only after Routing |
| **KPUB-5** | **Every knowledge item is traceable** — `traceability` block mandatory |
| **KPUB-6** | **Every knowledge item declares `eligible_surfaces`** — producer defaults required |
| **KPUB-7** | **`routing_priority` is platform-owned** — producers emit placeholder; Routing assigns final order (KP-1…KP-3) |
| **KPUB-8** | **Diagnostics are not merchant-facing by default** — `diagnostic_internal`, proof diagnostic fields admin-only |
| **KPUB-9** | **Knowledge production never changes truth** — confidence and facts copied unchanged from upstream |
| **KPUB-10** | **Knowledge production is deterministic** — same upstream → same `knowledge_id` and metadata; no AI, no LLM, no surface-varying heuristics |

---

## Section 9 — Relationship to adjacent standards

| Document | Relationship |
|----------|--------------|
| [`knowledge_routing_foundation_v1.md`](knowledge_routing_foundation_v1.md) | Routing consumes published items from this standard |
| [`knowledge_routing_readiness_review_v1.md`](knowledge_routing_readiness_review_v1.md) | Verdict C gaps closed by §6–§7 |
| [`merchant_explanation_unification_v1.md`](merchant_explanation_unification_v1.md) | Explanation producer spec — extend with `knowledge_id` |
| [`merchant_decision_implementation_v1.md`](merchant_decision_implementation_v1.md) | Decision producer spec — extend with publisher contract |
| [`merchant_daily_brief_composer_v2.md`](merchant_daily_brief_composer_v2.md) | Interim aggregator — migration target Step 5 |

---

## Section 10 — Anti-patterns (forbidden)

1. Minting `knowledge_id` in JavaScript  
2. Daily Brief Composer inventing new `knowledge_type` values  
3. KL JS rebuilding merchant narrative from raw `evidence{}` maps  
4. Lifecycle SoT emitting merchant narrative without Explanation sync  
5. Random UUID as `knowledge_id`  
6. Surface-specific `routing_priority` in Python attach hooks  
7. Producer changing `confidence` based on surface context  

---

## Success criteria

- [x] Knowledge producer definition ratified (§1)  
- [x] Publisher contract specified (§2)  
- [x] `knowledge_id` convention ratified (§3)  
- [x] Producer readiness matrix complete (§4)  
- [x] Surface selection freeze defined (§5)  
- [x] Metadata gap closure mapped (§6)  
- [x] Migration sequence ordered (§7)  
- [x] KPUB-1…KPUB-10 governance contracts ratified (§8)  

**Next artifact:** Producer metadata implementation (Explanation + Decision + KL) + `knowledge_routing_implementation_v1.md` — then Knowledge Routing Implementation V1.
