# Merchandising Mission Distinctness Audit V1

**Status:** CLOSED AS AUDIT (no implementation)  
**Date (UTC):** 2026-09-09  
**IMPLEMENTATION:** NO  
**DEPLOY:** NO  
**Mode:** Observe → falsify → invariants. No guess-to-code.

**Primary verdict:** `EXISTING_MISSIONS_ALREADY_OWN_THE_AVAILABLE_OPPORTUNITIES`

Products V1.2 is a product-fact surface. It is not a second Mission Catalog.

---

## 1. Observed owners (evidence)

| Layer | Owner | Opportunity identity |
|-------|--------|----------------------|
| Product facts | `product_read_model_contract_v1` → `products_commercial_truth_v1` | page-only `GET /api/dashboard/products` |
| Commercial opportunity | COL | `col:{family}:{reason}:{store_slug}` — **store**, not SKU |
| Mission lifecycle | Mission Catalog → Portfolio → CDC → Workspace | family-agnostic CDC |
| Existing merchandising families | `product_confidence`, `product_opportunity_focus` | already in `MISSION_PROFILES` + conflict group `merchandising_trust_theme` |
| Merchandising gate | `MERCHANDISING_EVAL_FAMILIES` | withheld from normal merchants |

COL `product_opportunity_focus` is explicitly store-level quality+warranty concentration. Copy forbids exposure / placement / ads / discount conclusions.

`PRODUCT_SCOPED_SHIPPING_CLAIM_ALLOWED = False`. Store-level 12/20 shipping must not become a product causal claim.

---

## 2. Product-scoped evidence contract

| Field | Class | Notes |
|-------|--------|--------|
| `product_id` / name / price | AUTHORITATIVE · PRODUCT-SCOPED | `ProductCatalogEntry`; degraded fallback when name missing |
| cart_count / cart_value | AUTHORITATIVE · PRODUCT-SCOPED | `CartLineSnapshot` ⨝ `AbandonedCart` (cart value is cart-level attributed to lines) |
| purchases / revenue | AUTHORITATIVE · PRODUCT-SCOPED | `ProductPurchaseMapping`; absent rows = known **0**, not unknown |
| hesitation_reason_counts | AUTHORITATIVE · PRODUCT-SCOPED | `ProductHesitationMapping` via session/cart join — not store rollup |
| store hesitation 12/20 | STORE-LEVEL ONLY | COL / OGL. Must not be copied onto a SKU |
| real merchant PDP / unique visitors | NOT STORED · UNKNOWN | `KNOWN_UNKNOWNS` |
| lab `product_viewed` | LAB-ONLY | labelled; forbidden as real exposure |
| COL `commercial_family` on a card | DERIVED · usually STORE-LEVEL | only if a product-scoped join is proven |
| `cart_behavior` family | UNSUPPORTED | reserved in catalog; not composed |

---

## 3. Candidate falsification (A–E)

### A) Placement / distribution

**Hypothesis:** strong behavior when encountered, insufficient exposure.

**FACT available:** carts, value, purchases, lab-only visits on lab tenant.  
**FACT missing:** real merchant exposure / unique visitors / PDP views.

**Verdict:** BLOCKED for normal merchants. Lab visits are not enough.  
This *would* be a new commercial class **if** exposure ingestion existed. It does not.

### B) Product-page confidence / merchandising

**Hypothesis:** carts without purchase + quality/warranty hesitation.

**Already owned by:** `product_confidence` (single trust reason) and `product_opportunity_focus` (quality+warranty pool).  
Action = show existing quality/warranty proof on the product page. Metric = hesitation share, 7 days.

Product-scoped quality counts, if present, are a **scope refinement** of that family — not a new family.

**Verdict:** DUPLICATE_INTENT.

### C) Price / value presentation

**Already owned by:** `price_hesitation`.  
Live R17 عود ملكي مركز: 5 product-scoped price reasons. That is still price, not merchandising.

**Verdict:** DUPLICATE_INTENT. Do not alias.

### D) Cart performance (carts / value, 0 purchases)

Live R17 طقم العناية الفاخر: 4 carts · 996 ر.س · 0 purchases · no hesitation · visits unavailable.

| Layer | Content |
|-------|---------|
| FACT | 4 carts, 996 SAR, 0 purchases (purchase truth authoritative) |
| DERIVED SIGNAL | presentation-only `neutral` / `limited` |
| DIAGNOSIS | **not licensed** — no page / price / placement / ad cause |
| RECOMMENDATION | none |
| MEASUREMENT / RECHECK | cannot define without a denominator (exposure or a joined hesitation class) |

`FAMILY_CART_BEHAVIOR` is catalog-reserved and unsupported. Do not promote this fact to a mission.

**Verdict:** FACT only. Insufficient for a new mission.

### E) Assortment / “focus product X before Y”

No authoritative comparable exposure or purchase-rate denominator.  
Products V1.2 order is readability, not a ranker (`frontend_ranking = 0`).

**Verdict:** BLOCKED.

---

## 4. Distinctness matrix

Overlap key: **E** evidence · **A** action · **M** measure · **R** recheck · **I** identity · **C** conflict · **D** duplicate-intent

