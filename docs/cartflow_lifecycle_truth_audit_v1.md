# CartFlow Lifecycle Truth Audit v1

**Date (UTC):** 2026-05-23  
**Scope:** Read-only inventory of runtime lifecycle states before implementing “Lifecycle Truth” as a unified product layer.  
**Commit message (when landed):** `docs: add lifecycle truth audit v1`

No runtime, recovery, widget, WhatsApp, onboarding, auth, purchase-truth, schedule, or dashboard **behavior** changes in this pass — documentation and grep evidence only.

---

## 1. Executive summary

CartFlow lifecycle truth is **distributed** across at least six surfaces that do not share one enum:

| Surface | Primary module / table | Role |
|---------|------------------------|------|
| **A** | `CartRecoveryLog.status` | Append-only operational log of each recovery step outcome |
| **B** | `RecoverySchedule.status` | Durable delayed-send worker rows (restart survival) |
| **C** | `recovery_key` session flags (`main.py`) | In-memory: sent / converted / scheduled-for-return |
| **D** | Dashboard `phase_key` + `coarse` | Merchant UI narrative (`main._NORMAL_RECOVERY_PHASE_ORDER`) |
| **E** | `services/lifecycle_intelligence.py` | Observation-only decision (STOP/WAIT/HANDOFF/…) |
| **F** | Purchase Truth + closure | Durable `purchase_truth_records` + `closed_purchase` terminal |

**Observed product precedence (multiple implementations):**

1. **Purchase** — `cartflow_purchase_truth` + `purchase_lifecycle_closure` + `stopped_converted` / `recovery_state=converted` (highest stop)
2. **Reply** — `skipped_followup_customer_replied`, `behavioral_replied`, continuation / reply intent
3. **Return to site** — `returned_to_site`, `skipped_anti_spam`, `customer_returned`
4. **Delay / queue** — `queued`, `skipped_delay_gate`, `RecoverySchedule.scheduled`
5. **Send** — `mock_sent`, `sent_real`

Canonical reconciliation (read-only) also exists in `services/cartflow_lifecycle_guard.py` (`STATE_CONVERTED` … `STATE_ABANDONED`).

Prior audit: `docs/audit_lifecycle_truth_completion_v1.md` (2026-05-19) — three decision layers; still valid; this document expands **state inventory** and **conflicts**.

---

## 2. Part 1 — State inventory (by source)

### 2.1 `AbandonedCart.status` (ORM default `detected`)

| Value | Evidence | Typical meaning |
|-------|----------|-----------------|
| `detected` | `models.py` L168 default | Row created / seen in catalog |
| `abandoned` | Tests, VIP paths, `main.py` | Active abandoned cart |
| `recovered` | `main.py` L14483 filter, merchant tests | Purchase / recovery success on row |

**Related (VIP-only column):** `vip_lifecycle_status` — comment L184: `abandoned` / `contacted` / `closed` / `converted` (dashboard VIP section, not normal recovery).

**Classification:** ACTIVE (cart row lifecycle).

---

### 2.2 `CartRecoveryLog.status` (append-only recovery log)

Values observed in **production code paths** (`main.py`, `services/whatsapp_queue.py`, `services/cartflow_merchant_clarity.py`):

| Status | Evidence (representative) |
|--------|-------------------------|
| `queued` | `main.py` L7705; `LOG_LABELS` in `cartflow_merchant_clarity.py` L22 |
| `mock_sent` | `main.py` L7875; sent set L3065 |
| `sent_real` | `routes/cartflow.py` L165; queue path |
| `skipped_delay` | `main.py` L8549 |
| `skipped_delay_gate` | `main.py` L7220 |
| `skipped_duplicate` | `main.py` L7044, L8572 |
| `skipped_no_verified_phone` | `main.py` L7296 |
| `skipped_missing_phone` | `main.py` L8531 |
| `skipped_missing_reason_tag` | `main.py` L6919, L8495 |
| `skipped_missing_last_activity` | `main.py` L7532 |
| `skipped_reason_template_disabled` | `main.py` L6932 |
| `skipped_attempt_limit` | `main.py` L7067, L7412 |
| `skipped_followup_customer_replied` | `main.py` L6771 |
| `skipped_user_rejected_help` | `main.py` L6835, `whatsapp_queue.py` L201 |
| `skipped_anti_spam` | Tests; mapped in `cartflow_lifecycle_guard.py` L208 |
| `returned_to_site` | `main.py` L2363 `_DURABLE_RETURN_TO_SITE_LOG_STATUS` |
| `stopped_converted` | `main.py` L6817, conversion paths |
| `whatsapp_failed` | `main.py` L7861 |
| `failed_retry` | `services/whatsapp_queue.py` L262 (queue retries) |
| `failed_final` | `services/whatsapp_queue.py` L286; `routes/cartflow.py` L166 |
| `vip_manual_handling` | `main.py` L5178, L9009 |

