# CartFlow Product Performance Domain Model V1

**Status:** Permanent business-domain charter (documentation only)  
**Date (UTC):** 2026-07-20  
**Authority:** Subordinate to [`docs/engineering_constitution_v1.md`](../engineering_constitution_v1.md), [`MERCHANT_TRUST_CONSTITUTION_V1.md`](../../MERCHANT_TRUST_CONSTITUTION_V1.md), [`IDENTITY_FOUNDATION_ARCHITECTURE_V1.md`](../../IDENTITY_FOUNDATION_ARCHITECTURE_V1.md), [`IDENTITY_FOUNDATION_CONTRACT_V1.md`](../../IDENTITY_FOUNDATION_CONTRACT_V1.md), [`commerce_brain_v1_1.md`](commerce_brain_v1_1.md), [`commerce_object_model_v1.md`](commerce_object_model_v1.md), [`commerce_evidence_contract_v1.md`](commerce_evidence_contract_v1.md), [`commerce_object_contracts_v1.md`](commerce_object_contracts_v1.md), [`commerce_temporal_change_contract_v1.md`](commerce_temporal_change_contract_v1.md), Product Identity Foundation ([`PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md`](../../PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md)), Product Data Foundation ([`cartflow_product_data_foundation_architecture_v1.md`](../cartflow_product_data_foundation_architecture_v1.md)), and Time Authority ([`TIME_AUTHORITY_ARCHITECTURE_V2.md`](TIME_AUTHORITY_ARCHITECTURE_V2.md)). Aligns with Proof of Value and Commercial Question Registry — does not replace them.  
**Audience:** Product, engineering, architecture, future maintainers  
**Explicitly out of scope:** Pages, UI, dashboards, Home widgets, reports, charts, APIs, schemas, migrations, code, prompts, scoring algorithms, Decision Engine, recommendations, merchant guidance copy, rankings, AI analysis, presentation fields, page-specific structures

> **Law:** Product Performance is the **Single Source of Truth** for governed product-performance understanding.  
> Surfaces may project it. Surfaces do not invent it.  
> Identity Foundation answers *which product*. Product Performance answers *how that product is performing* — without becoming a second Product identity.  
> No presentation logic. No recommendation logic. No decision logic in this charter.

---

## 0. Purpose

This document defines the **canonical Product Performance Domain** for CartFlow.

It is **not** a dashboard, **not** analytics productization, and **not** a recommendation engine.  
It is the business domain that every future layer (Decision Engine, Executive Knowledge, Home, Reports, Insights) must consume for product-performance understanding.

It answers, for the domain and each entity:

| Question | Meaning |
|----------|---------|
| **What is it?** | Business definition |
| **Why does it exist?** | The merchant or platform question it enables |
| **Who owns it?** | Domain authority for truth of the entity |
| **How does it evolve?** | What may change it, and what may not |
| **What can reference it?** | Which other entities/objects may point to it |
| **Boundaries** | What it must never become |

Plus the structural contract: **Identity · Lifecycle · Properties · Confidence · Freshness · Relationships · Never store**.

**Not in this document:** how entities are shown, scored, ranked, recommended, fetched, or stored in tables.

---

## 1. Primary business questions (domain charter)

The Product Performance Domain exists so CartFlow can eventually answer — with evidence and honesty about gaps:

| ID | Business question | Primary enabling entities |
|----|-------------------|---------------------------|
| **PP-Q1** | Which products attract strong customer interest? | Product Interest, Product Activity, Product Evidence, Product Confidence |
| **PP-Q2** | Which products convert well? | Product Purchase, Product Interest, Product Performance Snapshot |
| **PP-Q3** | Which products have declining performance? | Product Performance Snapshot (temporal comparison), Product Evidence |
| **PP-Q4** | Which products are improving? | Product Performance Snapshot (temporal comparison), Product Evidence |
| **PP-Q5** | Which products lack sufficient evidence? | Product Evidence, Product Confidence |
| **PP-Q6** | Which products deserve merchant attention? | *(out of scope for this charter — Decision/Guidance consumes snapshots + confidence; domain only supplies governed inputs)* |
| **PP-Q7** | Which products generate interest but fail to convert? | Product Interest, Product Purchase, Product Performance Snapshot, Product Evidence |

