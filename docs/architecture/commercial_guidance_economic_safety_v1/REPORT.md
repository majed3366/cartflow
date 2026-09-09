# Commercial Guidance Economic Safety Closure V1 — Report

**Date (UTC):** 2026-09-09
**Status:** SAFETY CLOSURE — merchant-facing wording only
**Base SHA:** `751c35a3d844b1f515b9da27ea89f3277a05dbc8` (live API at start)
**Branch:** `candidate/commercial-guidance-economic-safety-v1`

---

## Root finding

Workspace `decision_sentence_ar_v1` emitted, for any shipping-flavoured card that
was not in the *needs more evidence* state:

> `عدّل تكلفة الشحن للطلبات الصغيرة.`

That is a **Level 3-shaped** instruction: it tells the merchant to change the
shipping price for a cart-size cohort. CartFlow holds **no** authoritative
shipping cost, shipping subsidy, COGS, gross margin, or margin floor, and holds
no cart-value threshold truth. The sentence therefore exceeded the evidence
contract.

It was **not** OGL. `commercial_guidance_knowledge_registry_v1` already forbids
`reduce_shipping_cost`, `offer_shipping_discount`, `lower_the_price`, and
`force_discount_campaign`. The overshoot lived in the presentation/composition
layer, which composes its own fallback sentences when a card carries no explicit
merchant action.

**Root cause:** merchant-facing composition layers own hardcoded fallback action
strings that were never gated by an economic-input precondition. Diagnosis was
correct; the *action* clause skipped from evidence straight to an economic
parameter.

---

## Safety law applied

Until economic truth exists, guidance stays at **Level 2**:

- clarify shipping cost
- clarify delivery duration
- distinguish cost vs delivery-time hesitation
- clarify what the customer receives for the price
- collect evidence / wait

Never: lower shipping cost, subsidize shipping, free shipping, free-shipping
threshold, direct discount, monetary threshold, economically parameterized
bundle.

---

## Changes (merchant-facing wording only)

| File | Before | After |
|------|--------|-------|
| `services/decision_workspace_v2/narrative_v1.py` | `عدّل تكلفة الشحن للطلبات الصغيرة.` | `حدّد هل التردد بسبب تكلفة الشحن أم مدة التوصيل، ثم وضّح المعلومة للعملاء.` |
| `services/decision_composition_engine_v1/merchant_publication_v1.py` | `قرّر إن كنت ستعدّل سياسة الشحن لـ {X} أم تبقيها.` | `وضّح تكلفة الشحن ومدة التوصيل لـ {X} قبل أي تغيير في السعر أو العرض.` |
| `services/decision_composition_engine_v1/store_executive_understanding_v1.py` | `راجع تكلفة أو تجربة الشحن.` | `راجع وضوح تكلفة الشحن ومدة التوصيل للعملاء.` |
| `services/decision_composition_engine_v1/store_executive_understanding_v1.py` | `راجع استراتيجية التسعير أو الخصم.` | `راجع وضوح ما يحصل عليه العميل مقابل السعر.` |
| `services/merchant_dashboard_reference_ui.py` | `… يسببان N٪ من التردد — راجع إعدادات الشحن وعروض الخصم` | `… يمثلان N٪ من أسباب التردد المسجّلة — وضّح تكلفة الشحن ومدة التوصيل وما يحصل عليه العميل مقابل السعر` |
| `services/merchant_value_composition_v1.py` | `قد تستحق سياسة الشحن المراجعة إذا تكرر النمط.` | `قد يستحق وضوح تكلفة الشحن ومدة التوصيل المراجعة إذا تكرر النمط.` |
| `services/finding_decision_engine_v1.py` | `عدّل رسالة العرض/التوصيل/السعر …` | `عدّل وضوح رسالة الشحن/التوصيل/قيمة المنتج … دون تغيير الأسعار أو العروض.` |
| `services/business_reasoning_rules_v1.py` | `حسّن عرض تكلفة الشحن قبل زيادة حملات التذكير.` | `حسّن وضوح تكلفة الشحن ومدة التوصيل قبل زيادة حملات التذكير.` |
| `scripts/_orv_ui_polish_prod_capture_v1.py`, `scripts/observation_reality_ui_polish_verify_v1.py` (capture fixtures, not runtime) | `اختبر شحنًا مجانيًا أو خفّض تكلفة الشحن.` | `وضّح تكلفة الشحن ومدة التوصيل قبل أي تغيير في السعر أو العرض.` |