**Note:** Latest log status drives much dashboard copy; historical rows can coexist in DB (not a single current state).

**Classification:** ACTIVE (primary operational audit trail).

---

### 2.3 `RecoverySchedule.status` (durable worker)

Defined in `services/recovery_restart_survival.py` L24–35:

| Constant | String value |
|----------|--------------|
| `STATUS_SCHEDULED` | `scheduled` |
| `STATUS_RUNNING` | `running` |
| `STATUS_COMPLETED` | `completed` |
| `STATUS_CANCELLED` | `cancelled` |
| `STATUS_SKIPPED_RESUME` | `skipped_resume_unsafe` |
| `STATUS_NEEDS_REVIEW` | `needs_review` |
| `STATUS_FAILED_RESUME` | `failed_resume` |
| `STATUS_FAILED_RESUME_STALE` | `failed_resume_stale` |
| `STATUS_SKIPPED_DUPLICATE` | `skipped_duplicate` |
| `STATUS_SKIPPED_NO_PHONE` | `skipped_no_phone` |
| `STATUS_SKIPPED_NO_REASON` | `skipped_no_reason` |
| `STATUS_WHATSAPP_FAILED` | `whatsapp_failed` |

Purchase stop writes `cancelled` with `last_error` containing `purchase_truth_stop` (`cancel_durable_schedules_for_purchase`).

**Classification:** ACTIVE (delay / restart survival); distinct from `CartRecoveryLog`.

---

### 2.4 API `recovery_state` (cart-event / abandon handler responses)

Returned from `main.py` scheduling paths (grep `recovery_state`):

| `recovery_state` | When (evidence) |
|------------------|-----------------|
| `waiting_for_reason` | L8501 — no reason tag yet |
| `waiting_for_phone` | L8537 — phone not ready |
| `scheduled` | L8616, L8651 — recovery armed |
| `sent` | L8554 — session already sent |
| `skipped_duplicate` | L8577 — duplicate abandon while in-flight |
| `converted` | L8757 — purchase / conversion |
| `vip_manual_handling` | L8456 — VIP path |

**Classification:** ACTIVE (client/API contract); not persisted as enum column.

---

### 2.5 In-memory session flags (`recovery_key`)

`main.py` L2247–2248:

- `_session_recovery_sent[recovery_key]`
- `_session_recovery_converted[recovery_key]`

Used by: duplicate send guard, `_is_user_converted`, purchase truth (`cartflow_purchase_truth._mark_session_converted`), lifecycle closure checks (`purchase_lifecycle_closure._lifecycle_already_closed_in_memory`).

**Classification:** ACTIVE (process-local; lost on restart unless rebuilt from DB/logs).

---

### 2.6 Dashboard `phase_key` (normal recovery UI)

`main._NORMAL_RECOVERY_PHASE_ORDER` L3031–3043:

| `phase_key` | Arabic label (UI) |
|-------------|-------------------|
| `pending_send` | بانتظار الإرسال |
| `first_message_sent` | تم إرسال الرسالة الأولى |
| `pending_second_attempt` | بانتظار المحاولة الثانية |
| `reminder_sent` | تم إرسال الرسالة الثانية |
| `behavioral_link_clicked` | عاد لصفحة الدفع |
| `behavioral_replied` | العميل تفاعل مع الرسالة |
| `customer_returned` | عاد للموقع — تم إيقاف التسلسل |
| `ignored` | متجاهل |
| `stopped_manual` | تم الإيقاف |
| `stopped_purchase` | تم التحويل |
| `recovery_complete` | اكتمل الاسترجاع |
| `blocked_missing_customer_phone` | (overlay; L3046–3048) |

**Coarse bucket** (`_normal_recovery_coarse_status` L3853–3879):  
`pending`, `sent`, `replied`, `clicked`, `returned`, `ignored`, `stopped`, `converted`, `blocked`.

**Classification:** ACTIVE (presentation); derived from logs + behavioral JSON.

---

### 2.7 Lifecycle intelligence (observation only)

`services/lifecycle_intelligence.py`:

