# Product Identity Availability Investigation V1

**Status:** CRITICAL INVESTIGATION — complete (no implementation)  
**Date (UTC):** 2026-07-19  
**Scope:** End-to-end product identity availability across CartFlow  
**Constraint:** Investigate only. Do not implement Commercial Knowledge Expansion. Do not redesign Home/Carts. Do not patch labels.

---

## Executive verdict

CartFlow can compute **product-level behavior counts** while merchant surfaces fail to show **real product identity** for **three independent, proven causes** — not one shared mystery:

| # | Cause | Classification | Contaminates merchant surface? |
|---|--------|----------------|--------------------------------|
| **A** | Home “Product X” / «منتج X» is a **hard-coded demo fixture** (`demo_rich_fixture_v1`), not unresolved production identity | **7 — Simulator/fixture placeholder labels** | **Yes** — Commercial Intelligence + Review Labs + validation evidence |
| **B** | Live DB product-interest loader queries **non-existent columns** (`product_name`, `created_at`) on `cart_line_snapshots` | **2 — Exists in tables but missing from projections** (broken consume path) | **Yes (silent)** — empty products → no real product findings; engine may fall back to fixture |
| **C** | Carts merchant UI **never projects or renders** product names (value/status/timing only) | **1 — Identity may exist; missing from UI** (+ often **4** when Zid/history lack snapshots) | **Yes** — Carts page by design of current projection |

**Authenticity rule breach:** Merchant-facing Home Commercial Intelligence evidence used fixture copy «منتج X» with fabricated metrics (34 adds / 22 carts / 2 purchases). That string is **not** an honest unresolved state.

**STOP.** Await Product Review before any fix implementation.

---

## 1. End-to-end identity trace

Trace one product through every stage. Field availability uses:

- **Demo sandbox catalog** (real names exist): e.g. `TrueSound Air — سماعة خفيفة` / `demo_hp_air`
- **Store Reality Simulator cart write** (name degraded to key): `name = product_key` (e.g. `hp_air`)
- **Foundation snapshot model** (correct schema): `CartLineSnapshot.name`
- **Findings fixture** (fabricated): `prod_x` → «منتج X»

### Stage map

| Stage | product_id | provider_product_id | variant_id | product_name | normalized_name | snapshot_name | Source of truth | Fallback | Identity available? | Consumed? | Silent degrade? |
|-------|------------|---------------------|------------|--------------|-----------------|---------------|-----------------|----------|---------------------|-----------|------------------|
| **1. Provider / storefront payload** | Optional on line (`product_id` / nested `product.id` / bare `id`) | Same as platform id when present | Optional `variant_id` | `name` / `title` / `product_name` | n/a | n/a | Platform `window.cart` / Zid cart object | Counts-only if lines absent | **Variable** — demo high; Zid lite often none | Widget attach only if lines readable | **Yes** — empty `lines[]` |
| **2. Widget Product Identity capture** | Extracted | = product_id | Extracted | Extracted → `name` | n/a | n/a | `cartflow_product_identity_capture.js` | `lines=[]` on failure | Only if storefront exposes line arrays | Attached on `cart_state_sync` / `cart_abandoned` | **Yes** — never throws |
| **3. Canonical normalization** | Tier A–E key input | n/a | Tier A | Display `name` | `normalize_product_name` (lower/collapse) | n/a | `product_catalog_normalizer_v1.py` | Tier E name-hash if no id/sku | Yes if any of id/variant/sku/name | Catalog upsert + purchase/hesitation mapping | Tier E is low-confidence merge risk |
| **4. Canonical cart line (payload)** | On `lines[]` | = product_id | On `lines[]` | On `lines[].name` | n/a | n/a | Event payload after attach | Legacy `cart` / `items` in `raw_payload` | Only when widget/sim writes lines/items | Snapshot hook reads **`lines[]` only** — not `items` | **Yes** — `items` without `lines` → no snapshots |
| **5. Cart line snapshot persistence** | `cart_line_snapshots.product_id` | stored as product_id | `variant_id` | — | — | **`name`** | `product_cart_snapshots_v1.py` → model `CartLineSnapshot` | Skip line if no identity fields | **Yes when `lines[]` present** | Downstream mappings/catalog | Duplicate skip via `content_hash` |
| **6. Product identity / catalog record** | `product_catalog_entries.product_id` | same | `variant_id` | `name` | via resolve key | n/a | `product_catalog_v1.py` + `stable_identity_key` | Weaker tier may remain until upgrade | Yes after catalog hook | Purchase/hesitation use key | Name mutable (current truth); snapshots immutable |
| **7. Cart projection (merchant Carts)** | **Not projected** | — | — | **Not projected** | — | **Not projected** | `dashboard_snapshot_normal_carts_slim_v1` allowlist + `cart_detail_projection_v1` | Value/status/timing only | Often unused even if DB has it | **No** — UI omits | N/A (omission) |
| **8. Purchase mapping** | Copied from snapshot | — | via identity key | `product_purchase_mappings.name` | via identity | from snapshot | `product_purchase_mapping_v1.py` after Purchase Truth | Skip if no session snapshots | **Only if snapshots exist for session** | Findings/KL can count mappings | Empty session → no Product↔Purchase facts |
| **9. Product metrics / findings** | Group key (intended) | — | — | `name_ar` from load | — | intended `name` | **Fixture:** hard-coded; **DB:** broken query | Fixture «منتج X» / empty products | Fixture: fake; DB: usually empty | Home Commercial Intel consumes findings | **Yes** — wrong columns → `{}` |
| **10. Commercial Knowledge / Home** | `scope_reference` e.g. `prod_x` | — | — | Title/summary text | — | — | Findings → `home_commercial_intelligence_v1` | Demo fixture when `demo_fixture` or default | Fixture names only unless DB fixed | Understanding / Opportunity | **Yes** — authenticity breach |
| **11. Carts page** | — | — | — | — | — | — | Row render in `merchant_dashboard_lazy.js` | SAR + status + time + phone | **Not displayed** | No | N/A |

