# Intervention Contract V1

Design only. No implementation in this task.

## 1. Recommendation levels

A level describes how much economic authority a recommendation consumes, not how
confident CartFlow feels. Levels never skip: a family may only emit level `N` if
it can emit every level below `N` and if every input required by `N` is present.

| Level | Name | Merchant example | Requires |
| --- | --- | --- | --- |
| 0 | FACT | `الشحن يمثل 12 من 20 سبب تردد مسجّل.` | Evidence only |
| 1 | INTERVENTION CANDIDATE | `قد يكون من المناسب اختبار تدخل مرتبط بالشحن.` | Dominant-reason truth |
| 2 | BOUNDED SAFE TEST | `وضّح تكلفة الشحن ومدة التوصيل قبل تغيير السعر أو العرض.` | Level 1 + action changes no merchant economics |
| 3 | ECONOMICALLY PARAMETERIZED | `اختبر الشحن المجاني فوق <THRESHOLD>` | Full economic input set + computable margin floor |
| 4 | PRODUCT-SPECIFIC | `اقترح منتجًا مكملاً محددًا مع المنتج الحالي.` | Level 3 inputs + product-pair + inventory + compatibility truth |

The Level 2 boundary is the load-bearing one. An action is Level 2 only if it
changes **what the customer is told**, never **what the merchant charges, pays,
or gives away**. Clarifying a shipping cost is Level 2; lowering it is Level 3.

### Level ceiling resolution

The ceiling is computed per family, per store, at compose time:

```
ceiling(family, store) = min(
    family_max_level,                       # static registry, see §5
    max_level_supported_by_available_inputs # Economic Input Manifest
)
```

Candidates above the ceiling are not discarded. They are retained as
`blocked_candidates[]` so the merchant can be told what is blocked and why. This
is what makes UI section 4 (`لماذا لا نقترح تدخلاً أقوى؟`) truthful rather than
decorative.

## 2. Intervention object

Every intervention candidate exposes exactly these fields.

| Field | Type | Source of truth |
| --- | --- | --- |
| `intervention_id` | str | Derived: `civ1:{family}:{level}:{action_code}` — stable, no store PII |
| `family` | str | COL `family` (unchanged vocabulary) |
| `recommendation_level` | int 0–4 | CAL extension registry |
| `what_we_see_ar` | str | CAL `situation_ar` + `evidence_ar` (exists) |
| `what_we_suggest_ar` | str | CAL `action_ar` (exists) |
| `why_this_is_safe_ar` | str | **New** — states which economic lever is untouched |
| `required_economic_inputs` | list[str] | Economic Input Manifest for this level |
| `missing_inputs` | list[str] | Manifest fields with no registered authority |
| `dont_do_ar` | str | CAL `dont_ar` (exists) |
| `primary_metric` | str | Measurement contract |
| `guardrail_metric` | str | **New** — measurement contract |
| `measurement_window` | int days | CDC `resolve_measurement_window_days()` (exists, 7) |
| `recheck_condition` | str | CAL `recheck_ar` + CDC `recheck_condition_frozen` (exists) |
| `success_condition` | str | Measurement contract |
| `failure_condition` | str | Measurement contract |
| `mind_change_condition` | str | **New** — what would invalidate this intervention |
| `eligibility_state` | str | Derived projection, see §3 |
| `conflict_group` | str | **New** — declared, enforced by Portfolio |
| `evidence_refs` | list[str] | COL `evidence_refs` (exists) |

Three merchant-facing fields are genuinely new: `why_this_is_safe_ar`,
`guardrail_metric`, `mind_change_condition`. Everything else is either already
produced by CAL/COL/CDC or is derived governance metadata.

`why_this_is_safe_ar` must name the untouched lever explicitly. A sentence like
`هذا التدخل آمن` is not acceptable; `هذا التدخل لا يغيّر سعرك ولا تكلفة الشحن` is.

## 3. Eligibility states

`eligibility_state` is a **derived projection, not a stored authority**. It is
computed from owners that already exist, so no layer gains a second opinion about
its own domain.

| State | Derived from |
| --- | --- |
| `ELIGIBLE` | COL `PRODUCTION_TRUTH_READY` + Portfolio `may_execute` + no missing inputs at chosen level |
| `INSUFFICIENT_EVIDENCE` | COL `truth_class == INSUFFICIENT`, or opportunity absent |
| `ECONOMIC_INPUTS_REQUIRED` | Chosen level ≥ 3 and `missing_inputs` non-empty |
| `CONFLICTING_SIGNALS` | Portfolio `MUTUALLY_EXCLUSIVE` or `MEASUREMENT_CONTAMINATION` |
| `ALREADY_UNDER_MEASUREMENT` | CDC phase `ACTION_CHOSEN` or `UNDER_MEASUREMENT` for this opportunity |
| `INTERVENTION_NOT_JUSTIFIED` | Catalog role `suppressed`, or Portfolio `DUPLICATE_INTENT` / `CAPACITY_ONLY` |
| `WAIT_AND_RECHECK` | COL `PRODUCTION_PARTIAL`, or any unknown/missing input to this projection |