**Behaviors:** `purchase_completed`, `returned_to_site`, `customer_replied`, `ignored`, `delay_waiting`, `unknown`.

**Decisions:** `STOP`, `CONTINUE`, `WAIT`, `HANDOFF`, `FALLBACK`.

**Actions (examples):** `close_lifecycle`, `no_send`, `handoff_continuation`, `proceed_recovery`, `wait_schedule`, `reason_then_delay`.

**Classification:** ACTIVE (logging/gates in `main._observe_lifecycle_intelligence_decision`); does not persist its own row.

---

### 2.8 Purchase Truth (durable + terminal)

| State / field | Owner | Evidence |
|---------------|-------|----------|
| `purchase_truth_records.purchase_detected` | `models.PurchaseTruthRecord` | `models.py` L427 |
| `purchase_detected=true` (normalized) | `cartflow_purchase_truth` | `record_purchase()` |
| `terminal_state=closed_purchase` | `purchase_lifecycle_closure` | L19, logs L61 |
| `lifecycle_terminal_state` (behavioral patch) | `behavioral_patch_for_closed_purchase` | L154–160 |
| Evidence sources | `extract_purchase_evidence` | `order_paid`, `checkout_completed`, `purchase_completed`, `order_created`, `order_completed`, `user_converted`, events |

**Logs:** `[PURCHASE DETECTED]`, `[PURCHASE SOURCE]`, `[PURCHASE STOP]`, `[PURCHASE TRUTH]`, `[PURCHASE LIFECYCLE CLOSED]`, `[RECOVERY BLOCKED] reason=lifecycle_closed_purchase`.

**Classification:** ACTIVE (highest stop truth when evidence present).

---

### 2.9 Reply / continuation states

**Reply intent** (`services/reply_intent_handling.py`): `PURCHASE`, `STOP`, `PRICE`, `DELIVERY`, `UNKNOWN` → decisions `STOP` / `HANDOFF` / `FALLBACK` + actions `close_lifecycle`, `stop_recovery`, etc.

**Continuation state keys** (`cartflow_reply_intent_engine.continuation_state_key` L425–450):  
`customer_needs_human_help`, `recovery_closing`, `customer_ready_for_checkout`, `customer_interested_in_alternative`, `customer_asking_*`, `customer_hesitating`, `customer_replied`.

Stored on behavioral payload: `continuation_state`, `continuation_automation_stopped`, `lifecycle_terminal_state`.

**Classification:** ACTIVE (post-send automation); overlaps reply + purchase closure.

---

### 2.10 WhatsApp delivery truth (orthogonal to recovery lifecycle)

`services/whatsapp_delivery_truth_v1.py` — `truth_level`:  
`unknown`, `accepted_by_provider`, `sent_to_network`, `delivered_to_customer`, `read_by_customer`, `failed_delivery`.

**Classification:** ACTIVE for **delivery**; must not be confused with `CartRecoveryLog.status=sent_real`.

---

### 2.11 Merchant follow-up actions

`services/whatsapp_positive_reply.py`:  
`needs_merchant_followup`, `completed` (MerchantFollowupAction.status).

**Classification:** ACTIVE (merchant inbox); parallel to recovery log.

---

### 2.12 Canonical guard model (reconciliation)

`services/cartflow_lifecycle_guard.py` — abstract states:  
`abandoned`, `waiting_delay`, `queued`, `send_started`, `sent`, `replied`, `returned`, `converted`, `stopped`, `failed`, `duplicate_blocked`, `unknown`.

Maps from log status, phase_key, lifecycle hints (`map_recovery_log_status_to_state`, `map_dashboard_phase_to_state`).

**Classification:** ACTIVE (diagnostics + merge pruning); not written to DB as single column.

---

### 2.13 Blocker keys (dashboard / clarity)

`services/cartflow_merchant_clarity.py` `BLOCKER_GROUPS` L40–71:  
`missing_customer_phone`, `missing_reason`, `whatsapp_failed`, `duplicate_attempt_blocked`, `user_returned`, `customer_replied`, `purchase_completed`, `automation_disabled`.

**Classification:** ACTIVE (derived labels).

---

## 3. Part 2 — Lifecycle Truth Map (selected states)

Full inventory above; below is the required per-state template for **highest-impact** states.

---

### STATE: `purchase_detected` / Purchase Truth