**Registry alignment (do not duplicate):** Commercial questions **CQ-P01…CQ-P03** remain the platform question inventory for product interest/conversion families. Product Performance is the **domain SoT** those questions (and future CQ-P*) must draw from — not a parallel question registry, and not a Home section model.

**Executive Knowledge alignment:** Executive questions (e.g. EQ-04 opportunity, EQ-05 understanding) may *consume* Product Performance projections via Findings/Knowledge. They never own Product Performance truth.

---

## 2. Architectural position

### 2.1 Single Source of Truth

| Fact class | Source of truth | Not SoT |
|------------|-----------------|---------|
| Product identity (which product) | Product Identity Foundation + Object Model **Product** | Product Performance entities |
| Product performance understanding (how it performs) | **This domain** (entities below) | Home, Dashboard, Widgets, Reports, merchant pages, recommendation surfaces, Findings prose, fixtures |
| Evidence anatomy / strength vocabulary | Commerce Evidence Contract | Ad-hoc UI confidence chips |
| Store scope | MQIC / Identity Authority (`store_slug` / `canonical_store_id`) | Surface-local store switches |
| Time windows / “now” | Time Authority | Wall-clock improvisation in consumers |

### 2.2 Independence rules

| Rule | Meaning |
|------|---------|
| **PP-I1** | Domain entities contain **no** presentation fields (labels, card layouts, colors, sort orders for UI, CTA copy). |
| **PP-I2** | Domain entities contain **no** page-specific structures (Home bands, dashboard tabs, report sections). |
| **PP-I3** | Domain entities contain **no** recommendation or guidance payloads. |
| **PP-I4** | Domain entities contain **no** decision scores, ranks, or “attention priority” as truth. |
| **PP-I5** | Consumers project; they do not author Product Performance truth. |

### 2.3 Layer stack (reuse, do not redefine)

```text
Reality (PDF / Lifecycle / Purchase Truth / cart_line_snapshots / mappings)
  → Observation (Commerce Object Model)
  → Product Signal Collection                               ← atomic product facts (see product_signal_collection_v1.md)
  → Product Activity / Product Interest / Product Purchase   ← domain facts
  → Product Evidence                                        ← Evidence Contract kinds about products
  → Product Performance Snapshot                            ← governed as-of rollup
  → Product Confidence                                      ← sufficiency & confidence ceiling
  → Pattern / Knowledge / Decision / Guidance               ← Commerce Brain (future consumers)
  → Executive Knowledge / Home / Reports                    ← surfaces (project only)
```

**Complexity rule (Brain Rule 6):** These entities exist because Commerce Object Model **Product** is identity-only and **forbids** ranking/performance scores on Product. Product Performance is the governed place for performance understanding **about** Product — not a second Product type.

---

## 3. Shared property rules

Apply everywhere marked applicable. Do not invent parallel systems.

