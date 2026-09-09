# Measurement and Causality Contract V1

Design only.

## 1. Obligation

Every eligible Level 2+ intervention must define all eight of the following
before it is offered to the merchant. An intervention that cannot state what
would prove it wrong is not eligible.

| Element | Rule |
| --- | --- |
| BASELINE | Frozen at measurement start, not at accept time |
| PRIMARY METRIC | Must move for the intervention to have worked |
| GUARDRAIL METRIC | Must not degrade, even if primary improves |
| MEASUREMENT WINDOW | Fixed days; CDC default is 7 |
| RECHECK | Condition frozen at accept, evaluated at window end |
| SUCCESS | Explicit, directional, evidence-bound |
| FAILURE | Explicit; must be reachable |
| MIND CHANGE | What would invalidate the whole hypothesis, not just this test |

Baseline is frozen at **measurement start**, which CDC already separates from
accept via `measurement_started_at` and `measurement_start_authority`. Accepting
a mission is not evidence that the merchant executed it; measuring from accept
would attribute pre-execution noise to the intervention.

Failure must be reachable. A success condition with no symmetric failure
condition is not a measurement, it is a confirmation ritual.

## 2. Revenue is never sufficient

Revenue alone is never a sufficient primary metric. In CartFlow today it is
additionally not even measurable: `purchase_truth_records` carries no monetary
amount (see `ECONOMIC_INPUT_CONTRACT.md` §2). Purchase **count** truth exists and
is authoritative; purchase **value** truth does not.

A metric that improves while margin silently erodes is the specific failure a
guardrail exists to catch, which is why every economic intervention pairs a
conversion-style primary with a margin-style guardrail.

## 3. Per-family measurement

### Shipping clarification (Level 2, eligible today)

| Element | Value |
| --- | --- |
| Baseline | Shipping share of recorded hesitation reasons at measurement start |
| Primary | Shipping hesitation share, and cost-vs-duration split becoming distinguishable |
| Guardrail | No degradation in cart-to-purchase outcome |
| Window | 7 days (CDC default) |
| Recheck | Sufficiency threshold reached, or clear drop in shipping share |
| Success | Shipping share falls, or the split resolves clearly toward cost or duration |
| Failure | Share unchanged and split still ambiguous at window end |
| Mind change | Reason distribution shifts to a different dominant family |

The split resolving counts as success even without a share drop. The purpose of
a Level 2 disclosure test is to buy information that unlocks a better decision,
not to move the number by itself.

### Price value clarification (Level 2, eligible today)

| Element | Value |
| --- | --- |
| Baseline | Price share of recorded hesitation reasons |
| Primary | Price hesitation share |
| Guardrail | No degradation in cart-to-purchase outcome |
| Window | 7 days |
| Success | Price share falls without any price change |
| Failure | Share unchanged after value clarification is live |
| Mind change | Price share persists at high sufficiency, which raises the value of acquiring economic inputs rather than justifying a discount |

### Product confidence (Level 2, eligible today)

| Element | Value |
| --- | --- |
| Baseline | Product-confidence share of hesitation reasons |
| Primary | Product-confidence share |
| Guardrail | No degradation in cart-to-purchase outcome; no invented proof published |
| Window | 7 days |
| Success | Confidence share falls after authoritative evidence is surfaced |
| Failure | Share unchanged, indicating the gap is not informational |
| Mind change | Hesitation moves to price or shipping |

### Future free shipping (Level 3, blocked today)

Recorded for completeness; not emittable.

| Element | Value |
| --- | --- |
| Primary | Conversion |
| Guardrails | AOV **and** margin **and** shipping subsidy spend |
| Stop-loss | Cumulative subsidy breaching the merchant-declared bound before window end |

This intervention needs three guardrails because it can improve conversion while
destroying margin, which single-metric measurement would report as a win.

## 4. Causality contract

Observational result and causal result are stored and stated separately.

Allowed: `بعد التدخل تحسن المؤشر خلال نافذة القياس.`

Forbidden: `التدخل سبب التحسن.`

The distinction is not stylistic. A single-arm before/after comparison over seven
days cannot separate the intervention from seasonality, traffic mix, or
concurrent merchant activity. Controlled-experiment truth is a later level.

CDC already enforces part of this at the schema level:
`FORBIDDEN_CLOSE_REASONS = {"won", "lost", "learned", "purchase", "measurement_expired"}`.
CartFlow deliberately refuses to persist an outcome verdict. This contract keeps
that property.

Consequently no measurement-result column is proposed. The observational delta is
derived at read time from `baseline_snapshot_json` plus current evidence. Storing
a result would create a durable claim that outlives the evidence that justified
it, and would invite a causal reading of a correlational number.

## 5. Attribution protection

Measurement attribution is protected by Mission Portfolio, not by this contract.
`MAX_ACTIVE_MISSIONS = 1` and `MEASUREMENT_CONTAMINATION_PAIRS` already prevent a
second intervention from starting during an active measurement window. This
contract adds no parallel enforcement; it declares `conflict_group` and lets
Portfolio decide.