| Field | Value |
|-------|--------|
| **Owner** | Purchase Truth (`services/cartflow_purchase_truth.py`) + facade `services/purchase_truth.py` |
| **Source of truth** | `purchase_truth_records` row + `_session_recovery_converted` + `purchase_lifecycle_closure._closed_keys` |
| **Terminal?** | **YES** (for recovery automation) |
| **Overrides** | All scheduled recovery, delay wake (`stop_if_purchased`), continuation when `closed_purchase` |
| **Can coexist with** | Historical `queued` / `mock_sent` logs (past tense); must not coexist with **new** sends after truth |
| **Displayed to merchant** | `stopped_purchase` / `purchase_complete` / «تمت عملية الشراء — انتهت مهمة الاسترجاع» (`cartflow_merchant_lifecycle.py` L91–96) |
| **Risk** | Operators who only read `CartRecoveryLog` latest=`queued` may miss purchase; grep `[PURCHASE TRUTH]` |

---

### STATE: `closed_purchase` (terminal behavioral)

| Field | Value |
|-------|--------|
| **Owner** | `services/purchase_lifecycle_closure.py` |
| **Source of truth** | In-memory `_closed_keys` + behavioral `lifecycle_terminal_state` |
| **Terminal?** | **YES** |
| **Overrides** | Recovery sequence entry (`block_recovery_if_purchase_lifecycle_closed`), continuation skip |
| **Can coexist with** | Old log lines; not with active `RecoverySchedule.scheduled` after cancel |
| **Displayed to merchant** | Via purchased evidence / phase `stopped_purchase` |
| **Risk** | Process restart: closure memory cleared unless purchase_truth DB row exists |

---

### STATE: `stopped_converted` (log)

| Field | Value |
|-------|--------|
| **Owner** | Recovery sequence / conversion (`main.py`) |
| **Source of truth** | Latest `CartRecoveryLog.status` + conversion API |
| **Terminal?** | **YES** (merchant precedence treats as purchased — `lifecycle_purchased_evidence`) |
| **Overrides** | Further sends in same sequence (tail steps) |
| **Can coexist with** | Earlier `mock_sent` in same session |
| **Displayed to merchant** | «تم إيقاف الاسترجاع بعد الشراء» (`LOG_LABELS`) |
| **Risk** | Set without `purchase_truth_records` in older paths — dual paths to “converted” |

---

### STATE: `returned_to_site` / `skipped_anti_spam`

| Field | Value |
|-------|--------|
| **Owner** | Return-to-site tracker + anti-spam (`main` durable log constant L2363) |
| **Source of truth** | `CartRecoveryLog` + behavioral `user_returned_to_site` |
| **Terminal?** | **YES** for automated send (STOP / no_send in lifecycle intelligence) |
| **Overrides** | Delayed send, follow-up automation |
| **Can coexist with** | `queued` if ordering wrong (known guard issue: `returned_while_queued_pending` in `cartflow_session_consistency.py`) |
| **Displayed to merchant** | `customer_returned` phase / «عاد للموقع» |
| **Risk** | Temporal: return after queue but before send |

---

### STATE: `skipped_followup_customer_replied`

| Field | Value |
|-------|--------|
| **Owner** | Recovery sequence (`main.py` post-reply) |
| **Source of truth** | `CartRecoveryLog` + behavioral `customer_replied` |
| **Terminal?** | **Partial** — stops **follow-up** sends, not always full closure |
| **Overrides** | Second+ attempts in sequence |
| **Can coexist with** | `mock_sent` (first message already sent) |
| **Displayed to merchant** | «توقف الإرسال بعد تفاعل العميل» |
| **Risk** | Lifecycle intelligence logs **HANDOFF** while execution suppresses — naming mismatch (prior audit P2) |

---

### STATE: `queued`

| Field | Value |
|-------|--------|
| **Owner** | Recovery scheduler / delay dispatcher |
| **Source of truth** | `CartRecoveryLog` + optionally `RecoverySchedule.scheduled` |
| **Terminal?** | **NO** |
| **Overrides** | Nothing; superseded by send or skip |
| **Can coexist with** | `skipped_delay_gate` (delay not elapsed) |
| **Displayed to merchant** | «تم جدولة الاسترجاع — بانتظار وقت الإرسال» |
| **Risk** | Stale `queued` as “latest” after purchase/return — dashboard lie |

---

### STATE: `skipped_delay_gate`

