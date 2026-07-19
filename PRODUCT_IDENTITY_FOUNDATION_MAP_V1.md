# Product Identity Foundation Map V1

**Status:** Implementation complete — readiness **READY** (see readiness report)  
**Date (UTC):** 2026-07-19  
**Domain:** Product  
**Governing architecture:** [`IDENTITY_FOUNDATION_ARCHITECTURE_V1.md`](IDENTITY_FOUNDATION_ARCHITECTURE_V1.md)  
**Investigation (complete):** [`PRODUCT_IDENTITY_AVAILABILITY_INVESTIGATION_V1.md`](PRODUCT_IDENTITY_AVAILABILITY_INVESTIGATION_V1.md)  
**Readiness:** [`IDENTITY_READINESS_CHECKLIST_V1.md`](IDENTITY_READINESS_CHECKLIST_V1.md) → **READY**  
**Readiness report:** [`PRODUCT_IDENTITY_FOUNDATION_READINESS_V1.md`](PRODUCT_IDENTITY_FOUNDATION_READINESS_V1.md)

> First application of Identity Foundation. PI-F1…PI-F7 implemented.  
> **Commercial Knowledge Expansion remains forbidden** until Product Review explicitly resumes it.

---

## 1. Canonical identity

| Element | Definition |
|---------|------------|
| **Grain** | One sellable product line identity per store, optionally variant-scoped |
| **Stable key** | `stable_identity_key` tiers A–E (`product_catalog_normalizer_v1.resolve_canonical_identity`) |
| **Tier A** | `product_id` + `variant_id` |
| **Tier B** | `product_id` + `sku` |
| **Tier C** | `product_id` |
| **Tier D** | `sku` |
| **Tier E** | normalized name hash (low confidence only) |
| **Tenant scope** | `store_slug` under MQIC (Identity Authority) |

**Human-readable identity:** display `name` (snapshot immutable; catalog mutable current truth).

**Immutable identifiers (historical):** snapshot `product_id`, `variant_id`, `sku`, `name`, `content_hash` on `cart_line_snapshots`.

---

## 2. Source of truth

| Fact | Source of truth | Owner module |
|------|-----------------|--------------|
| Line identity at capture time | `cart_line_snapshots` | `product_cart_snapshots_v1.py` |
| Current catalog identity | `product_catalog_entries` | `product_catalog_v1.py` |
| Product ↔ purchase | `product_purchase_mappings` | `product_purchase_mapping_v1.py` |
| Product ↔ hesitation | `product_hesitation_mappings` | `product_hesitation_mapping_v1.py` |
| Cart value / status (not product name) | `abandoned_carts` | cart event / lifecycle |
| Opaque legacy lines | `abandoned_carts.raw_payload` | secondary; not Foundation SoT |
| Merchant store scope | MQIC | Identity Authority |

**Not SoT for product name:** Findings fixtures, Home copy, Carts UI inference.

---

## 3. Investigation crosswalk (Q1–Q12)

| Q | Answer (proven) | Gate |
|---|-----------------|------|
| 1 Canonical? | Yes — tiers A–E + `stable_identity_key` | OK (declared) |
| 2 Created? | Widget `lines[]` attach; catalog JSON; sim `items` (degraded) | **Gap:** Zid lite often creates none |
| 3 Normalized? | `product_catalog_normalizer_v1` | OK when input present |
| 4 Persisted? | Snapshots + catalog + mappings | OK when `lines[]` present |
| 5 Snapshotted? | Insert-only `cart_line_snapshots.name` | **Gap:** hook reads `lines[]` only |
| 6 Projected? | **Carts:** not projected; Findings DB loader broken | **BLOCK** |
| 7 Consumed? | Purchase/hesitation mappings; Home CI; Carts omit | **BLOCK** (CI fixture) |
| 8 Silent disappear? | **Yes** — wrong columns → `{}`; empty `lines[]` | **BLOCK** |
| 9 Silent change? | Catalog mutable; snapshots immutable (OK if used) | Conditional |
| 10 Placeholders? | **Yes** — «منتج X» fixture on merchant path | **BLOCK** |
| 11 Historical loss? | Pre-foundation + totals-only cohorts | Documented |
| 12 Sim corrupt? | **Yes** — `name=product_key`; no `lines[]` | **BLOCK** |

---

## 4. Provider mapping

| Provider path | product_id | variant_id | sku | display name | Snapshot path today |
|---------------|------------|------------|-----|--------------|---------------------|
| Demo widget + catalog | `demo_*` | rare | `DEMO-*` | Real catalog name | `lines[]` when attach works |
| Zid lite bridge | often none | none | none | none | often none (counts only) |
| Zid globals with products/items | variable | variable | variable | variable | if capture reads arrays |
| Store Reality Simulator | `demo_*` id | — | via catalog | **key written as name** | **`items` only — no snapshots** |
| Findings fixture | `prod_x` | — | — | **منتج X** | N/A (not real) |

---

## 5. Snapshot strategy

| Rule | Status |
|------|--------|
| Capture sources: `cart_state_sync`, `cart_abandoned` only | Implemented |
| Input: `payload.lines[]` | Implemented — **too narrow** vs sim `items` |
| Insert-only; dedupe `content_hash` | Implemented |
| Fields frozen: id/variant/sku/**name**/price/qty | Implemented |
| Max 20 lines | Implemented |

**Foundation gap:** Any production/sim path that persists product lines only under `items`/`cart` without `lines[]` never enters Foundation snapshots.

---

## 6. Projection strategy

