# Return-Without-Purchase Merchant Explanation V1

**Date:** 2026-07-05  
**Scope:** Presentation-only — merchant dashboard language, Daily Brief composer, proof surface.  
**Unchanged:** Purchase Truth, Lifecycle Truth ownership, Recovery scheduling, Provider Truth.

---

## 1. Problem

Merchants saw internal diagnostic wording in cart detail explanations:

- Raw lifecycle keys (`waiting_purchase_window`)
- Operational phrases (`سجل إرسال`, `قبول المزود`, `حالة المسار`)

Return-after-message without purchase was technically correct in backend truth but not clearly explained in merchant language.

---

## 2. Audit — current behavior (return without purchase)

| Question | Answer (from code) |
|----------|-------------------|
| State after send + return, no purchase | `customer_lifecycle_state = waiting_purchase_window` (`customer_lifecycle_states_v1.py`) |
| Does follow-up resume? | **Yes** — when `next_attempt_due_at` passes and return pause lifts, classifier moves to `waiting_next_scheduled` / sends per schedule; anti-spam (`skipped_anti_spam`) pauses immediate send only |
| Merchant action required? | **No** — `merchant_needed_ar = لا`, decision key `monitor` → `decision_monitor_return` (Observation) |
| Decision Layer | `resolve_merchant_decision_key_v1` → `monitor` for `return_to_site` and `waiting_purchase_window` |
| Daily Brief | Composer V2 treats `monitor` / Observation as **achievement**; headline from `decision_explanation.rationale_ar` |

Recovery scheduling behavior was **not** modified — only presentation and decision copy.

---

## 3. Implementation

### 3.1 Proof surface (`merchant_proof_surface_v1.py`)

- `why_we_know_ar` — merchant summary (what happened, reason, send acceptance) — **no raw state keys**
- `why_we_know_diagnostic_ar` — preserved internal chain (`حالة المسار: …`, `سجل إرسال مقبول`) for dev/admin
- Step label `message_accepted` → «إرسال الرسالة»; delivery notes merchant-friendly

### 3.2 Merchant lifecycle narrative (`cartflow_merchant_lifecycle.py`)

New primary `customer_returned_after_message` when return detected after provider send:

- **ماذا حدث؟** عاد العميل إلى المتجر بعد الرسالة.
- **ماذا فعل CartFlow؟** أوقف المتابعة مؤقتًا…
- **ماذا سيحدث؟** سيواصل المتابعة حسب الإعدادات إذا لم يكتمل الشراء.

### 3.3 Lifecycle v1 copy (`customer_lifecycle_states_v1.py`)

`waiting_purchase_window` explanation aligned to same narrative; unavailable label → «— لا تتوفر حالة واضحة بعد —».

### 3.4 Decision + Daily Brief

- `_build_explanation` for `waiting_purchase_window` → achievement-friendly rationale
- Composer V2 prefers `rationale_ar` for Observation achievements; aggregated monitor headline updated

### 3.5 Dashboard JS

- Proof block title «ملخص CartFlow» (was «لماذا نعرف؟»)
- Unavailable fallback strings updated

---

## 4. Verification report

| # | Question | Result |
|---|----------|--------|
| 1 | Behavior after return without purchase? | Pause (`waiting_purchase_window`); monitor decision; no merchant action |
| 2 | Recovery resumes automatically? | Yes — via existing `RecoverySchedule` / next due (unchanged) |
| 3 | Merchant action needed? | No |
| 4 | Merchant-facing text now? | Arabic narrative in lifecycle block + merchant lifecycle card; no raw keys in proof summary |
| 5 | Daily Brief when appropriate? | Yes — `decision_monitor_return` → achievement topic via Composer V2 |
| 6 | Technical terms removed from merchant dashboard? | Yes — proof `why_we_know_ar`, step labels, unavailable chip |
| 7 | Diagnostics preserved internally? | Yes — `why_we_know_diagnostic_ar`, `normal_recovery_diagnostics`, dev routes |
| 8 | Truth / Recovery behavior unchanged? | Yes — presentation-only diff |

---

## 5. Test scenarios

Automated: `tests/test_return_without_purchase_merchant_explanation_v1.py`

| Scenario | Expected |
|----------|----------|
| 1 — Return + purchase | Purchase proof copy; no internal keys |
| 2 — Return, no purchase during window | Waiting explanation; monitor decision; achievement-eligible |
| 3 — Window expires | Schedule resume path documented; merchant copy mentions auto continuation |
| 4 — Internal state present | Diagnostic field retains keys; merchant fields clean |

---

## 6. Governance flow (unchanged)

```
Truth / Lifecycle / Recovery
        ↓
Proof Surface (presentation)
        ↓
Merchant Decision Layer
        ↓
Daily Brief Composer V2
        ↓
Daily Brief UI
```

Daily Brief does **not** inspect raw Truth directly — only published decisions from row bundles.