| Field | Value |
|-------|--------|
| **Owner** | `_run_recovery_sequence_after_cart_abandoned_impl` delay gate |
| **Source of truth** | `CartRecoveryLog` L7220 |
| **Terminal?** | **NO** (waiting) |
| **Overrides** | Send until delay satisfied |
| **Can coexist with** | `RecoverySchedule.scheduled` |
| **Displayed to merchant** | «بانتظار المهلة قبل الإرسال» |
| **Risk** | Confused with failure |

---

### STATE: `mock_sent` / `sent_real`

| Field | Value |
|-------|--------|
| **Owner** | Send path (`main`) vs WhatsApp queue |
| **Source of truth** | `CartRecoveryLog` |
| **Terminal?** | **NO** (mid-lifecycle) |
| **Overrides** | Waiting states for that attempt |
| **Can coexist with** | Later `stopped_converted` or skips |
| **Displayed to merchant** | `first_message_sent` / `sent` coarse |
| **Risk** | `mock_sent` in production sandbox looks “sent” but may not be Twilio-delivered |

---

### STATE: `RecoverySchedule.scheduled`

| Field | Value |
|-------|--------|
| **Owner** | `services/recovery_restart_survival.py` |
| **Source of truth** | `recovery_schedules` table |
| **Terminal?** | **NO** until `completed` / `cancelled` / failed/skipped variants |
| **Overrides** | N/A — parallel track to logs |
| **Can coexist with** | `CartRecoveryLog.queued` and purchase truth cancel |
| **Displayed to merchant** | Indirectly via “بانتظار” copy |
| **Risk** | Orphan `scheduled` after purchase if cancel fails |

---

### STATE: `waiting_for_phone` / `waiting_for_reason`

| Field | Value |
|-------|--------|
| **Owner** | Cart-event handler (`main.py` L8495–8538) |
| **Source of truth** | API response only (+ pending phone/reason arms) |
| **Terminal?** | **NO** |
| **Overrides** | Scheduling until resolved |
| **Can coexist with** | `AbandonedCart` row |
| **Displayed to merchant** | Blockers `missing_customer_phone` / `missing_reason` |
| **Risk** | Not a DB enum — easy to lose on refresh |

---

### STATE: `vip_manual_handling`

| Field | Value |
|-------|--------|
| **Owner** | VIP decision engine |
| **Source of truth** | `CartRecoveryLog` + VIP flags on cart |
| **Terminal?** | **YES** for **normal** automated recovery |
| **Overrides** | Standard recovery sequence |
| **Can coexist with** | Separate VIP lifecycle column |
| **Displayed to merchant** | VIP dashboard sections |
| **Risk** | Must not mix into normal cart lists (documented elsewhere) |

---

## 4. Part 3 — Precedence proposal (unified target)

Align implementers on **one** rank order (matches `lifecycle_intelligence.resolve_lifecycle_behavior` + merchant precedence module + purchase truth wiring):

```text
purchase / converted  (100)
  > stopped / manual stop (95)
  > replied / handoff (88)
  > returned_to_site (82)
  > sent (75)
  > failed send (70)
  > duplicate_blocked (62)
  > send_started (55)
  > queued / waiting_delay (48–52)
  > abandoned / pending setup (40)
```

**Evidence:** `cartflow_lifecycle_guard._PRECEDENCE` L37–50; `lifecycle_intelligence` L74–75; `cartflow_merchant_lifecycle_precedence` L89+.

---

## 5. Part 4 — Conflict detection

Documented invalid or high-risk combinations (from `cartflow_lifecycle_guard._INVALID_JUMP_MESSAGES` + session consistency + operational experience):

| Combination | Severity | Why impossible / misleading | Evidence |
|-------------|----------|----------------------------|----------|
| `sent` + `converted` (same active window) | High | Send after purchase | `_INVALID_JUMP_MESSAGES` L160–161 |
| `send_started` + `converted` | High | Same | L161 |
| `sent` + `replied` (active send after reply) | High | Should suppress follow-up | L162–163 |
| `sent` + `returned` | High | Send after return | L164–165 |
| `duplicate_blocked` + `sent` (same moment) | Medium | Duplicate guard vs send | L166 |
| `queued` + `purchase_detected` (latest log only) | Medium | Stale queue display | Session consistency L247–254 |
| `scheduled` (RecoverySchedule) + `cancelled` (same row) | Low | Terminal row state — mutually exclusive per row | DB row single `status` |
| `waiting` + `purchased` (coarse) | Medium | UI must use precedence — `lifecycle_purchased_evidence` | `merchant_lifecycle_precedence` |
| `mock_sent` + `skipped_duplicate` (sequence) | Low | Valid timeline: sent then duplicate abandon | Tests `test_cart_recovery_sequence_behavior` |
| `running` + `completed` (schedule) | Low | Invalid on **same** schedule row | Worker claims `running` then terminal |