Resolution order is fixed and first-match-wins:

```
1. INSUFFICIENT_EVIDENCE
2. ALREADY_UNDER_MEASUREMENT
3. CONFLICTING_SIGNALS
4. INTERVENTION_NOT_JUSTIFIED
5. ECONOMIC_INPUTS_REQUIRED
6. WAIT_AND_RECHECK
7. ELIGIBLE
```

Evidence insufficiency dominates because telling a merchant "your economics are
missing" is misleading when the underlying problem is not even established.

CDC phase `RECHECK_DUE` does not block eligibility; it is the recheck path and is
already boosted by Mission Catalog (`BOOST_RECHECK_DUE`).

### Fail-safe rule

No eligible intervention → no recommendation escalation. The absence of an
eligible intervention must never cause CartFlow to promote a lower-evidence
candidate, widen a window, relax a threshold, or fall back to generic advice.
Unknown state resolves to `WAIT_AND_RECHECK`, never to `ELIGIBLE`.

## 4. Terminology

Merchant-facing complementary products are `منتجات مكملة`.

`البيع المتقاطع` is not merchant-facing vocabulary. Internal identifiers may keep
`cross_sell`. Current merchant dashboard surfaces contain zero occurrences; the
existing `cross_sell` strings live in `services/revenue_reality_validation_v1`
and `services/commercial_decision_library_v1_1`, which are simulation/lab
lineages that COL already forbids from rendering on `/dashboard` via
`FORBIDDEN_SIM_MARKERS`. Note for implementation: `mission_composer_v1.py`
carries the Arabic string `فرصة حزمة / بيع متقاطع`; if any lab surface ever
becomes merchant-visible, that string must become `منتجات مكملة` first.

## 5. Family ceilings today

| Family | `family_max_level` | Ceiling today | Blocked above |
| --- | --- | --- | --- |
| `shipping_friction` | 3 | **2** | `ECONOMIC_INPUTS_REQUIRED` |
| `price_hesitation` | 3 | **2** | `ECONOMIC_INPUTS_REQUIRED` |
| `product_confidence` | 2 | **2** | Level 3 not defined for this family |
| complementary products (`cross_sell`, internal) | 4 | **1** | `ECONOMIC_INPUTS_REQUIRED` |
| `wait_insufficient_evidence` | 0 | **0** | `INSUFFICIENT_EVIDENCE` |

### Shipping family

Allowed now (Level 2):

- clarify shipping cost
- clarify delivery duration
- distinguish cost hesitation from duration hesitation

Blocked now: free shipping, shipping subsidy, shipping threshold, any monetary
shipping recommendation. Reason: `shipping_cost`, `shipping_subsidy`, and margin
truth have no registered authority.

Blocked-state contract: the merchant is told the intervention class exists, that
it is blocked, and which inputs would unblock it. The merchant is never told a
number, a direction, or a threshold.

### Price / value family

Allowed now (Level 2): `وضّح قيمة العرض مقابل السعر الحالي قبل أي خصم.`

Blocked now: direct discount, price reduction, bundle price, monetary threshold.

CartFlow knows selling price (`product_catalog_entries.price`) but not cost, so
it can state what a customer pays and never what the merchant keeps. Price
without cost cannot bound a discount.

### Product confidence family

Allowed now (Level 2), and only from authoritative merchant evidence: specs,
warranty, quality evidence, product explanation.

Never invented: reviews, certificates, guarantees, social proof. This is already
enforced in CAL copy (`بلا تقييمات أو شهادات غير موجودة`) and is retained as a
contract obligation, not a copy preference.

### Complementary products

Merchant-facing term: `منتجات مكملة`. Current safe level: **1 only**.

Allowed conceptually: `قد توجد فرصة لرفع قيمة السلة بمنتج مكمل.`

Product B must not be named. A named complementary-product recommendation is
Level 4 and requires product-pair evidence, inventory quantity, product
economics, shipping impact, and compatibility evidence. Co-occurrence counts are
derivable today from `cart_line_snapshots`, but co-occurrence alone is
correlation, and inventory and product economics have no authority at all, so
Level 4 stays closed.