| Surface / consumer | Required projection | Today |
|--------------------|---------------------|-------|
| Carts row / detail | Snapshot or catalog `name` **or** unresolved | **Missing** — value/status/timing only |
| Findings evidence | Aggregate by stable key + real `name` | **Broken** — queries `product_name`/`created_at` |
| Home Commercial Intel | Real name or unresolved; no fixture | **Fixture contamination** |
| Purchase mapping | Snapshot name at purchase | Implemented when snapshots exist |
| Product data health | Coverage metrics | Implemented (diagnostic) |

---

## 7. Historical consistency

| Cohort | Policy |
|--------|--------|
| Pre–`cart_line_snapshots` | Unresolved unless honest `raw_payload` backfill approved |
| Zid totals-only | Unresolved — no invented names |
| Sim key-as-name rows | Not merchant-authentic display; fix forward + optional catalog join |
| No invented backfill | AR-8 / IF-11 |

---

## 8. Simulator compatibility

| Requirement | Status |
|-------------|--------|
| Use catalog display name in cart identity fields | **FAIL** (`ingress_adapter_v1` uses `product_key`) |
| Emit `lines[]` (or shared normalizer) into snapshot hook | **FAIL** |
| Isolation under demo store / run tags | Owned elsewhere (SRS identity isolation) |

---

## 9. Failure modes

| Mode | Symptom | Merchant impact |
|------|---------|-----------------|
| F1 Fixture admission | «منتج X» + fake metrics | Authenticity breach |
| F2 Broken loader | Wrong ORM columns | Empty products; silent |
| F3 Engine default fixture | `load_db=False` → rich fixture | Production risk if composition slips |
| F4 No `lines[]` | Zero snapshots | No Product↔Purchase; no names |
| F5 UI omission | Carts never shows name | Merchant cannot see product even when known |
| F6 Sim key-as-name | `hp_air` as title | Corrupted training / demo knowledge |
| F7 Tier E collision | Name-hash merge | Wrong product linkage |

---

## 10. Fallback policy (Product)

| Condition | Allowed fallback |
|-----------|------------------|
| No snapshot, no trusted raw line name | **Unresolved** or suppress product finding |
| Snapshot name present | Use snapshot `name` |
| Catalog name + stable key, no snapshot | Allowed for **current** catalog speech only — not historical cart claims |
| Loader/DB failure | **Fail closed** — insufficient evidence; **never** fixture |
| Review lab | Explicit `source=fixture` only |

**Forbidden:** Product X / منتج X / Product A / random peer labels / engine demo_rich on merchant Home.

---

## 11. Authenticity guarantees (Product)

Binds to [`IDENTITY_AUTHENTICITY_RULES_V1.md`](IDENTITY_AUTHENTICITY_RULES_V1.md):

| Guarantee | Status |
|-----------|--------|
| AR-1 real or unresolved only | **Violated** (fixture) |
| AR-2 no placeholders | **Violated** |
| AR-4 fixture isolation | **Violated** on CI validation path |
| AR-5 simulator honesty | **Violated** |
| AR-6 observable degrade | **Violated** (silent `{}`) |
| AR-7 projection honesty | **Violated** (Carts omit; Home fakes) |

---

## 12. Readiness scorecard

| Checklist group | Result |
|-----------------|--------|
| R-A Investigation | **PASS** (investigation complete) |
| R-B Foundation artefacts | **PARTIAL** (this map = draft; sim/projection gaps open) |
| R-C Authenticity | **PASS** |
| R-D Engineering proof | **PASS** |
| R-E Approvals | Pending Product Review of READY report |

**Domain readiness: READY** (implementation) — Commercial Knowledge still gated on Product Review

---

## 13. Implementation order (dependency-ordered — do not start Knowledge)

Work packages must follow Identity Foundation, not “patch the label”:

| Order | Work | Closes |
|-------|------|--------|
| **PI-F0** | Governance approval of Architecture + this map | R-E path start |
| **PI-F1** | Authenticity gate: merchant path never admits `demo_rich_fixture_v1`; no default fixture | F1, F3, AR-4 |
| **PI-F2** | Fix findings loader columns (`name`, `captured_at`); prefer `stable_identity_key` + real name | F2, IF-8 |
| **PI-F3** | Capture completeness: Zid/`lines[]` reliability (prior widget audit) | F4 |
| **PI-F4** | Simulator: display name + `lines[]` into snapshot path | F6, AR-5 |
| **PI-F5** | Carts projection + UI: real name or unresolved | F5, IF-6 |
| **PI-F6** | Production verification (health + one cart + one purchase + Home provenance) | R-D5 |
| **PI-F7** | Readiness re-score → READY → Product/Architecture sign-off | R-E3 |

**Only after PI-F7:** Truth Validation refinements → Knowledge → Commercial Knowledge Expansion.

**Explicitly out of order / forbidden now:**

- Commercial Knowledge Expansion V1  
- Home redesign  
- Replacing «Product X» with another synthetic label  

---

## 14. Regression / verification (Product)

Inherited from investigation §8–§9; mandatory before READY:

- Loader schema contract test  
- Fixture isolation test (`load_db` / merchant Home)  
- Forbidden-string test (`منتج X`, `Product X`, …)  
- Snapshot golden path + totals-only negative path  
- Purchase mapping name propagation  
- Simulator display-name + lines ingest  
- Carts projection field or unresolved  
- Production: `/api/product-data/health` + SQL samples + Home `evidence_loaded_from`

---

## 15. STOP

- Identity Foundation governance applied to Product Identity via this map.  
- Product Identity readiness remains **BLOCKED**.  
- Await approval of Identity Foundation Architecture V1 + companions.  
- Then execute PI-F1…PI-F7 under this map.  
- **Do not expand Commercial Knowledge until READY (approved).**