The dashboard insight also drops the causal verb `يسببان` ("cause") in favour of
`يمثلان … من أسباب التردد المسجّلة` ("represent … of recorded hesitation
reasons"). Share, not causation.

**Diagnosis text was not changed.** Only the action clause.

---

## Regression classification

Swept for: reduce shipping cost · offer shipping discount · free shipping ·
lower price · discount · specific threshold.

**UNSAFE_WITHOUT_ECONOMICS → 0 remaining.** All nine occurrences above were
corrected. Verified: zero hits across
`decision_workspace_v2`, `decision_composition_engine_v1`,
`home_executive_summary_v1`, `merchant_value_composition_v1`,
`merchant_dashboard_reference_ui`, `finding_decision_engine_v1`,
`business_reasoning_rules_v1`.

**SAFE (left unchanged):**

- `finding_decision_engine_v1` `عدّل وضوح السعر/الشحن/الثقة` — clarity, not price.
- `business_reasoning_rules_v1` `حسّن رسائل ووضوح وقت التوصيل قبل الاعتماد على حملات الخصم.` — explicitly *anti*-discount.
- `home_executive_summary_v1/diagnosis_language_v1` — insufficient-evidence paths already return `واصل جمع الأدلة.`
- `narrative_v1` wait paths — `لا تغيّر سياسة الشحن حتى تتضح الأدلة.` / `لا تُجرِ تغييراً حتى تتضح الأدلة.`
- `recovery_offer_decision.py`, `recovery_product_suggestions.py` — margin-protective guardrails that *discourage* discounting.

**SAFE — negated guardrails (the largest category).** A forbidden phrase is safe
when the merchant is told *not* to do it. `commercial_action_language_v1` and
`operational_guidance_v1` already emit, on the live price path:

> `dont_ar`: `لا تطلق خصماً عاماً ولا تخفّض السعر لأن السعر تكرر كسبب تردد.`
> `why_ar`: `السعر هو أعلى سبب تردد الآن: 12 من 20 (60٪). هذا لا يثبت أن الخصم يرفع الإيراد.`

A naive substring sweep counted 26 such occurrences as violations. They are the
opposite — they are the price-safety law already working. The gate is therefore
**negation-aware**: only an *unnegated* use counts, and
`test_negation_is_required_to_keep_a_forbidden_phrase` proves the check still
catches a real instruction. Both modules are now inside the gate's coverage.

**NON-MERCHANT_INTERNAL (out of scope, unchanged):**

- OGL `forbidden_actions` identifiers (`reduce_shipping_cost`, …) — policy identifiers, never painted.
- VIP / general settings offer configuration (`vip_offer_type=free_shipping`, `عروض الخصم (كود)`) — the merchant's *own* configured offer, not CartFlow advice.
- Widget and recovery message copy — customer-facing, merchant-configured.
- `cart_workspace` `راجع طلب الخصم` — a customer *asked* for a discount; operational response, not CartFlow economic advice. Carts is outside this boundary.
- `docs/business_findings/BUSINESS_REASONING_DEMO_REPORT_V1.md` — dated historical report, not runtime.

**Merchant-facing `البيع المتقاطع`: 0** (verified across `services`, `static`,
`templates`). Reserved future merchant term is **`منتجات مكملة`**. Internal
identifiers may keep `cross_sell`. No cross-sell UI introduced.

---

## Production review scenarios (local proof)

| Family | Output |
|--------|--------|
| `shipping_friction` R17 (12 of 20 = **60.0%**) | diagnosis share preserved; action `حدّد هل التردد بسبب تكلفة الشحن أم مدة التوصيل، ثم وضّح المعلومة للعملاء.` |
| `shipping_friction` situation action | `وضّح تكلفة الشحن ومدة التوصيل لـ R17 قبل أي تغيير في السعر أو العرض.` |
| `price_hesitation` | `راجع وضوح ما يحصل عليه العميل مقابل السعر.` |
| `product_confidence` | `راجع عرض صفحة المنتج.` (page presentation; no invented reviews/certificates/guarantees) |
| `wait_insufficient_evidence` (shipping) | `لا تغيّر سياسة الشحن حتى تتضح الأدلة.` |
| `wait_insufficient_evidence` (generic) | `لا تُجرِ تغييراً حتى تتضح الأدلة.` |

Forbidden-phrase hits across all emitted scenario text: **0**.

Shipping safe level: **2**. No economic parameterization, no monetary threshold.

---

## No-action contract

Preserved, not redefined:

- insufficient evidence → `لا تُجرِ تغييراً حتى تتضح الأدلة.` / `واصل جمع الأدلة.`
- shipping insufficient evidence → `لا تغيّر سياسة الشحن حتى تتضح الأدلة.`
- blocked → `أرجئ التنفيذ حتى يُستكمل المتطلب الناقص.`
- OGL `KT_EVIDENCE_GAP` → `collect_additional_evidence`; `KT_EVIDENCE_CONFLICT` → `delay_operational_decision`

`ECONOMIC_INPUTS_REQUIRED` remains a **design-only** state from the Commercial
Intervention Intelligence audit. No state machine was introduced here.

---

## Tests

New: `tests/test_commercial_guidance_economic_safety_v1.py` — 11 tests.

Covers: no economically parameterized guidance; no invented product-confidence
proof; no monetary threshold; no merchant-facing `البيع المتقاطع`; shipping
action stays disclosure-level (Workspace + publication); price title clarifies
value instead of discount; wait state prefers no action; reason insight is share
not cause; OGL still forbids economic actions.

Updated: `tests/test_decision_workspace_v2_budget.py` — the shipping assertion
now requires cost-vs-duration disclosure and explicitly forbids the old string.

**Impacted-suite parity vs baseline `751c35a3`** (38 suites touching the modified
modules):

| Tree | Result |
|------|--------|
| Baseline (`cartflow-product-exposure-server-v1` @ `751c35a3`) | **33 failed, 295 passed** |
| Candidate | **33 failed, 305 passed** |

Failure sets are **identical test IDs**. All 33 are pre-existing at the base SHA
(Home/Figma/runtime-identity/visual-parity suites that already fail in this
tree). **New failures introduced: 0.** The +10 delta is exactly the new safety
suite.

`tests/test_demo_lab_scenario1_v1.py` fails collection at the base SHA
(`services.customer_movement_snapshot_v1` missing) — pre-existing, unrelated.

---

## Live production proof

API deployed by exact SHA (`serviceInstanceDeployV2`), autodeploy OFF, no env
mutation, Scheduler untouched (`f91e799d` / `2b1e5665`, 2026-08-27).

| Check | Result |
|-------|--------|
| Pre-deploy live API SHA (re-observed) | `751c35a3…` / deployment `36be0d5c` SUCCESS |
| `/ping` · `/health` · `/health?db=1` | 200 · 200 · 200 (`database: ok`) |
| QueuePool `timeout_count` | 0 |
| `X-CartFlow-Git-Sha` = `git_sha` = candidate | YES |

Lab tenant `cf_live_reality_lab`, real `/dashboard` 200.

| Family | Scenario | apply / verify | Live merchant action |
|--------|----------|----------------|----------------------|
| `shipping_friction` | `R17_shipping_hesitation` | ok / ok | `وضّح تكلفة الشحن ومدة التوصيل لـ … قبل أي تغيير في السعر أو العرض.` |
| `price_hesitation` | `R21_price_hesitation` | ok / ok | `وضّح قيمة العرض مقابل السعر الحالي قبل أي خصم.` + `dont_ar: لا تطلق خصماً عاماً ولا تخفّض السعر…` |
| `product_confidence` | `R20_product_confidence` | ok / ok | no invented reviews / certificates / guarantees |
| `wait_insufficient_evidence` | `R15_zero_visits` | ok / ok | no economic instruction emitted |

**R17 diagnosis unchanged:** `merchant_reason_counts_week` = shipping **12**,
price 5, thinking 3 → 20 recorded reasons, shipping share **12/20 = 60%**.

Dashboard insight now reads
`السعر والشحن يمثلان 85٪ من أسباب التردد المسجّلة — وضّح تكلفة الشحن ومدة التوصيل وما يحصل عليه العميل مقابل السعر`
(share of recorded reasons, not causation, no discount).

**Unnegated forbidden instructions across `/dashboard` HTML + 4 scenario
summaries + 4 workspace projections: 0.** Monetary thresholds: 0.

Shipping live safe level: **2**.

---

## Boundary

| Item | Changed |
|------|---------|
| COL diagnosis ownership | NO |
| Mission Catalog | NO |
| Portfolio lifecycle | NO |
| CDC lifecycle | NO |
| Products | NO |
| Carts | NO |
| Product Exposure | NO |
| Scheduler | NO |
| DB schema | NO |
| New intervention engine | NO |
| AI | 0 |
| External API | 0 |

**NEW TECHNICAL DEBT: NONE.** No temporary compatibility code, no feature flag,
no dual-path wording, no shim.
