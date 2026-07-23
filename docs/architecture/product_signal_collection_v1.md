# CartFlow Product Signal Collection V1

**Status:** Governed platform layer (architecture + runtime collection)  
**Date (UTC):** 2026-07-20  
**Authority:** Subordinate to [`product_performance_domain_model_v1.md`](product_performance_domain_model_v1.md), [`commerce_signals_foundation_v1.md`](commerce_signals_foundation_v1.md), [`commerce_evidence_contract_v1.md`](commerce_evidence_contract_v1.md), Product Identity Foundation ([`PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md`](../../PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md)), Product Data Foundation ([`cartflow_product_data_foundation_architecture_v1.md`](../cartflow_product_data_foundation_architecture_v1.md)), Merchant Trust, Time Authority.  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Scoring, trends, conversion rates, opportunity detection, rankings, Decision Engine, Executive Knowledge, recommendations, merchant guidance, AI analysis, dashboards, Home widgets, new merchant UI

> **Law:** Signals are **facts**. Knowledge is built later.  
> Never mix collection with interpretation.  
> Every future Product Performance calculation must read from this layer — not reconstruct product activity independently.

---

## 0. Purpose

Product Signal Collection is the governed layer that **records canonical product-related facts** so Product Performance (and every consumer) can trust a complete evidence base.

| This layer does | This layer must never |
|-----------------|------------------------|
| Capture atomic “what happened” about a Product Identity | Analyze, score, or rank |
| Persist reusable platform assets | Decide or recommend |
| Point at evidence / truth rows | Invent product identity |
| Stay UI-independent | Emit presentation fields |

**Relationship to Commerce Signals Foundation:** Commerce Signals V1 is a **read projection** (Recovery/Purchase families today). Product Signal Collection is the **durable Product-family collection store**. Future Brain/Pulse projection may read from this store; it must not create a second product event vocabulary.

**Relationship to Product Performance Domain:** Collection feeds Product Activity / Interest / Purchase facets. Domain rollups and Confidence are **not** computed here.

---

## 1. Placement

```text
Platform event / truth (cart-event, reason, purchase, return, recovery timeline)
        ↓
Product Identity resolution (Foundation / PDF — cite only)
        ↓
Product Signal Collection   ← THIS LAYER (atomic facts + evidence_refs)
        ↓
Product Performance Domain (Activity / Interest / Purchase / Snapshot / Evidence / Confidence)
        ↓
Commerce Brain / Findings / Executive Knowledge / Surfaces   (consumers only)
```

---

## 2. Canonical signal catalog

### 2.1 Families

| Family | Code | Canonical meaning | V1 collector |
|--------|------|-------------------|--------------|
| **Product Exposure** | `product_exposure` | Product was shown/exposed in a storefront context | Catalog only — **not wired** (no durable exposure event today) |
| **Product View** | `product_view` | Product detail/view occurred | Catalog only — **not wired** (no PDP view persist today) |
| **Product Interest** | `product_interest` | Customer interest/hesitation involved this product | **Wired** — reason capture → hesitation mapping path |
| **Product Cart Activity** | `product_cart_activity` | Cart composition activity involved this product | **Wired** — `cart_state_sync` / `cart_abandoned` + lines/snapshots |
| **Product Checkout Activity** | `product_checkout_activity` | Checkout-context activity involved this product | **Partial** — when sync `reason=checkout` or return context `checkout` |
| **Product Purchase** | `product_purchase` | Purchase Truth linked to this product | **Wired** — after purchase mapping |
| **Product Recovery Interaction** | `product_recovery_interaction` | Recovery timeline step while product present in session | **Wired** — after recovery truth timeline insert |
| **Product Customer Return** | `product_customer_return` | Customer returned commercially; product present in session | **Wired** — after behavioral return persist |
| **Product Evidence Events** | `product_evidence` | Durable product-scoped evidence/truth link recorded | **Wired** — companion when snapshot/mapping evidence refs are available |

### 2.2 Signal types (atomic past facts)

| `signal_type` | Family | Meaning |
|---------------|--------|---------|
| `product_exposed` | product_exposure | Product exposed (deferred) |
| `product_viewed` | product_view | Product viewed (deferred) |
| `product_interest_hesitation` | product_interest | Product present when hesitation reason captured |
| `product_cart_added` | product_cart_activity | Product present on cart sync with reason `add` |
| `product_cart_removed` | product_cart_activity | Product present on cart sync with reason `remove` |
| `product_cart_synced` | product_cart_activity | Product present on cart sync (other/page_load) |
| `product_cart_abandoned` | product_cart_activity | Product present when cart abandoned |
| `product_checkout_touched` | product_checkout_activity | Product present in checkout-context activity |
| `product_purchased` | product_purchase | Product linked after Purchase Truth confirmation |
| `product_recovery_started` | product_recovery_interaction | Product present when recovery timeline status indicates start |
| `product_recovery_progressed` | product_recovery_interaction | Product present on later recovery timeline status |
| `product_customer_returned` | product_customer_return | Product present when commercial return persisted |
| `product_evidence_linked` | product_evidence | Evidence/truth row linked for this product (snapshot or mapping id) |

### 2.3 Minimum persisted fields

Aligned with Commerce Signals spirit + Product Identity grain:

| Field | Meaning |
|-------|---------|
| `signal_family` | Family code from §2.1 |
| `signal_type` | Atomic past-fact type from §2.2 |
| `store_slug` | MQIC store scope |
| `stable_identity_key` | Product Identity Foundation key (required) |
| `identity_tier` | A–E when known |
| `session_id` / `cart_id` / `recovery_key` | Commerce subject links when known |
| `observed_at` | When observed (naive UTC) |
| `source` | Platform source string (e.g. `cart_state_sync`, `purchase_truth`, `reason_capture`) |
| `evidence_ref_type` / `evidence_ref_id` | Pointer to backing truth row when available |
| `dedup_hash` | Deterministic insert-only uniqueness |

**Never store:** scores, ranks, recommendations, UI labels, confidence inventions, causal stories, conversion rates.

---

## 3. Ownership

| Concern | Owner |
|---------|-------|
| Signal catalog + collection rules | Product Signal Collection (`services/product_data/product_signal_*`) |
| Product identity keys | Product Identity Foundation / PDF normalizer |
| Cart line snapshot truth | `product_cart_snapshots_v1` |
| Hesitation / purchase mappings | PDF mapping modules |
| Purchase occurred | Purchase Truth |
| Recovery status transitions | Recovery Truth Timeline |
| Return-to-site behavioral fact | Behavioral recovery / return path |
| Interpretation / Knowledge | Commerce Brain / Product Performance Domain (downstream) |
| Surfaces | Home / Dashboard / Reports (consumers only) |

---

## 4. Signal lifecycle

```text
Observed platform event
  → Identity resolve (or skip if unresolved)
  → Draft candidate signal(s) (in-memory)
  → Dedup check
  → Insert-only persist (Active historical fact)
  → Never update / never reinterpret
```

| State | Rule |
|-------|------|
| **Skipped** | Missing store/session, unresolved identity, empty products, collector error (never raises to caller) |
| **Inserted** | New `dedup_hash` |
| **Duplicate** | Same `dedup_hash` — no-op |
| **Sealed** | All inserted rows are immutable history |

Corrections = new superseding facts in future versions — not silent mutation.

---

## 5. Collection rules

| # | Rule |
|---|------|
| **PSC-1** | One signal = one happened fact about one Product Identity. |
| **PSC-2** | Resolve identity only via Foundation normalizer (`resolve_canonical_identity`). |
| **PSC-3** | Prefer products from payload `lines[]`; else session `cart_line_snapshots`. |
| **PSC-4** | Never invent products when none are present — skip honestly. |
| **PSC-5** | Never raise into cart-event / purchase / recovery paths. |
| **PSC-6** | No aggregates, rates, trends, or “opportunity” fields at write time. |
| **PSC-7** | Store isolation mandatory. |
| **PSC-8** | Deferred families remain typed in catalog with **no writer** until a real source exists. |
| **PSC-9** | Consumers must read `product_signal_events` (or published read helpers) — not re-parse widget payloads for the same facts. |

---

## 6. Relationship map

```text
Store
 └── Product Identity (stable_identity_key)
       ├── product_cart_* / product_checkout_touched
       ├── product_interest_hesitation
       ├── product_purchased
       ├── product_recovery_*
       ├── product_customer_returned
       └── product_evidence_linked
             └── evidence_ref → cart_line_snapshots | product_*_mappings | recovery_truth_timeline_events | …
```

| Signal family | Feeds Product Performance entity (future) |
|---------------|-------------------------------------------|
| Cart / Checkout / Return / Recovery | Product Activity |
| Interest | Product Interest |
| Purchase | Product Purchase |
| Evidence linked | Product Evidence inputs |
| (all, with sufficiency later) | Product Confidence / Snapshot |

---

## 7. Integration points

| Foundation | Integration |
|------------|-------------|
| Product Identity Foundation | Subject key + authenticity gate upstream |
| PDF hooks | Collection attached after snapshots / hesitation / purchase mapping |
| Purchase Truth | Purchase signals only after confirmed purchase |
| Recovery Truth Timeline | Recovery interaction signals after successful timeline insert |
| Behavioral return | Customer return signals after persist |
| Commerce Signals Foundation | Shared “what happened” philosophy; Product family durability lives here |
| Product Performance Domain | Downstream SoT consumer of collected signals |
| Home / Dashboard | **No wiring** in V1 |

### Runtime modules

| Module | Role |
|--------|------|
| `services/product_data/product_signal_types_v1.py` | Catalog constants |
| `services/product_data/product_signal_collection_v1.py` | Persist + resolve + read helpers |
| `services/product_data/product_signal_hook_v1.py` | Never-raise delegates |
| `schema_product_signal_events_v1.py` | Schema ensure |
| `models.ProductSignalEvent` | Append-only table |
| Alembic `u4v5w6x7y8z9_add_product_signal_events` | Migration |

---

## 8. Extension points

| Extension | How without breaking contracts |
|-----------|--------------------------------|
| Product Exposure / View | Add writers when widget emits durable product_id events; keep types already reserved |
| New signal types | Additive constants + new writers; never reuse type for a different meaning |
| Commerce Brain Product family projection | Read from `product_signal_events`; do not redefine types |
| Measure catalogs / Snapshots | Separate Product Performance WP consuming this store |
| Kill switch | `CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1=0` disables writers (default **on**) |

---

## 9. Acceptance

| Criterion | Status |
|-----------|--------|
| Governed collection layer exists | Met |
| Canonical catalog defined | Met |
| Ownership documented | Met |
| Reusable by future foundations | Met (`product_signal_events` + read helpers) |
| No business decisions | Met |
| No presentation logic | Met |
| Existing contracts intact | Met (hooks are additive, never-raise) |

---

## 10. STOP

No scoring, Decision, Home, or recommendation work follows from this document alone.  
Exposure/View remain unwired until real sources exist.