**Not conflicts (valid timelines):** `mock_sent` → `stopped_converted`; `queued` → `skipped_delay_gate` → `mock_sent`.

---

## 6. Part 5 — Active vs legacy classification

| Category | States / surfaces |
|----------|-------------------|
| **ACTIVE** | All `CartRecoveryLog.status` in §2.2; `RecoverySchedule` constants; API `recovery_state`; `phase_key` / `coarse`; purchase truth + `closed_purchase`; lifecycle intelligence; reply/continuation; guard canonical states; WhatsApp delivery truth |
| **LEGACY / alias** | `skipped_delay` (mapped to waiting in guard L200 — prefer `skipped_delay_gate`); `customer_returned` vs `returned_to_site` duplicate narrative; `recovery_complete` vs `stopped_purchase` overlap; `sent` API state when log shows `skipped_delay` (L8554) |
| **UNKNOWN / session-only** | `_session_recovery_sent` without DB mirror; dev-only behaviors in `/dev/*` routes (not inventory here) |

---

## 7. Terminal states summary

| Terminal for automation | Surfaces |
|-------------------------|----------|
| Purchase / conversion | `purchase_truth_records`, `stopped_converted`, `recovery_state=converted`, `phase_key` in (`stopped_purchase`,`recovery_complete`), `STATE_CONVERTED`, `closed_purchase` |
| Return to site | `returned_to_site`, `skipped_anti_spam`, `customer_returned`, STOP in lifecycle intelligence |
| Reply stop / reject | `skipped_followup_customer_replied`, `skipped_user_rejected_help`, reply STOP intent |
| VIP manual | `vip_manual_handling` |
| Attempt cap | `skipped_attempt_limit` |
| Duplicate (in-flight) | `skipped_duplicate`, `recovery_state=skipped_duplicate` |
| Schedule cancelled | `RecoverySchedule.cancelled` (incl. purchase stop) |
| Failed final (send) | `failed_final` (no more queue retries) |

**Non-terminal (waiting):** `queued`, `skipped_delay_gate`, `waiting_for_phone`, `waiting_for_reason`, `pending_*` phases, `RecoverySchedule.scheduled`, `STATUS_RUNNING` (in progress).

---

## 8. Evidence index (grep / code references)

| Search | Primary hits |
|--------|----------------|
| `RecoverySchedule` status constants | `services/recovery_restart_survival.py` L24–35 |
| `CartRecoveryLog` / `status=` in recovery | `main.py` (50+ persist sites), `services/whatsapp_queue.py` |
| `recovery_state` API | `main.py` L8456–8828 |
| Phase keys | `main.py` L3031–3043, L3853–3879 |
| Guard mapping | `services/cartflow_lifecycle_guard.py` L194–248 |
| Merchant precedence | `services/cartflow_merchant_lifecycle_precedence.py` |
| Purchase truth | `services/cartflow_purchase_truth.py`, `models.PurchaseTruthRecord` |
| Lifecycle intelligence | `services/lifecycle_intelligence.py` |
| Prior completion audit | `docs/audit_lifecycle_truth_completion_v1.md` |
| Tests (behavior) | `tests/test_cartflow_lifecycle_consistency.py`, `tests/test_purchase_truth_lifecycle_v1.py`, `tests/test_cartflow_purchase_truth_foundation_v1.py` |

**Suggested operator grep order (no code change):**

```text
[PURCHASE TRUTH]
[PURCHASE LIFECYCLE CLOSED]
[PURCHASE STOP]
[RECOVERY BLOCKED]
[LIFECYCLE DECISION]
[REPLY INTENT]
```

---

## 9. Out of scope / next implementation (not this audit)

- Unified `Lifecycle Truth` service writing a single read model
- Attribution analytics
- Dashboard redesign
- Wiring platform webhooks beyond existing conversion / purchase truth ingest
- Changing decision engine precedence in `main` send paths

---

## 10. Verification checklist (reviewer)

- [ ] Inventory matches your production logs (spot-check 5 sessions)
- [ ] Terminal list matches stop behavior you expect in QA
- [ ] Conflict table acceptable for v1 implementation planning
- [ ] Legacy aliases documented before renaming any `CartRecoveryLog.status`

**After review:** commit `docs: add lifecycle truth audit v1` — push to `main` only when approved.
