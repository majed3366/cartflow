# CartFlow — Attention Bucket Semantic Audit V1

**Date (UTC):** 2026-07-02  
**Status:** Read-only audit — no code, UI, or copy changes  
**Goal:** Determine what merchant question **«تحتاج تدخل»** is answering, and why rows appear there with phone + customer reply + no actionable control.

---

## 0. Executive answer

**«تحتاج تدخل» does not answer one question today — it names at least three different things:**

| Surface | Arabic label | Data source | Merchant question (implicit) |
|---------|--------------|-------------|------------------------------|
| Sidebar + `#page-followup` | **تحتاج تدخل** | `MerchantFollowupAction` rows (`STATUS_NEEDS_MERCHANT_FOLLOWUP`) | *“Which carts had a positive customer reply?”* |
| `#page-carts` filter chip | **يحتاج متابعة** | Lifecycle filter bucket `attention` | *“Which carts are in reply / engaged / intervention lifecycle?”* |
| Row lifecycle label | **تحتاج تدخل** | Only `customer_lifecycle_state = needs_intervention` | *“Something blocked automation — merchant may need to act.”* |

**Root ambiguity:** The lifecycle bucket `attention` (counter `engaged_total`, filter `attention`) groups **system-handled customer replies** with **true intervention blockers** under one operational label family. The follow-up page title says **تحتاج تدخل** while every row’s compact block explicitly says **تدخل: لا**.

**Against the proposed rule** (*«تحتاج تدخل» only when human action is possible, a recommended action exists, and an action button can exist*):

- **Most rows in the attention bucket fail the rule** (`customer_reply`, `customer_engaged`).
- **Most rows on `#page-followup` fail the rule** (system continuation; no contact/complete button in lazy UI).
- **Many `needs_intervention` rows partially fail** (`merchant_decision_key` may resolve server-side, but client `NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS` is empty — no «الإجراء المقترح»; only **نقل للأرشيف** is offered).

**States `manual_followup` and `customer_requested_help` do not exist** as lifecycle keys in the current source of truth.

---

## 1. STEP 1 — Lifecycle states mapped to `attention`

Canonical mapping: `lifecycle_state_to_filter_bucket()` in `services/customer_lifecycle_states_v1.py`.

| Lifecycle state | Arabic label (`LABEL_AR`) | Primary bucket | `merchant_needed_ar` | `what_next_ar` (merchant guidance) | `dashboard_action` | Actual merchant action in product |
|-----------------|---------------------------|----------------|----------------------|-----------------------------------|---------------------|-----------------------------------|
| `customer_reply` | رد العميل | `customer_reply` | **لا** | نراقب هل يكمّل الطلب أو يرد مرة أخرى | `archive` | Optional **نقل للأرشيف** only — no contact, no retry, no decision key |
| `customer_engaged` | تفاعل العميل — أرسل النظام متابعة | `customer_engaged` | **لا** | لا حاجة لرسائل إرسال إضافية — المتابعة آلية | `archive` | Same — system runs continuation; merchant dismiss only |
| `needs_intervention` (VIP lane) | تحتاج تدخل (VIP) / variants | `needs_followup` | **نعم** | تواصل مع العميل يدوياً عند الحاجة | `archive` | VIP has separate contact paths; normal-carts row: archive only |
| `needs_intervention` (send/channel failure) | تحتاج تدخل | `needs_followup` | **نعم** | أوقف CartFlow المسار الآلي مؤقتاً بانتظار إزالة العائق أو اكتمال البيانات | `archive` | Text guidance only; decision key may be `fix_channel` or `contact_customer` server-side — **not rendered** on normal carts |
| `needs_intervention` (missing phone, pre-send) | بانتظار اكتمال بيانات التواصل | `needs_followup` | **نعم** | لا توجد وسيلة تواصل — سيبدأ التواصل تلقائياً عند توفر البيانات | `archive` | Decision key `obtain_contact` server-side — **not executable in UI** |
| `needs_intervention` (schedule not materialized) | لم يتم تجهيز الإرسال بعد | `needs_followup` | **لا** | بانتظار اكتمال بيانات السلة — سيتابع CartFlow تلقائياً عند الجاهزية | `archive` | Wait state mis-bucketed into `attention` |

**Classifier legacy note:** `services/merchant_cart_row_classifier.py` can still emit `s-attention` for older primary keys, but normal-carts API **overwrites** `merchant_cart_bucket` / `merchant_cart_visible_tabs` from lifecycle attach (`attach_customer_lifecycle_state_v1`).

**Not in `attention` bucket (for contrast):**

| State | Bucket | Why it matters |
|-------|--------|----------------|
| `waiting_customer_reply` | `sent` | Awaiting reply — not “intervention” |
| `return_to_site` / `waiting_purchase_window` | `sent` | System monitors purchase |
| `waiting_next_scheduled` | `sent` (filter) / primary `needs_followup` | Scheduled send — not attention filter |