### Concrete sample records (code / fixtures)

**A. Foundation snapshot (test / intended production shape)** — `tests/test_product_cart_snapshots_v1.py`:

```json
{
  "product_id": "prod-100",
  "variant_id": "var-10",
  "sku": "SKU-100",
  "name": "Snapshot Product",
  "unit_price": 49.5,
  "quantity": 2
}
```

Persisted columns (`models.py` / Alembic `h8i9j0k1l2m3`):  
`product_id`, `variant_id`, `sku`, **`name`**, `unit_price`, `quantity`, `captured_at`, `capture_source`, `capture_confidence`, `content_hash`.

**B. Demo catalog (real names available)** — `services/demo_sandbox_catalog.py` / sim manifest:

```json
{
  "key": "hp_air",
  "id": "demo_hp_air",
  "name": "TrueSound Air — سماعة خفيفة",
  "sku": "DEMO-HP-AIR",
  "price": 119.0
}
```

Evidence: `docs/architecture/reality_validation_lab_v1_small/.../simulation_manifest.json` products[].

**C. Simulator cart persistence (name lost at write)** — `services/store_reality_simulator/ingress_adapter_v1.py` `_upsert_cart`:

```python
"items": [{"id": ev.product_id, "name": ev.product_key, "price": ev.product_price, "qty": 1}]
```

So a cart for TrueSound Air stores **`name: "hp_air"`** (key), not the catalog display name. Also writes **`items`**, not widget **`lines[]`** → snapshot hook does not ingest this path.

**D. Findings fixture (Product X)** — `services/business_findings_evidence_v1.py` `build_demo_rich_evidence_bundle_v1`:

```python
"prod_x": {
    "name_ar": "منتج X",
    "add_to_cart": 34,
    "unique_carts": 22,
    "purchases": 2,
    ...
}
```

Rendered finding (exact metrics observed by Product):  
`docs/business_findings/business_findings_demo_package_v1.json` →  
«أُضيف منتج X إلى السلة 34 مرة عبر 22 سلة، بينما اكتمل الشراء 2 مرة فقط (6%).»

Home validation evidence used the same fixture:  
`HOME_COMMERCIAL_INTELLIGENCE_TRANSITION_V1_EVIDENCE.json` →  
`"evidence_loaded_from": "demo_rich_fixture_v1"`.

**E. One completed purchase mapping shape** — `ProductPurchaseMapping` (`models.py`):  
`stable_identity_key`, `product_id`, **`name`**, `order_id`, `session_id`, `purchase_confidence`, `purchase_source`, `purchased_at`, `dedup_hash`.  
Filled only from session `CartLineSnapshot` rows at Purchase Truth time (`product_purchase_mapping_v1._present_products_for_session`).