| Property | Meaning | Rule |
|----------|---------|------|
| **Confidence** | Strength of support for a claim-like assertion | Compatible with Proof of Value / Evidence Contract (e.g. strong/medium/weak/insufficient/unknown or High/Medium/Low/**Unknown**). AI cannot raise it. |
| **Freshness** | How current the support is | Window end, `as_of`, or last_verified — stale certainty is not current truth. Time Authority governs “now.” |
| **Unknown** | Valid value | Absence of proof beats false certainty. Insufficient evidence is a first-class outcome. |
| **Store isolation** | One store per instance | No cross-store pooling of proof or rollups. |
| **Identity reference** | Subjects by Foundation key | References use `stable_identity_key` (tiers A–E) + store scope — never display names as identity. |
| **Reference rule** | Cite, do not embed | Entities reference identities and evidence ids; they do not embed full Product/Cart copies as truth. |
| **No causation-as-fact** | Correlation ≠ cause | Co-occurrence and conversion rates may be stated; “caused” is forbidden until a future contract allows it. |

---

## 4. Domain entity map

| Entity | Primary responsibility | One-line role |
|--------|------------------------|---------------|
| **Product Identity** | Subject grain | *Which* sellable product (Foundation-owned; cited, not redefined) |
| **Product Activity** | Behavioral volume | What commerce activity touched this product |
| **Product Interest** | Attention / intent signal class | How strongly customers engage without asserting conversion quality |
| **Product Purchase** | Conversion / purchase linkage | What purchase truth attaches to this product |
| **Product Performance Snapshot** | As-of governed rollup | Coherent performance picture for a product in a window |
| **Product Evidence** | Proof bundles | Structured proof for product-performance claims |
| **Product Confidence** | Sufficiency & ceilings | How much CartFlow may responsibly claim from the above |

---

## 5. Entity definitions

Entities are ordered: identity subject → activity facts → meaning facets → rollup → proof → confidence.

---

### 5.1 Product Identity *(Foundation citation — not owned here)*

**What is it?**  
The canonical sellable product subject for a Store, as defined by Product Identity Foundation and Commerce Object Model **Product**.

**Why does it exist in this domain?**  
Every Product Performance fact must attach to a governed identity. Without Foundation readiness/authenticity, performance understanding is forbidden (Identity Foundation gate).

**Who owns it?**  
**Product Identity Foundation / Product Data Foundation** — not Product Performance.

**How does it evolve?**  
Per Foundation and Object Model Product rules. Product Performance **never** creates, merges, or renames identity.

**What can reference it?**  
All Product Performance entities (by identity key only).

#### Contract

| Dimension | Definition |
|-----------|------------|
| **Identity** | `stable_identity_key` tiers A–E; tenant = `store_slug` under MQIC. Immutable snapshot identifiers on `cart_line_snapshots` where applicable. |
| **Lifecycle** | Owned by Foundation (Active → Stale → Retired / Merged). Stale ≠ “unpopular.” |
| **Properties** | Only those defined by Foundation / Object Model Product. |
| **Confidence** | Identity-match confidence (Foundation) — distinct from Product Confidence (performance claims). |
| **Freshness** | Catalog/snapshot freshness per Foundation — distinct from performance-window freshness. |
| **Relationships** | Product Identity ← referenced by all PP entities; Product Identity → Store. |
| **Never store (in PP domain)** | A second product key, display-name-as-id, placeholders («منتج X»), ranking scores, recommended lists, UI cards. |

**Boundary:** Product Performance **cites** Product Identity. It does not redefine Product.

---

### 5.2 Product Activity

**What is it?**  
Governed, store-scoped facts about commerce activity involving a Product Identity within a declared time window — counts and linkages of observed commercial touches (e.g. cart-line presence, add/update events, session touches) without interpreting conversion quality.

**Why does it exist?**  
To answer: *what happened involving this product?* — the volume and shape of activity that later Interest/Purchase/Snapshot layers may interpret.

**Who owns it?**  
Product Performance Domain (activity facet). **Upstream reality owners remain:** Lifecycle/cart truth, Observation plane, PDF cart-line snapshots. Product Activity assembles governed activity facts from those sources; it does not replace them.

**How does it evolve?**  
Rebuilt or versioned when windowed reality/observations change under deterministic assembly rules (future implementation). Append/version discipline preferred over silent rewrite. Does not evolve from Knowledge prose or UI filters.

**What can reference it?**  
Product Interest, Product Performance Snapshot, Product Evidence (as source items), Pattern/Knowledge (via Evidence).

#### Contract

| Dimension | Definition |
|-----------|------------|
| **Identity** | Stable `product_activity_id` (or deterministic key: store + product identity + window + activity_kind set). |
| **Lifecycle** | Draft → Active → Superseded / Invalidated. Sealed historical windows are immutable except via supersession. |
| **Properties** | Store scope; Product Identity ref; window; activity measures (e.g. cart_line_occurrences, distinct_carts, distinct_sessions — exact measure catalog is a future contract); source refs; gaps. |
| **Confidence** | Sensing/completeness confidence for activity capture (not merchant “this product is hot”). |
| **Freshness** | Window end / assembled_at; incomplete ingest → Unknown/insufficient, not fabricated zeros presented as truth. |
| **Relationships** | Activity → Product Identity → Store; consumed by Interest, Snapshot, Evidence. |
| **Never store** | Rankings, “trending” badges, recommendation lists, UI sort keys, causal stories, cross-store aggregates. |

**Boundary:** Activity is **volume/touch truth**, not interest quality and not purchase success.

---

### 5.3 Product Interest

**What is it?**  
Governed characterization of customer interest/attention in a Product Identity for a window — derived from Product Activity and eligible observations (including hesitation linkage when present) **without** asserting purchase outcome.

**Why does it exist?**  
To answer: *which products attract interest?* and to enable PP-Q1 / PP-Q7 / CQ-P* interest facets — separately from conversion.

**Who owns it?**  
Product Performance Domain (interest facet).

**How does it evolve?**  
When Activity (and related observations/mappings) change under deterministic rules. Interest must not silently invent engagement when Activity evidence is insufficient.

**What can reference it?**  
Product Performance Snapshot, Product Evidence, Pattern/Knowledge (via Evidence). Decision/Guidance may cite Interest only through Snapshot/Evidence/Confidence — not by inventing interest.

#### Contract

| Dimension | Definition |
|-----------|------------|
| **Identity** | Stable `product_interest_id` (or deterministic key: store + product identity + window + interest_model_version). |
| **Lifecycle** | Draft → Active → Superseded / Invalidated. |
| **Properties** | Store scope; Product Identity ref; window; interest facets (e.g. repeated cart presence, hesitation-linked interest — catalog deferred); Activity refs; gaps; Unknown allowed. |
| **Confidence** | Claim support for interest assertions; capped by Product Evidence / Product Confidence. |
| **Freshness** | Window / assembled_at; stale interest is not current interest. |
| **Relationships** | Interest → Product Identity; Interest → Product Activity (basis); Interest ↔ Product Purchase (comparable, not embedded); Snapshot/Evidence cite Interest. |
| **Never store** | “Customers love this,” AI sentiment, marketing copy, recommendation rank, conversion rate as interest, Home card fields. |

**Boundary:** Interest ≠ Purchase. High interest with low purchase is a **comparison across entities**, not a field stuffed into Interest alone.

---

### 5.4 Product Purchase

**What is it?**  
Governed, store-scoped purchase-linked facts for a Product Identity within a window — what CartFlow can responsibly assert about purchase outcomes tied to that product via Purchase Truth and PDF purchase mappings.

**Why does it exist?**  
To answer: *which products convert / are purchased?* (PP-Q2, PP-Q7) without conflating cart interest with purchase.

**Who owns it?**  
Product Performance Domain (purchase facet). **Upstream reality owners remain:** Purchase Truth, `product_purchase_mappings` / PDF purchase mapping modules. Product Purchase does not redefine order/cart purchase authority.

**How does it evolve?**  
When purchase truth and product–purchase mappings change under deterministic assembly. Cannot invent line-level purchase when mappings are absent — must record gaps / Unknown.

**What can reference it?**  
Product Performance Snapshot, Product Evidence, Pattern/Knowledge (via Evidence).

#### Contract

| Dimension | Definition |
|-----------|------------|
| **Identity** | Stable `product_purchase_id` (or deterministic key: store + product identity + window + purchase_model_version). |
| **Lifecycle** | Draft → Active → Superseded / Invalidated. |
| **Properties** | Store scope; Product Identity ref; window; purchase measures (e.g. purchased_cart_links, purchase_events — catalog deferred); Purchase Truth / mapping refs; gaps. |
| **Confidence** | Linkage confidence (product ↔ purchase) and completeness; Unknown when grain is cart-only. |
| **Freshness** | Window / last purchase-truth alignment time. |
| **Relationships** | Purchase → Product Identity → Store; comparable to Interest; Snapshot/Evidence cite Purchase. |
| **Never store** | Attributed ROI narratives, recovery credit fiction, recommendation “buy this,” UI revenue cards as domain truth, causation claims. |

**Boundary:** Purchase facet is **purchase linkage truth about a product**, not store-wide GMV reporting and not recovery attribution engine.

---

### 5.5 Product Performance Snapshot

**What is it?**  
The governed, point-in-time (or windowed) **coherent rollup** of Product Activity, Product Interest, and Product Purchase for one Product Identity in one Store — the primary SoT unit consumers should read for “how is this product performing *as of* this window?”

**Why does it exist?**  
To prevent every consumer from joining Activity/Interest/Purchase differently. Snapshot is the **canonical performance picture**; facets remain separately owned for audit and re-assembly.

**Who owns it?**  
Product Performance Domain (rollup authority).

**How does it evolve?**  
Materialized/versioned when facet inputs change; historical snapshots sealed. Temporal comparison (improving/declining) is performed by **comparing snapshots** (or sealed snapshot deltas under a future temporal contract) — not by mutable “trend” fields rewritten in place without provenance.

**What can reference it?**  
Product Evidence (claims about snapshot contents), Product Confidence, Pattern/Knowledge/Decision/Guidance (future), Executive Knowledge projection, Reports (as consumers).

#### Contract

| Dimension | Definition |
|-----------|------------|
| **Identity** | Stable `product_performance_snapshot_id` (or deterministic key: store + product identity + window + snapshot_version). |
| **Lifecycle** | Draft → Active → Sealed → Superseded. Sealed snapshots are immutable. |
| **Properties** | Store scope; Product Identity ref; window; `as_of`; refs to Activity/Interest/Purchase facet versions; declared measure set; gaps[]; optional prior_snapshot_ref for comparison chains. |
| **Confidence** | Inherited ceiling from Product Confidence / Evidence — snapshot does not invent higher confidence. |
| **Freshness** | `as_of` / window_end; sealed historical snapshots are historical truth, not “live.” |
| **Relationships** | Snapshot → Product Identity; Snapshot → Activity + Interest + Purchase (refs); Snapshot ← Evidence/Confidence; consumers read Snapshot first. |
| **Never store** | Rank position, “Top products” lists, Home E-band placement, CTA copy, decision scores, AI narrative, presentation sort keys. |

**Boundary:** Snapshot is **understanding rollup**, not a leaderboard and not Guidance.

---

### 5.6 Product Evidence

**What is it?**  
Evidence Contract–compliant proof bundles whose **subject** is Product Identity (or a product-performance claim about it). Product Evidence is a **domain facet / Evidence kind family**, not a fork of Evidence anatomy.

**Why does it exist?**  
To answer: *what proof supports or refutes a product-performance claim?* and PP-Q5 (insufficient evidence) honestly.

**Who owns it?**  
Product Performance Domain for **product-performance claim assembly**; anatomy, strength, seal, isolation rules owned by **Commerce Evidence Contract**.

**How does it evolve?**  
Per Evidence Contract: draft → active → sealed; corrections via supersession; invalidation explicit. No AI dependency for eligibility/strength.

**What can reference it?**  
Product Confidence, Pattern, Knowledge, Guidance (Commerce Brain chain), Findings engines (as consumers of sealed evidence — they do not become SoT).

#### Contract

| Dimension | Definition |
|-----------|------------|
| **Identity** | `evidence_id` per Evidence Contract; `evidence_type` in a product-performance kind family (exact type catalog = future companion contract). |
| **Lifecycle** | Draft → Active → Sealed → Superseded / Invalidated. |
| **Properties** | Full Evidence anatomy: store_id, claim_ref, window, items[], sample_n, gaps[], strength, confidence_ceiling, validation_status, built_at/sealed_at, supersedes_id; subject = Product Identity (+ optional Snapshot/facet refs). |
| **Confidence** | `strength` + `confidence_ceiling` only — no parallel scoring engine. |
| **Freshness** | Evidence window + sealed_at. |
| **Relationships** | Evidence → Product Identity; Evidence items → Reality/Observation/Activity/Interest/Purchase/Snapshot refs; Confidence/Knowledge cite Evidence. |
| **Never store** | Causation-as-fact, cross-store pooled proof, Guidance text, UI excerpts as proof, silent rewrite of sealed evidence. |

**Boundary:** Observation ≠ Evidence. Snapshot ≠ Evidence. Product Evidence is the only proof path for product-performance Knowledge.

**Illustrative claim families (not decision logic):** interest_level, purchase_linkage, interest_without_purchase, insufficient_product_sample, temporal_change_support — to be named in a future `product_performance_evidence_contract_v1` if needed.

---

### 5.7 Product Confidence

**What is it?**  
The governed confidence and **evidence-sufficiency** object for product-performance claims about a Product Identity (typically bound to a Snapshot and/or sealed Product Evidence set).

**Why does it exist?**  
To answer: *may CartFlow claim this, and how strongly?* and PP-Q5 — without each surface inventing its own confidence chip logic.

**Who owns it?**  
Product Performance Domain (confidence facet), using Proof of Value + Evidence Contract vocabularies.

**How does it evolve?**  
When Evidence strength/gaps/sample_n change. AI cannot raise confidence. Insufficient/Unknown are valid terminal states that **block** Knowledge publish and Guidance offer when thresholds fail (per Evidence Contract).

**What can reference it?**  
Knowledge, Guidance, Decision (future), Executive Knowledge projection, Findings admission gates (consumers).

#### Contract

| Dimension | Definition |
|-----------|------------|
| **Identity** | Stable `product_confidence_id` (or deterministic key: store + product identity + claim_ref or snapshot_id + confidence_model_version). |
| **Lifecycle** | Draft → Active → Superseded. |
| **Properties** | Store scope; Product Identity ref; claim_ref and/or Snapshot ref; Evidence refs; confidence value (PoV-compatible); sufficiency (`sufficient` / `insufficient` / `unknown`); confidence_ceiling; gaps summary; as_of. |
| **Confidence** | This entity *is* the confidence record — it does not nest a second confidence system. |
| **Freshness** | as_of tied to Evidence/Snapshot freshness. |
| **Relationships** | Confidence → Evidence (+ optional Snapshot); Confidence → Product Identity; consumers may not exceed confidence_ceiling. |
| **Never store** | UI badge styles, “trust score” gamification, recommendation priority, merchant attention rank, fabricated Medium/High when evidence is insufficient. |

**Boundary:** Product Confidence is **claim sufficiency**, not identity-match confidence (Foundation) and not a Decision priority score.

---

## 6. Entity relationships

### 6.1 Relationship summary

```text
Store (MQIC)
  └── Product Identity (Foundation / Object Model Product)
        ├── Product Activity
        ├── Product Interest ──────────┐
        ├── Product Purchase ──────────┤  (comparable facets)
        │                              ▼
        ├── Product Performance Snapshot ──► Product Evidence ──► Product Confidence
        │            ▲                            │
        │            └──── cites facets ──────────┘
        └── (future) Pattern / Knowledge / Decision / Guidance  [Commerce Brain consumers]
```

| From | To | Cardinality | Meaning |
|------|----|-------------|---------|
| Product Activity | Product Identity | many → 1 | Activity is always about one identity (per store) |
| Product Interest | Product Identity | many → 1 | Interest windows about one identity |
| Product Interest | Product Activity | many → many (refs) | Interest grounded in activity |
| Product Purchase | Product Identity | many → 1 | Purchase linkage about one identity |
| Product Performance Snapshot | Product Identity | many → 1 | One snapshot row per identity×window×version |
| Product Performance Snapshot | Activity / Interest / Purchase | 1 → refs | Snapshot cites facet versions |
| Product Evidence | Product Identity | many → 1 (subject) | Proof about product claims |
| Product Evidence | Snapshot / facets | refs | Items cite rollup and/or facets |
| Product Confidence | Product Evidence | many → many (refs) | Confidence earned from evidence |
| Product Confidence | Snapshot | optional 1 | Confidence for a snapshot claim set |
| Knowledge / Guidance / Findings / Home | Snapshot + Evidence + Confidence | consume | Project only; never author |

### 6.2 Ownership boundaries

| Concern | Owner | Product Performance may… | Product Performance must not… |
|---------|-------|--------------------------|-------------------------------|
| Which store | Identity Authority (MQIC) | Scope all entities by store | Invent store identity |
| Which product | Product Identity Foundation | Cite `stable_identity_key` | Create alternate product keys / placeholders |
| Cart lifecycle state | Lifecycle Truth | Read observations/reality refs | Redefine abandoned/purchased cart state |
| Order/purchase occurred | Purchase Truth | Assemble product–purchase facet from mappings | Override purchase authority |
| Catalog/snapshot name authenticity | Identity Authenticity Rules | Refuse performance claims on inauthentic identity | Project «منتج X» as real |
| Evidence anatomy/strength | Commerce Evidence Contract | Specialize claim kinds for products | Fork strength vocabulary |
| “Now” / windows | Time Authority | Declare windows using TA | Invent clocks |
| What to show on Home | Home Surface / Executive Constitution | Supply consumable Snapshot/Confidence | Own Home bands or admission UI |
| What merchant should do | Decision / Guidance (future) | Provide Snapshot + Evidence + Confidence inputs | Emit recommendations or rankings |
| How Findings phrase insights | Business Findings / CI | Be cited as SoT inputs | Become Findings’ private product model |

---

## 7. Integration points with existing CartFlow foundations

| Foundation | Integration |
|------------|-------------|
| **Identity Foundation Architecture / Contract** | Gate: no Product Performance Knowledge without authentic Product Identity readiness for the subject. IF-P* / AR-* apply. |
| **Product Identity Foundation Map** | Subject grain and SoT tables (`cart_line_snapshots`, `product_catalog_entries`, mappings). |
| **Product Data Foundation** | Upstream plumbing for catalog, snapshots, purchase/hesitation mappings; PP consumes PDF outputs, does not replace PDF modules. |
| **Commerce Object Model** | Product remains identity object; PP entities are performance understanding **about** Product. Observation/Evidence/Pattern/Knowledge/Guidance remain Brain objects. |
| **Commerce Evidence Contract** | Product Evidence must satisfy E1–E9; strength/insufficient/unknown; seal/supersession; no causation-as-fact; store isolation. |
| **Commerce Decision Contract** | Future Decision may subject Product using PP Snapshot + Evidence + Confidence — Decision does not live in this domain. |
| **Commerce Temporal Change Contract** | Improving/declining (PP-Q3/Q4) via temporal comparison of sealed Snapshots / authorized change objects — not UI sparklines as truth. |
| **Commerce Brain v1.1** | Understand (Activity/Interest/Purchase/Snapshot) → Explain (Knowledge via Evidence) → Guide/Improve (future) — surfaces consume only. |
| **Commercial Question Registry** | CQ-P01…P03 (and future CQ-P*) draw answers from PP SoT; registry is question inventory, not performance storage. |
| **Business Findings / Reasoning Engines** | Downstream consumers; must not maintain a parallel product-performance model. |
| **Executive Knowledge / Home Executive Constitution** | Home/EQ layers project PP-derived Knowledge/Findings only; Home never computes PP truth (`HOME_SURFACE_CONTRACT_V1`). |
| **Proof of Value / Merchant Trust** | Evidence before speech; Unknown named; confidence earned; no fake intelligence. |
| **Time Authority** | All windows and `as_of` bound to TA. |
| **Execution Governance** | Future implementation WPs require architecture approval between packages; this charter alone authorizes **no code**. |

---

## 8. Future extension points (non-breaking)

Extensions must preserve entity contracts and SoT boundaries.

| Extension | Allowed approach | Forbidden approach |
|-----------|------------------|--------------------|
| New activity/interest/purchase measures | Versioned measure catalogs + new snapshot_version | Mutating sealed snapshot meaning in place |
| New commercial questions (CQ-P*) | Registry growth + map to existing PP entities | New Home-only product model |
| Product Performance Evidence type catalog | Companion `product_performance_evidence_contract_v1` | New Evidence anatomy fork |
| Temporal improvement/decline detectors | Compare sealed Snapshots under Temporal Change Contract | Mutable “trend_score” without provenance |
| Decision Engine / rankings / attention | Separate Decision/Guidance layer consuming Snapshot + Confidence | Storing ranks/scores on Snapshot as domain truth |
| Recommendations / merchant guidance | Guidance object citing Knowledge + Evidence | Recommendation payloads inside PP entities |
| Executive summaries / Home cards | Surface projection contracts | PP entities gaining E-band or card fields |
| Reports / charts | Read Snapshot + Evidence + Confidence | Chart configs inside domain entities |
| Category / collection performance | New subject grain only after Identity Foundation for that grain | Reusing product keys for categories loosely |
| Cross-product patterns | Pattern object about multiple Product Identities | Cross-store pooling |
| AI analysis | Propose candidates only under existing Brain gates; never raise confidence | AI-authored Snapshot/Evidence/Confidence |

**Versioning rule:** Additive fields and new optional measure keys are preferred. Renaming or redefining sealed snapshot semantics requires a new `snapshot_version` (or supersession), never silent reinterpretation.

---

## 9. Hard rules (PP-*)

| # | Rule |
|---|------|
| **PP-1** | Product Performance is the **SSOT** for product-performance understanding. |
| **PP-2** | Product Identity is **cited** from Foundation — never redefined here. |
| **PP-3** | No presentation, dashboard, Home, report, or widget logic in this domain. |
| **PP-4** | No recommendation, ranking, scoring, or Decision logic in this domain. |
| **PP-5** | Activity, Interest, and Purchase remain **separate facets**; Snapshot is the coherent rollup. |
| **PP-6** | Knowledge/Guidance about product performance require **Product Evidence** (Evidence Contract). |
| **PP-7** | Insufficient / Unknown confidence is valid and must block overclaiming. |
| **PP-8** | Store isolation is mandatory; no cross-tenant proof. |
| **PP-9** | Sealed Snapshots and sealed Evidence are immutable except via supersession. |
| **PP-10** | Consumers project; they do not author Product Performance truth. |
| **PP-11** | Future features must extend this foundation — not invent parallel product-performance models. |

---

## 10. Explicit non-goals (V1 charter)

This charter does **not** define or implement:

- Product scoring formulas  
- Decision Engine behavior  
- Recommendations or merchant guidance  
- Executive summary text  
- Dashboard cards, Home widgets, reports, charts  
- Product rankings or leaderboards  
- AI analysis  
- APIs, schemas, migrations, or runtime modules  

Those belong to future foundations that **consume** this domain.

---

## 11. Acceptance (charter completeness)

| Criterion | Status |
|-----------|--------|
| Canonical governed Product Performance domain exists | **Met** — this document |
| SSOT for product performance named | **Met** — §2.1, PP-1 |
| No presentation logic | **Met** — PP-I1, PP-3, Never-store rows |
| No dashboard logic | **Met** — out of scope + independence rules |
| No recommendation logic | **Met** — PP-I3, PP-4 |
| Extensible without redesign | **Met** — §8 versioning + extension table |
| Aligns with CartFlow governance | **Met** — Authority chain + §7 |
| Future features can build on foundation | **Met** — entity contracts + extension points |

---

## 12. STOP

**Documentation only.**  
No implementation, no schema, no Home/Dashboard wiring, no Findings rewrite, no Commercial Knowledge Expansion from this charter alone.

**Next (gated, separate WPs):** optional companion contracts (evidence type catalog, measure catalog), then architecture-approved implementation against Product Identity Foundation + PDF + Evidence Contract — still without UI ownership.