| Candidate | shipping_friction | price_hesitation | product_confidence | recovery_hesitation | communication_followup |
|-----------|-------------------|------------------|--------------------|---------------------|------------------------|
| A placement | low E; different A if exposure existed | low | low | none | none |
| B page confidence | conflict group vs price | **pricing_value_theme** | **SAME family** E/A/M/R/I | COL-only thinking | none |
| C price presentation | distinct reason | **SAME family** | conflict group | none | none |
| D carts w/o purchase | none unless shipping mapped | none unless price mapped | none unless quality mapped | none | none |
| E assortment | none | none | none | none | none |

B and C are DUPLICATE_INTENT.  
A is distinct-class but missing truth.  
D and E are not missions.

---

## 5. Reality cases (R17 live / production-shaped)

| Product | FACT | Maps to | Mission? |
|---------|------|---------|----------|
| عود ملكي مركز | 5 carts · 945 · 0 purch · price hes=5 · lab visits=5 | `price_hesitation` | existing |
| عنبر ليلي | 4 carts · 596 · 0 purch · shipping hes=4 · lab visits=4 | `shipping_friction` | existing |
| طقم العناية الفاخر | 4 carts · 996 · 0 purch · no hes · visits unavailable | fact only | no |
| missing-name | degraded identity · 1 cart · 39 | fail-safe | no SKU mission |
| normal merchant | visits `NOT_STORED` | never 0 visits | placement blocked |

Store-level R17 shipping 12/20 remains OGL/COL, not a product diagnosis.

---

## 6. Portfolio / CDC compatibility (if someone later scopes SKU)

Opportunity keys are **store-shaped**. A SKU key would be new identity work — out of scope here.

Existing conflict groups already prevent stacking:

- `price_hesitation` + `product_confidence`
- `product_confidence` + `product_opportunity_focus`

Hypothetical states:

| Situation | Safe behavior |
|-----------|----------------|
| shipping ACTION_CHOSEN + merchandising READY | allowed (different families) if merchandising gate permits |
| merchandising UNDER_MEASUREMENT + price READY | suppress via `pricing_value_theme` |
| merchandising vs product_confidence | suppress via `merchandising_trust_theme` |
| insufficient exposure | INSUFFICIENT / no new mission |
| degraded / removed product | no SKU mission; catalog fallback only |
| tenant isolation | Products compose is store-scoped; founder-eval live had 0 lab SKUs |

Do not add frontend ranking.

---

## 7. Query fanout — CLOSED (dedicated task 2026-09-09)

`PRODUCTS_READ_MODEL_QUERY_FANOUT_V1` is **CLOSED** by the dedicated consolidation task. This merchandising audit did not close it and added **0** queries.

Pack: `docs/architecture/products_read_model_query_fanout_v1/`  
Closed cost: normal **+1** · lab **+1** · N+1 **0**

| # | Owner | Purpose | Class |
|---|--------|---------|--------|
| 1 | Consolidated CTE read (`load_consolidated_v1`) | identity + carts + purchases + hesitation (+ lab visits in the same lab SQL) | REQUIRED · MERGED |

**Governance:** no merchandising mission implementation may begin from this audit. Closing the fanout debt does not authorize merchandising design.

---

## 8. Economic gate (future mission, if ever designed)

| Cost | Target |
|------|--------|
| AI / store / day | 0 |
| External / store / day | 0 |
| DB / store / Products page | +1 normal / +1 lab (fanout debt CLOSED) |
| Scheduler / store / day | 0 |
| Storage / store / month | none from this audit |

---

## 9. Failure tests (fail-safe = INSUFFICIENT / NO NEW MISSION)

| Class | Result |
|-------|--------|
| missing exposure | BLOCK A and E |
| lab exposure on normal merchant | contract forbids; visits omitted / NOT_STORED |
| store evidence on product | `PRODUCT_SCOPED_SHIPPING_CLAIM_ALLOWED=False` |
| product hesitation generalized to store | COL remains store rollup; Products stays SKU-mapped |
| duplicate price / confidence | B, C = DUPLICATE_INTENT |
| revenue as causality | not licensed |
| 0 purchases without denominator | FACT only (D) |
| missing / stale / removed identity | degraded / drop card |
| unknown family | catalog fail-closed |
| frontend ranking | 0 |
| query fanout worse | audit Δ 0 |

---

## 10. Invariants (do not violate later)

1. No new merchandising family from Products V1.2 facts.
2. Fact ≠ diagnosis ≠ causal claim.
3. Unknown exposure ≠ 0 visits.
4. Lab visits stay lab-only.
5. Do not alias price or product_confidence as “merchandising”.
6. Lifecycle remains Catalog → Portfolio → CDC → Workspace.
7. Fanout debt `PRODUCTS_READ_MODEL_QUERY_FANOUT_V1` is CLOSED (2026-09-09 dedicated task). That does not authorize merchandising implementation.
8. Frontend ranking stays 0.

---

## Closure

Audit complete. Fanout debt `PRODUCTS_READ_MODEL_QUERY_FANOUT_V1` was closed by a later dedicated task. Merchandising design / implementation remain **NO**.