**F. One Home commercial finding (fixture path)** — CQ-P01 in `HOME_COMMERCIAL_INTELLIGENCE_TRANSITION_V1_EVIDENCE.json`:  
answer uses «منتج X» + 34/22/2 — not a live store product.

---

## 2. Source-of-truth map

| Concern | Authoritative store | Notes |
|---------|---------------------|-------|
| Cart existence / value / status / timing | `abandoned_carts` (+ lifecycle projections) | Carts UI uses this |
| Opaque cart JSON (legacy lines) | `abandoned_carts.raw_payload` | May hold `cart` / `items` / `lines`; 65k cap |
| Immutable line identity at capture | **`cart_line_snapshots`** | Insert-only; field **`name`** (not `product_name`) |
| Current catalog identity | **`product_catalog_entries`** | Mutable; `stable_identity_key` tiers A–E |
| Product ↔ hesitation | `product_hesitation_mappings` | Needs snapshots at reason time |
| Product ↔ purchase | `product_purchase_mappings` | Needs snapshots at purchase time |
| Purchase occurred (boolean) | `purchase_truth_records` | **No line items** |
| Merchant cart row display | Dashboard snapshot / live row builders | **No product name fields in slim allowlist** |
| Commercial product findings | EvidenceBundle.products → Findings Engine | **Fixture vs broken DB loader** |
| Home commercial copy | Findings → `home_commercial_intelligence_v1` | Must not invent identity |

**Identity precedence (canonical):**  
`product_id+variant_id` (A) → `product_id+sku` (B) → `product_id` (C) → `sku` (D) → normalized name hash (E) — `product_catalog_normalizer_v1.resolve_canonical_identity`.

---

## 3. Answers to specific questions (with evidence)

### 1. Does the canonical cart model contain the real product name?

**Partially / conditionally.**

- **Canonical durable line model:** yes — `CartLineSnapshot.name` (nullable String(200)).
- **Canonical cart aggregate (`AbandonedCart`):** no dedicated product-name column; only optional JSON in `raw_payload`.
- **Simulator carts:** often store **product_key** as `items[].name`, not catalog display name.

### 2. Are cart line items persisted with immutable product name snapshots?

**Yes, when ingest succeeds.**  
`CartLineSnapshot` is insert-only; name is part of `content_hash`; never updated in place (`product_cart_snapshots_v1.py`, model docstring).  
**Gate:** only `payload.lines[]` from `cart_state_sync` / `cart_abandoned`. Legacy `items`/`cart` alone do **not** create snapshots.

### 3. Can current carts be reconstructed with real product names?

| Path | Reconstructable? |
|------|------------------|
| Carts with foundation snapshots | **Yes** — `lines_for_cart` / `lines_for_session` |
| Carts with rich `raw_payload` items/lines (demo widget) | **Often yes** via `line_items_from_abandoned_cart` / recovery parsers |
| Zid lite counts-only carts | **No** — only value/count |
| Simulator carts | **Partial** — key/`demo_*` id, not display name unless joined to catalog |
| Merchant Carts UI today | **No** — not projected/rendered |

### 4. Are product names available in the demo simulation data?

**Yes in the catalog / manifest** (real Arabic/English display names).  
**Degraded in simulator cart writes** (`name = product_key`).  
**Not** «منتج X» — that label is exclusive to Business Findings demo fixture.

### 5. Why did Home produce “Product X”?

Because Commercial Intelligence consumed a Business Finding built from **`demo_rich_fixture_v1`**, which hard-codes `"name_ar": "منتج X"` and metrics 34/22/2.

Proven chain:

1. `build_demo_rich_evidence_bundle_v1()` → `prod_x` / «منتج X»  
   (`services/business_findings_evidence_v1.py` L117–124)
2. `evaluate_high_interest_low_purchase_v1` interpolates `name` into merchant_summary  
   (`services/business_findings_families_v1.py` L263–278)
3. `finding_to_commercial_insight_v1` → Home Understanding  
   (`services/home_commercial_intelligence_v1.py`)
4. Validation evidence records `evidence_loaded_from: demo_rich_fixture_v1`  
   (`HOME_COMMERCIAL_INTELLIGENCE_TRANSITION_V1_EVIDENCE.json`)

Engine default: if neither `evidence` nor `load_db`, **`run_business_findings_engine_v1` falls back to the same rich fixture** (`business_findings_engine_v1.py` L321–322).

### 6. Is “Product X” a hard-coded placeholder, fallback, fixture, or symptom?

