# CartFlow merchant operational clarity

## Philosophy

Operational clarity is **additive copy** for merchants: it explains what happened to a cart, why automation paused or continued, and what (if anything) requires action — without changing recovery, scheduling, or provider behavior. Wording stays **short, Arabic-first, and ROI-oriented** (actionability over analytics).

## Merchant trust rules

- **Waiting is not failure**: queued and delay-gate states are described as normal scheduling, not errors.
- **Intentional stops are not crashes**: reply suppression, return suppression, and purchase completion are framed as expected outcomes.
- **Protection is not malfunction**: duplicate prevention is described as protecting the customer experience.
- **No false success**: when a real blocker exists (e.g. missing phone, provider send failure), the clarity group moves to **يحتاج إجراء** or setup- incomplete categories.

## Lifecycle wording rules

Canonical labels and outcomes live in `services/cartflow_merchant_clarity.py`. Blocker keys reuse the same vocabulary as the dashboard blocker layer **without** replacing `recovery_blocker_display` (that module remains authoritative for blocker bundles). Clarity adds **parallel** fields on the normal-recovery payload:

- `merchant_clarity_group_ar` — operational category
- `merchant_clarity_headline_ar` — what happened (concise)
- `merchant_clarity_outcome_ar` — why the path looks this way
- `merchant_clarity_roi_hint_ar` — optional actionable hint
- `merchant_clarity_progress_chip_ar` — lightweight progress from existing phase steps (no new timeline UI)
- `merchant_clarity_waiting_is_normal` / `merchant_clarity_intentional_stop` — boolean truth flags for copy logic

## Operational grouping strategy

Groups are coarse buckets only:

- يحتاج إجراء
- يعمل بشكل طبيعي
- توقف بسبب تفاعل العميل
- توقف بسبب إعداد ناقص
- بانتظار تنفيذ الاسترجاع
- حماية تشغيلية (duplicate / guardrails)

## ROI-oriented communication

Hints focus on **what to do next** (phone capture, avoid over-messaging after return, monitor conversation after reply) rather than generic metrics.

## Simplicity constraints

- No new charts, realtime feeds, or AI summaries.
- Dashboard changes are **small inserts** (normal cart row strip + optional onboarding footnote).
- Runtime health exposes `merchant_operational_clarity_runtime` and trust may include `merchant_operational_clarity_ar` when supplements apply.

## Tests

See `tests/test_cartflow_merchant_clarity.py` for waiting vs failure, suppression wording, and grouping consistency.