---

## 2. STEP 2 — Can the merchant do something now?

Interpretation: *Is there a dedicated, in-product intervention the dashboard offers for this state (not optional archive/dismiss)?*

| Lifecycle state | Merchant action possible now? | Rationale |
|-----------------|------------------------------|-----------|
| `customer_reply` | **NO** | `merchant_needed = لا`; no `merchant_decision_key`; continuation/monitoring is automatic |
| `customer_engaged` | **NO** | Same; continuation engine already started |
| `needs_intervention` + `merchant_needed = نعم` + phone + channel fail | **PARTIAL / NO in UI** | Backend may set `merchant_decision_key` (`fix_channel`, `contact_customer`) but `NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS = {}` suppresses «الإجراء المقترح»; only archive button |
| `needs_intervention` + missing phone | **NO in UI** | `obtain_contact` not wired; no in-dashboard phone capture |
| `needs_intervention` + schedule not materialized | **NO** | `merchant_needed = لا`; system wait |
| VIP `needs_intervention` on VIP page | **YES** (VIP lane only) | Manual WhatsApp / merchant alert — not on normal-carts table |

### Separate surface: `#page-followup` (`MerchantFollowupAction`)

| Field | Value |
|-------|-------|
| Trigger | Positive inbound WhatsApp reply → `MerchantFollowupAction` with `STATUS_NEEDS_MERCHANT_FOLLOWUP` |
| Page title | **تحتاج تدخل** |
| Row compact copy | **تدخل: لا** — «النظام يتابع تلقائياً» |
| Server payload | `contact_wa_href` built when phone exists |
| Lazy dashboard UI | **Does not render** `contact_wa_href` or complete action (API exists: `POST /api/merchant-followup-actions/{id}/complete`) |

| Follow-up row profile | Merchant action possible now? |
|-----------------------|------------------------------|
| Phone + customer replied + follow-up page | **NO** (in lazy merchant app) |

---

## 3. STEP 3 — Row profiles under «تحتاج تدخل» / `attention`

### 3.1 Profile A — *Customer replied, phone present, no intervention action* (**dominant mismatch**)

**Where shown:**

- `#page-carts` filter **يحتاج متابعة** (`attention`) — lifecycle `customer_reply` or `customer_engaged`
- `#page-followup` titled **تحتاج تدخل** — `MerchantFollowupAction` positive replies

**Typical signals:**

- `customer_lifecycle_state` ∈ `{customer_reply, customer_engaged}`
- `customer_lifecycle_merchant_needed_ar` = **لا**
- `merchant_decision_key` = absent
- Phone column: ✓ متوفر
- Customer reply visible in timeline / inbound message
- Buttons: **نقل للأرشيف** only on carts row (optional dismiss), or **no button** on follow-up page

**Why it lands in «attention»:** `lifecycle_state_to_filter_bucket()` maps both reply states to `UI_FILTER_ATTENTION` regardless of `merchant_needed`.

**Operational truth:** System is already handling follow-up; merchant question answered is *“customer engaged — watch or dismiss”*, not *“you must intervene now.”*

### 3.2 Profile B — *True intervention flag, phone present, no matching action*

**Where shown:** `#page-carts` → **يحتاج متابعة** / lifecycle label **تحتاج تدخل**

**Typical signals:**

- `customer_lifecycle_state` = `needs_intervention`
- `customer_lifecycle_merchant_needed_ar` = **نعم**
- `merchant_decision_key` ∈ `{fix_channel, contact_customer}` (server attach)
- Phone present
- UI: lifecycle block may show guidance text; **no** «الإجراء المقترح» line; **نقل للأرشيف** only

**Gap:** Semantics say intervention; product offers dismiss/archive, not the recommended decision.

### 3.3 Profile C — *Intervention state, no phone*

**Signals:** `needs_intervention`, label **بانتظار اكتمال بيانات التواصل**, `obtain_contact` key server-side.

**Shown under:** `attention` filter (and possibly **لا جوال** facet if pre-send).

**Action:** None in-dashboard — belongs closer to **لا يمكن المتابعة** than **تحتاج تدخل**.

### 3.4 Naming collision summary

```
Sidebar «تحتاج تدخل»
    → resolveCartPage('intervention') = 'followup'
    → MerchantFollowupAction (Profile A on follow-up page)

Filter «يحتاج متابعة» (attention)
    → merchant_cart_visible_tabs includes 'attention'
    → customer_reply + customer_engaged + needs_intervention (Profiles A, B, C)

Lifecycle label «تحتاج تدخل»
    → needs_intervention only (Profiles B, C subset)
```