**Hard-coded fixture placeholder** (`demo_rich_fixture_v1`), also used as **engine default when not loading DB**.  
It is **not** a runtime “unknown product” fallback from missing snapshots.  
It **is** an authenticity violation if shown as real store knowledge.

Related placeholders in same fixture: «منتج B», «منتج C», «منتج مقارن 1/2».

### 7. Why does the Carts page display only value and not product identity?

**UI + projection omission (not a missing CSS quirk):**

1. Row renderer shows value, reason chip, status, next action, last seen, phone — **no product field**  
   (`static/merchant_dashboard_lazy.js` `cartRowTableDisplay` ~L3531–3587).
2. Slim snapshot allowlist has `merchant_cart_value`, lifecycle, timing — **no** `product_name` / lines  
   (`services/dashboard_snapshot_normal_carts_slim_v1.py` `NORMAL_CARTS_SNAPSHOT_ROW_ALLOWLIST`).
3. `cart_detail_projection_v1` projects explanation/actions/lifecycle — **not** line identity.
4. Separately, many production Zid carts may lack identity in payload (prior audit).

So even a cart with perfect snapshots would not show names on Carts today.

### 8. Does Purchase Mapping preserve Product ↔ Purchase identity?

**Yes by design**, when session snapshots exist:

- Maps `stable_identity_key` + optional `product_id` + **`name`** snapshot at purchase time.
- Insert-only with `dedup_hash`.
- **Cannot invent** products: empty snapshots → `skipped_empty` — purchase remains cart-level only in Purchase Truth.

### 9. Can the same product be recognized across carts, sessions, purchases?

**Yes when identity tiers resolve consistently** (prefer product_id tiers A–C).  
**Fragile** on name-only (tier E) or when simulator uses keys vs catalog ids inconsistently.  
Cross-cart recognition for findings is intended via aggregation on `product_id`/`name` — but live aggregator is currently broken (Q10/Q11).

### 10. Are provider-specific product IDs normalized correctly?

**Normalization rules are correct** when ids reach the normalizer (`catalog_input_from_line` + tier keys).  
**Capture is the weak link:** Zid bridge historically emits counts/totals without product ids (`docs/cartflow_widget_product_identity_audit_v1.md`). Widget capture can read Zid `products`/`items` **if present on globals**, but production reliability remains path-dependent.

### 11. Are historical rows missing product identity?

**Yes, expected for:**

- Pre–Cart Line Snapshots foundation carts (before ~2026-06-07 / migration `h8i9j0k1l2m3`).
- Zid lite events that never sent `lines[]`.
- Simulator rows that wrote `items` without going through `lines[]` snapshot ingest.
- Any cart whose `raw_payload` is totals-only.

These cannot be fully reconstructed from foundation tables alone.

### 12. Can unresolved product identity contaminate Commercial Knowledge?

**Yes — and fixture identity already did.**

Contamination vectors:

1. **Fixture names as merchant truth** (proven on Home CI validation).
2. **Broken DB loader** → empty products → missing/wrong product findings; default engine path may substitute fixture.
3. **Simulator keys** (`hp_air`) treated as names if ever aggregated from `raw_payload.items`.
4. **Tier E name-hash** collisions if display names vary slightly.
5. Findings copy that presents unresolved identity as a named product (forbidden by authenticity rule).

---

## 4. Root-cause classification

Multi-cause. Ordered by merchant impact:

### Primary (Home “Product X”)

**Class 7 — Fixture / placeholder product labels**  
Hard-coded in `demo_rich_fixture_v1` and admitted into Home Commercial Intelligence / review surfaces.

### Secondary (live Commercial Knowledge cannot use real names)

**Class 2 — Identity in tables, missing from projections (broken consume)**  

`_load_product_interest_v1` queries:

```python
CartLineSnapshot.product_name   # DOES NOT EXIST — model field is `name`
CartLineSnapshot.created_at     # DOES NOT EXIST — model field is `captured_at`
```

Runtime check (2026-07-19): `hasattr(CartLineSnapshot, "product_name") is False`.  
Exception path returns `{}` — silent degrade (`business_findings_evidence_v1.py` L443–445).

### Tertiary (Carts page)

**Class 1 — Identity not consumed by UI** (always), compounded by  
**Class 4 — Snapshots often absent** on Zid/history (capture gap), and  
**Class 3 — Simulator normalization loss** (`product_key` written as name; no `lines[]`).

### Not the sole cause

- Not “Home only forgot to bind a field while DB had Product X.”
- Not Purchase Truth inventing product names.
- Not Carts CSS hiding names that the API already sends.

---

## 5. Affected surfaces list

| Surface | How identity fails | Severity |
|---------|-------------------|----------|
| **Home — Business Understanding / Opportunity** (Commercial Intelligence) | Fixture «منتج X» / fake metrics; or empty DB products | Critical — authenticity |
| **Business Findings Review Lab** | Fixture by design for Product review | High if mistaken for production truth |
| **Business Reasoning Review Lab / demos** | Consumes fixture findings with Product X | High for review confusion |
| **Carts page queue / table / detail** | No product name in projection or render | High merchant visibility |
| **Product Data Health / Identity Coverage APIs** | Diagnostic only; do not fix merchant display | Medium (ops) |
| **Knowledge Layer product bridge** | Coverage metrics only; no product display names to Home | Medium |
| **WhatsApp recovery copy** | Separate parsers (`recovery_product_context`); may still get names from `raw_payload` when present | Variable |
| **Commercial Knowledge Expansion V1** | **Blocked** — must not expand until identity authenticity fixed | N/A (deferred) |

---

## 6. Historical-data impact assessment

| Cohort | Likely identity state | Reconstruct display name? |
|--------|----------------------|---------------------------|
| Demo widget carts with `lines[]` / rich `cart` array | Snapshots +/or raw lines | **Yes** |
| Post-foundation Zid carts with successful identity capture | Snapshots | **Yes** if capture worked |
| Zid lite counts-only | No snapshots, no lines | **No** |
| Pre-foundation historical abandoned carts | raw_payload only / totals | **Maybe** from JSON; else **No** |
| Store Reality Simulator carts | `items[].name = product_key` | **Catalog join** possible; snapshot path usually empty |
| Purchase Truth without snapshots | Purchase yes; mapping empty | **No product↔purchase name** |

**Backfill:** Only honest where `raw_payload` or catalog can supply names. Do not invent. Historical gaps must remain **unresolved** in merchant language.

---

## 7. Fix recommendation (ordered by dependency)

**Do not implement in this task.** Recommended sequence for Product Approval:

1. **Authenticity gate (P0)**  
   - Forbid merchant Home from admitting findings whose `evidence.loaded_from` is `demo_rich_fixture_v1` / engine default fixture.  
   - Review Labs may keep fixtures only under explicit `source=fixture` / `/dev` paths.  
   - Replace «منتج X» in any merchant-eligible path with real `name` or honest “identity unavailable.”

2. **Repair DB product evidence loader (P0)**  
   - `_load_product_interest_v1`: use `CartLineSnapshot.name` + `captured_at` (and prefer `stable_identity_key` / catalog name when joining).  
   - Add regression test that fails if wrong attribute names are queried.  
   - Never fall back to demo fixture for `load_db=True` store composition.

3. **Capture completeness (P1)**  
   - Ensure production widget paths attach non-empty `lines[]` for Zid object carts (prior audit recommendations).  
   - Simulator: write catalog **display name** into items/lines and emit `lines[]` so snapshots + UI share one identity.

4. **Carts projection + UI (P1)**  
   - Project snapshot/catalog names into cart row/detail (or honest empty state).  
   - Extend slim allowlist only with governed fields.  
   - No placeholder product labels.

5. **Purchase / cross-cart recognition (P2)**  
   - Verify mapping coverage after capture+loader fixes.  
   - Prefer product_id tiers; surface unresolved when tier E only.

6. **Commercial Knowledge Expansion V1**  
   - Only after P0–P1 authenticity + real-name proof on one live cart + one purchase + one Home finding.

---

## 8. Regression test plan

| ID | Test | Pass criteria |
|----|------|---------------|
| T1 | `CartLineSnapshot` column contract | Findings evidence loader references `name` + `captured_at` only |
| T2 | Fixture isolation | `load_db=True` never returns `loaded_from` containing `demo_rich_fixture` |
| T3 | Home authenticity | Home package with fixture findings rejected / not admitted to merchant Understanding |
| T4 | Snapshot persist | `lines[]` with real name → row with identical `name` |
| T5 | No lines | totals-only payload → zero snapshots; merchant copy must not invent a product |
| T6 | Purchase mapping | Snapshot name propagates to `ProductPurchaseMapping.name` |
| T7 | Simulator | Cart raw/lines use catalog display name (not only `product_key`) |
| T8 | Carts projection | When snapshots exist, row/detail includes name or explicit unavailable |
| T9 | Cross-cart identity | Same `product_id` aggregates across two sessions |
| T10 | Forbidden strings | Merchant Home package must not contain `منتج X` / `Product X` / `Product A` unless `/dev` fixture mode |