Counter field `engaged_total` counts all three lifecycle states — label suggests “engagement,” not “intervention required.”

---

## 4. STEP 4 — Proposed operational groups

Design principle: **every merchant-visible bucket must imply a real, offered action** (or explicit “nothing to do — informational”).

| Proposed group (AR) | Merchant question | Lifecycle / source | Suggested action (product) | Maps from today |
|---------------------|-------------------|--------------------|-----------------------------|-----------------|
| **العميل تفاعل — متابعة آلية** | ماذا يفعل النظام بعد رد العميل؟ | `customer_reply`, `customer_engaged`; optionally `MerchantFollowupAction` when system owns continuation | Read-only status + optional archive | Split from `attention`; rename follow-up page away from «تحتاج تدخل» |
| **يحتاج متابعة** (informational queue) | ما الذي يستحق مراقبتي دون إجراء فوري؟ | High-value or time-sensitive sent paths if product wants a watchlist | Monitor / open timeline | Do **not** use for reply states if automation handles them |
| **طلب التواصل** | أين أتواصل مع عميل طلب مساعدة؟ | Future `customer_requested_help` or explicit positive-reply merchant-outreach policy | WhatsApp handoff + mark complete | Today: `contact_wa_href` exists but hidden; complete API exists but not in lazy UI |
| **يحتاج تدخل** | ماذا أفعل الآن لإزالة عائق؟ | `needs_intervention` **and** `merchant_needed = نعم` **and** executable `merchant_decision_key` | Render decision + matching button (fix channel / contact / obtain contact) | Subset of current `needs_intervention` only |
| **لا يمكن المتابعة** | لماذا توقف المسار وليس لدي أداة؟ | Missing phone, channel not configured, pre-send blockers without merchant tooling | Link to settings / widget guidance | `obtain_contact`, no-phone facet rows |
| **بانتظار الجاهزية** | متى يكمل النظام تلقائياً؟ | Schedule not materialized (`merchant_needed = لا`) | None — ETA or wait copy | Remove from `attention` bucket |

### Recommended strict rule for **تحتاج تدخل**

Show tab/label/filter **تحتاج تدخل** only when **all** hold:

1. `customer_lifecycle_state == needs_intervention`
2. `customer_lifecycle_merchant_needed_ar == نعم`
3. `merchant_decision_key` ∈ `{obtain_contact, fix_channel, contact_customer}`
4. Matching control is rendered (or deep-link to fix) — not archive-only

Everything else routes to the groups above.

---

## 5. Code references (authorities)

| Concern | Location |
|---------|----------|
| Attention bucket mapping | `services/customer_lifecycle_states_v1.py` — `lifecycle_state_to_filter_bucket()` |
| Reply / engaged / intervention classification | `services/customer_lifecycle_states_v1.py` — `classify_customer_lifecycle_state_v1()` |
| Decision keys (server) | `services/merchant_decision_layer_v1.py` — `resolve_merchant_decision_key_v1()` |
| Decision UI gate (client) | `static/merchant_dashboard_lazy.js` — `NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS = {}` |
| Lifecycle action buttons | `static/merchant_dashboard_lazy.js` — `cartLifecycleActionBtnHtml()` → archive / reopen only |
| Sidebar intervention → follow-up page | `static/merchant_app.js` — `resolveCartPage('intervention')` → `'followup'` |
| Intervention tab → attention filter (carts only) | `static/merchant_app.js` — `cartTabToFilterMode('intervention')` → `'attention'` |
| Counter `engaged_total` | `services/dashboard_counter_totals_v1.py` |
| Follow-up rows | `main.py` — `merchant_followup_actions_for_dashboard()` |
| Follow-up compact copy (تدخل: لا) | `templates/partials/merchant_followup_compact_block.html`, `followupCompactHtml()` |

---

## 6. Related audits

- `docs/cartflow_merchant_intervention_action_audit_v1.md` — `merchant_needed = نعم` without intervention CTA
- `docs/cartflow_merchant_action_matrix_v1.md` — archive/reopen inventory
- `docs/cartflow_dashboard_counter_parity_audit_v1_report.md` — `engaged_total` vs row sources

---

## 7. Conclusion

**What «تحتاج تدخل» currently answers:** inconsistently — either *“customer replied positively”* (follow-up page), *“any post-reply or blocked lifecycle state”* (attention filter), or *“automation stopped”* (lifecycle label).

**Why phone + reply + no action appears:** by design of bucket mapping and UI wiring — not a single-row bug. Reply states are intentionally automation-first (`merchant_needed = لا`) but bucketed into `attention` / shown on a page titled **تحتاج تدخل**.

**No fixes in this audit.** Implementation should split buckets, align Arabic labels to implied actions, and gate **تحتاج تدخل** on executable merchant decisions per §4.