---

## 9. Production verification plan

| Step | Action | Evidence to capture |
|------|--------|---------------------|
| V1 | `GET /api/product-data/health` for a live store | `identity_coverage`, `foundation_health`, snapshot rates |
| V2 | SQL sample | One `abandoned_carts` row + matching `cart_line_snapshots` (or prove absence) |
| V3 | SQL sample | One `product_purchase_mappings` row with non-null `name` for a confirmed purchase |
| V4 | Home composition JSON | `home_commercial_intelligence_v1.evidence_loaded_from` must be `db_v1:*` — not fixture; product finding names must match catalog/snapshots |
| V5 | Carts API/snapshot row | Confirm whether product name field present after fix (today: absent) |
| V6 | Zid storefront console | `[PRODUCT IDENTITY] lines=N source=…` on add-to-cart / sync |
| V7 | Negative | Store with no lines → Home must say identity/evidence unavailable — never «منتج X» |

**Local note (this investigation):** No production DB credentials were available in the workspace for live SQL. Schema/model/runtime attribute checks and fixture/evidence JSON were used as proof. Production V1–V7 remain required before closing the incident.

---

## 10. Stage-by-stage proof appendix

### Provider → widget

- Capture: `static/cartflow_widget_runtime/cartflow_product_identity_capture.js`  
- Attach: `cart_abandon_tracking.js`, `cartflow_widget.js` call `cartflowAttachProductLines`  
- Loader includes capture script: `cartflow_widget_loader.js`  
- Prior Zid gap audit: `docs/cartflow_widget_product_identity_audit_v1.md`

### Persist

- Hook: `services/product_data/product_data_line_snapshots_hook_v1.py`  
- Persist: `services/product_data/product_cart_snapshots_v1.py` (`_extract_lines` → **`lines` only**)  
- Schema: Alembic `h8i9j0k1l2m3` column **`name`**, **`captured_at`**

### Normalize / catalog / purchase

- `product_catalog_normalizer_v1.py`, `product_catalog_v1.py`  
- `product_purchase_mapping_v1.py`, `product_purchase_hook_v1.py` (from Purchase Truth)

### Findings → Home

- Evidence: `business_findings_evidence_v1.py` (fixture + broken DB loader)  
- Families: `business_findings_families_v1.py`  
- Engine fallback to fixture: `business_findings_engine_v1.py` L321–322  
- Home wire: `merchant_home_composition_v1.py` L1568–1598 + `home_commercial_intelligence_v1.py`

### Carts

- Render: `merchant_dashboard_lazy.js` `cartRowTableDisplay`  
- Slim fields: `dashboard_snapshot_normal_carts_slim_v1.py`  
- Detail: `cart_detail_projection_v1.py` (no product lines)

---

## 11. Distinction checklist (mission taxonomy)

| # | Hypothesis | Verdict |
|---|------------|---------|
| 1 | Exists; missing from UI only | **True for Carts** (when snapshots/raw exist) |
| 2 | Exists in tables; missing from projections | **True** — findings loader + Carts slim/detail |
| 3 | Lost in provider normalization | **True for simulator** (key as name); **partial for Zid** (often never emitted) |
| 4 | Not persisted in cart line snapshots | **True when `lines[]` absent**; false when capture works |
| 5 | Disconnected from purchase mapping | **Conditional** — mapping preserves name iff snapshots exist |
| 6 | Exists but Commercial Knowledge does not consume | **True** — broken loader + fixture substitution |
| 7 | Simulator/fixture placeholder labels | **True** — «منتج X» fixture; sim uses product_key |
| 8 | Historical rows predate foundations | **True** for pre-snapshot / totals-only cohorts |

---

## 12. STOP / next gate

- Investigation complete.  
- **No code fixes applied.**  
- **Do not** continue Commercial Knowledge Expansion V1.  
- **Do not** patch «Product X» with another fake label.  
- **Await Product Review** before implementation of §7.

**Primary Product decision needed:**  
Treat fixture-backed product names on merchant Home as a **P0 authenticity defect**, independent of Carts UI work.
