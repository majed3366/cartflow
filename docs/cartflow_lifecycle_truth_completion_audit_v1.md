# Lifecycle Truth Completion Audit v1

**Date (UTC):** 2026-05-19  
**Scope:** Read-only audit — whether CartFlow has **complete lifecycle closure truth** (terminal states, stop behavior, UI/dashboard alignment, durability, conflicts).  
**Commit message:** `docs: add lifecycle truth completion audit v1`

**No runtime, recovery, dashboard, queue, widget, or WhatsApp changes.**

Related: `docs/cartflow_lifecycle_truth_audit_v1.md` (state inventory), `docs/audit_lifecycle_truth_completion_v1.md` (decision-layer matrix), `docs/cartflow_purchase_truth_audit_v1.md` (purchase durability), `docs/cartflow_lifecycle_truth_v1_examples.md` (canonical evaluator).

---

## Executive summary

CartFlow **does stop recovery** for the main terminal outcomes (purchase, return, reply suppress, VIP manual, attempt cap, duplicate in-flight, schedule cancel) via **multiple coordinated layers**. There is **no single “lifecycle closed” row** that proves completion for all paths.

**Verdict: PARTIAL**

| Question | Answer |
|----------|--------|
| Can automation stop correctly when evidence is present? | **Mostly yes** (purchase truth + send gates + schedule cancel) |
| Is there one durable “final truth” store? | **No** — distributed across logs, schedules, purchase truth, behavioral JSON, session cache |
| Does dashboard always show final truth? | **Partial** — derived `phase_key` / `coarse` can lag if **latest log** is stale |
| Is closure complete after process restart? | **Partial** — purchase truth + schedules durable; `purchase_lifecycle_closure` memory is not |
| Canonical precedence unified everywhere? | **No** — shadow evaluator vs `lifecycle_intelligence` order differ on reply vs return |

---

## 1. Terminal states inventory

States below are **terminal for automated recovery** unless marked *non-terminal*. Names reflect **code vocabulary** (multiple aliases per concept).

### 1.1 Purchase / converted (hard terminal)

| Name(s) | Primary surface |
|---------|-----------------|
| `purchase_detected` | `purchase_truth_records` |
| `purchase_completed` | API flags, blockers, lifecycle intelligence behavior |
| `user_converted` / `event=user_converted` | `POST /api/cart-event` |
| `stopped_converted` | `CartRecoveryLog.status` |
| `recovery_state=converted` | Cart-event API response |
| `closed_purchase` | `purchase_lifecycle_closure` + behavioral `lifecycle_terminal_state` |
| `stopped_purchase` / `recovery_complete` | Dashboard `phase_key` |
| `coarse=converted` | Dashboard bucket |
| Canonical `purchased` | `evaluate_lifecycle_truth()` (shadow) |
| `STATE_CONVERTED` | `cartflow_lifecycle_guard` |

### 1.2 Reply / customer engagement (soft or hard terminal)

| Name(s) | Primary surface |
|---------|-----------------|
| `customer_replied` | Lifecycle intelligence → **HANDOFF** (observe) |
| `skipped_followup_customer_replied` | `CartRecoveryLog` — **stops follow-up** in sequence |
| `skipped_user_rejected_help` | `CartRecoveryLog` — user rejected help |
| Reply intent `STOP` | `reply_intent_handling` → `stop_recovery` |
| Reply intent `PURCHASE` | `close_lifecycle` → `record_purchase_lifecycle_closure` |
| `behavioral_replied` / `phase_key=behavioral_replied` | Dashboard |
| `coarse=replied` | Dashboard |
| Canonical `replied` | `evaluate_lifecycle_truth()` |
| `continuation_automation_stopped` | Behavioral patch (continuation engine) |

### 1.3 Return to site (terminal for send)

| Name(s) | Primary surface |
|---------|-----------------|
| `returned_to_site` | Durable log constant `main._DURABLE_RETURN_TO_SITE_LOG_STATUS` |
| `skipped_anti_spam` | Log alias / guard mapping |
| `user_returned` / `customer_returned` | Blockers, `phase_key` |
| `coarse=returned` | Dashboard |
| Canonical `returned` | `evaluate_lifecycle_truth()` |
| Lifecycle intelligence | **STOP** + `no_send` |

### 1.4 Recovered (merchant / cart row — business outcome)

| Name(s) | Primary surface |
|---------|-----------------|
| `AbandonedCart.status=recovered` | ORM cart row |
| `recovery_complete` | `phase_key` when cart status recovered |
| `stopped_purchase` | Phase when purchase evidence without recovered row |
| Interaction `recovered` | `recovery_interaction_state.STATE_RECOVERED` (terminal in inbox layer) |

*Note:* “Recovered” in KPIs can mean **revenue outcome** or **cart row status**, not always the same as “recovery automation closed.”

### 1.5 Failed send (terminal for that attempt / queue)

| Name(s) | Primary surface |
|---------|-----------------|
| `whatsapp_failed` | `CartRecoveryLog`, `RecoverySchedule.STATUS_WHATSAPP_FAILED` |
| `failed_retry` | Queue retry in flight |
| `failed_final` | Queue exhausted retries |
| Canonical `failed` | `evaluate_lifecycle_truth()` |
| Blocker `whatsapp_failed` | Merchant clarity |

### 1.6 Cancelled / stopped manual

| Name(s) | Primary surface |
|---------|-----------------|
| `RecoverySchedule.status=cancelled` | Durable schedule row |
| `last_error` contains `purchase_truth_stop` | Purchase cancel |
| `stopped_manual` | `phase_key` |
| `coarse=stopped` | Dashboard |
| Canonical `cancelled` | `evaluate_lifecycle_truth()` |

### 1.7 Caps and duplicates

| Name(s) | Primary surface |
|---------|-----------------|
| `skipped_attempt_limit` / `max_attempts_reached` | Log + decision engine tag |
| `skipped_duplicate` | Log + `recovery_state=skipped_duplicate` |
| `duplicate_attempt_blocked` | Blocker key |

### 1.8 VIP / manual handling

| Name(s) | Primary surface |
|---------|-----------------|
| `vip_manual_handling` | Log + `recovery_state` on VIP path |
| Canonical `vip_manual` | `evaluate_lifecycle_truth()` |

### 1.9 Explicitly *non-terminal* (waiting / in-progress)

| Name(s) | Why not terminal |
|---------|------------------|
| `queued`, `skipped_delay_gate`, `skipped_delay` | Waiting for delay or worker |
| `waiting_for_phone`, `waiting_for_reason` | Setup incomplete |
| `RecoverySchedule.scheduled` / `running` | In progress |
| `mock_sent`, `sent_real` | Mid-funnel (may precede terminal) |
| `ignored` (lifecycle intelligence) | **CONTINUE** — `attempt_{n+1}` |
| `pending_send`, `pending_second_attempt` | Dashboard pending phases |
| `checkout_started` | Widget suppress only — **not** lifecycle intelligence |

---

## 2. Closure verification matrix

Legend: **Y** = yes for intended path, **P** = partial / derived / can be wrong, **N** = no.

| Terminal family | Recovery stops? | Scheduling stops? | Dashboard reflects? | Merchant UI reflects? | Can reopen incorrectly? |
|-----------------|-----------------|-------------------|---------------------|------------------------|-------------------------|
| **Purchase / converted** | **Y** (`stop_if_purchased`, `_is_user_converted`, `block_recovery_if_purchase_lifecycle_closed`) | **Y** (`cancel_durable_schedules_for_purchase`) | **P** (`phase_key` `stopped_purchase` / `recovery_complete` via precedence) | **P** (normal carts payload `phase_key`, `coarse`) | **P** — without `purchase_truth_records`, session-only or log-only paths; new abandon if duplicate guard fails |
| **Reply (follow-up suppress)** | **P** (stops **follow-up** in sequence, not always first send) | **P** (may not cancel existing schedule unless other hooks run) | **Y** often (`behavioral_replied`, `coarse=replied`) | **P** | **P** — HANDOFF in logs vs suppress in execution; continuation may still run until `closed_purchase` |
| **Reply PURCHASE (text)** | **Y** (closure + flags) | **P** | **P** | **P** | **P** — may lack `purchase_truth_records`; weaker after restart |
| **Return to site** | **Y** (anti-spam, `_is_user_returned`, intelligence STOP) | **P** (schedule may still exist until wake/cancel) | **Y** (`customer_returned`) | **P** | **P** — `returned_while_queued_pending` race; passive return variants |
| **Recovered (cart row)** | **Y** (cart marked recovered on conversion paths) | **Y** if conversion ingested | **Y** (`recovery_complete`) | **Y** when status synced | **N** low if conversion durable |
| **Failed final** | **Y** (no successful send path) | **P** (`failed_final` log; schedule may be `whatsapp_failed`) | **P** (failed messaging in clarity) | **P** | **P** — retries until `failed_final`; new abandon could reschedule |
| **Cancelled (purchase)** | **Y** | **Y** | **P** (may still show `queued` as latest log) | **P** | **P** if cancel fails silently |
| **VIP manual** | **Y** (normal recovery not scheduled) | **N/A** (VIP path) | **Y** (VIP sections) | **Y** | **P** if VIP misclassified |
| **Attempt limit** | **Y** (`skipped_attempt_limit`) | **P** | **Y** | **P** | **P** — new session/abandon could start new sequence |
| **Duplicate in-flight** | **Y** (`skipped_duplicate`) | **P** | **P** | **P** | **P** — timing window before flag set |
| **Ignored** | **N** (CONTINUE) | **N** | **Y** (`phase_key=ignored`) | **P** | **Y** — by design sends continue |

**Dashboard / UI mechanism:** `main._normal_recovery_dashboard_phase_key()` + `build_merchant_recovery_lifecycle_truth()` + lazy normal-carts JSON (`phase_key`, `coarse`, blockers). Not a separate closure table.

---

## 3. Conflict scenarios

### 3.1 Purchase + reply (same session)

| Aspect | Behavior |
|--------|----------|
| **Canonical evaluator** (`cartflow_lifecycle_truth`) | **purchase wins** (tier 1 before tier 2) |
| **Lifecycle intelligence** (`decide_lifecycle_recovery`) | **purchase before return before reply** — purchase wins if `purchased=True` |
| **Execution** | Purchase truth cancels schedules; reply continuation checks `closed_purchase` / `is_purchase_lifecycle_closed` |
| **Risk** | Reply PURCHASE text without `purchase_truth_records` → closure memory only; dashboard may show **replied** if latest log is reply-skipped but purchase log older |

**Verdict:** Stops are **safe** if purchase ingested; **display** can disagree.

### 3.2 Return + scheduled send

| Aspect | Behavior |
|--------|----------|
| **Before wake** | `RecoverySchedule.scheduled` + log `queued` |
| **Return ingested** | Anti-spam / return flags → send blocked at wake |
| **Race** | Return after queue, before send — documented in `cartflow_session_consistency` (`returned_while_queued_pending`) |
| **Schedule** | May remain `scheduled` until worker runs `stop_if_purchased` / cancel path |

**Verdict:** Send suppression **usually works**; schedule row may look “pending” until worker.

### 3.3 Reply + send (follow-up)

| Aspect | Behavior |
|--------|----------|
| **First send** | May already have `mock_sent` / `sent_real` |
| **After reply** | `skipped_followup_customer_replied` — blocks **later** steps |
| **Intelligence** | Logs **HANDOFF** while execution is STOP-like |

**Verdict:** **Partial terminal** — conversation stopped, not always “closed” in one enum.

### 3.4 Purchase + delayed task (async recovery)

| Aspect | Behavior |
|--------|----------|
| **Delay** | `asyncio.sleep` then wake in `_run_recovery_sequence_after_cart_abandoned_impl` |
| **Purchase before wake** | `stop_if_purchased` → **return** (no send) |
| **Purchase after send, before tail** | `stopped_converted` on tail steps (tests) |
| **Purchase never ingested** | Send may complete — platform/widget must POST evidence |

**Verdict:** **Durable purchase truth** closes the race; **without ingest**, delayed send remains a gap.

### 3.5 Restart + terminal state

| Layer | After restart |
|-------|----------------|
| `purchase_truth_records` | **Survives** — `has_purchase` / `has_conversion_truth` |
| `RecoverySchedule.cancelled` | **Survives** |
| `CartRecoveryLog` history | **Survives** (append-only) |
| `_session_recovery_converted` | **Lost** — rehydrated from DB on read |
| `purchase_lifecycle_closure._closed_keys` | **Lost** — **not** durable; mitigated by purchase truth + session truth fallback |
| `RecoverySchedule.scheduled` (orphan) | **Risk** if cancel failed before crash |

**Verdict:** **PARTIAL** — purchase path is restart-safe; pure closure-without-truth is weaker.

### 3.6 Precedence mismatch (implementers)

| Module | Order |
|--------|-------|
| `cartflow_lifecycle_truth.evaluate_lifecycle_truth` | purchase **>** reply **>** return **>** waiting **>** send |
| `lifecycle_intelligence.decide_lifecycle_recovery` | purchase **>** return **>** reply **>** ignored **>** delay |

If `returned=True` and `replied=True` with `purchased=False`, **shadow canonical** = `replied`, **intelligence** = `returned` (STOP). Operators may see `[LIFECYCLE TRUTH MISMATCH]` in shadow mode only.

---

## 4. Durable evidence — what proves lifecycle closed?

| Proof type | Proves closure? | Durability | Typical terminal |
|------------|-----------------|------------|------------------|
| `purchase_truth_records` row | **Y** (purchase) | DB, per `recovery_key` | Purchase |
| `RecoverySchedule.status=cancelled` + `purchase_truth_stop` | **Y** (stop scheduled work) | DB | Purchase cancel |
| `CartRecoveryLog.status=stopped_converted` | **P** | DB append-only | Conversion in sequence |
| `CartRecoveryLog` terminal skips (`skipped_*`, `failed_final`) | **P** (per event type) | DB | Reply, return, caps, fail |
| `_session_recovery_converted` | **P** | Process memory | Purchase mirror |
| `purchase_lifecycle_closure._closed_keys` | **P** | Process memory only | Purchase / reply PURCHASE |
| Behavioral `lifecycle_terminal_state=closed_purchase` | **P** | `AbandonedCart` JSON / merge | Purchase |
| `AbandonedCart.status=recovered` | **P** (business) | DB row | Recovered cart |
| `evaluate_lifecycle_truth` result | **N** (shadow) | Not persisted | Observation only |
| `[PURCHASE LIFECYCLE CLOSED]` stdout/log | **P** (audit) | Logs | Purchase |

**Strongest closure bundle:** `purchase_truth_records` + cancelled schedule + `has_conversion_truth` true at wake.

**Weakest closure:** Reply PURCHASE or intelligence STOP with **no** truth row and **no** `stopped_converted` log — may block only until restart.

---

## 5. Source-of-truth map — who owns final truth?

There is **no single owner**. Use this precedence for **“what should win now?”** reconciliation:

```text
1. purchase_truth_records + has_conversion_truth     (purchase — durable)
2. RecoverySchedule terminal row per recovery_key   (scheduling — durable per row)
3. Latest CartRecoveryLog.status + full log set      (operations — can be stale as “latest”)
4. Behavioral JSON on AbandonedCart                   (merged hints — prune rules apply)
5. Dashboard phase_key / coarse                     (derived presentation)
6. API recovery_state on last cart-event              (ephemeral client contract)
7. lifecycle_intelligence decision                    (observation / gates — not persisted)
8. evaluate_lifecycle_truth                         (shadow canonical — not execution owner)
9. In-memory session flags                            (fast path only)
```

| Layer | Owns final truth for… | Does *not* own |
|-------|----------------------|----------------|
| **`purchase_truth_records`** | Verified purchase stop | Reply tone, return visits, send success |
| **`RecoverySchedule`** | Whether delayed worker should run | Merchant-facing narrative |
| **`CartRecoveryLog`** | Audit trail of what happened | Single current enum (use precedence) |
| **`AbandonedCart.status`** | Cart catalog lifecycle (`abandoned` / `recovered`) | Per-attempt send state |
| **`evaluate_lifecycle_truth`** | Canonical label for audits (shadow) | Execution |
| **`lifecycle_intelligence`** | Observe-time decision logging | Durable closure record |
| **`purchase_lifecycle_closure`** | Terminal flags + behavioral patch | Cross-process durability |
| **`cartflow_merchant_lifecycle` / clarity** | Merchant Arabic copy | Scheduling |
| **`cartflow_lifecycle_guard`** | Merge/prune diagnostics | Live writes |

**Practical rule for support:** Grep `[PURCHASE TRUTH]` → `[PURCHASE LIFECYCLE CLOSED]` → `[PURCHASE STOP]` → `[RECOVERY BLOCKED]` → latest `CartRecoveryLog` → `RecoverySchedule` row.

---

## 6. Verdict

### **PARTIAL** (not **NOT READY**, not **READY**)

**READY aspects**

- Documented terminal vocabulary across logs, schedules, purchase truth, and dashboard phases.
- Purchase path: durable stop + schedule cancel + conversion read chain (`tests/test_cartflow_purchase_truth_foundation_v1.py`, `tests/test_purchase_truth_lifecycle_v1.py`).
- Return and purchase gates at recovery wake (`stop_if_purchased`, `_is_user_converted`).
- Reply STOP / PURCHASE hooks and follow-up suppress paths (`tests/test_lifecycle_truth_completion_audit_v1.py`).
- Shadow canonical evaluator documents target precedence (`cartflow_lifecycle_truth_v1_examples.md`).

**PARTIAL gaps (block “complete closure truth”)**

1. **Distributed state** — no one table = “lifecycle complete.”
2. **Latest-log dashboard lie** — `queued` / `skipped_delay_gate` can display after terminal event if sort order wrong.
3. **Dual purchase paths** — truth ingest vs `stopped_converted` vs reply PURCHASE without truth row.
4. **Reply vs return precedence** differs between intelligence and canonical evaluator.
5. **`purchase_lifecycle_closure` not durable** alone (restart gap without purchase truth).
6. **`checkout_started`** not in unified lifecycle closure.
7. **`evaluate_lifecycle_truth` not wired to execution** — completion truth is operational, not single canonical runtime owner.
8. **Ignored** is non-terminal but can look “done” in UI — by design continues attempts.

**NOT READY would require:** systematic wrong sends after known terminal events in QA — **not** observed as systemic when purchase truth is ingested; gaps are **consistency / observability**, not total absence of stops.

### Upgrade path to **READY** (future, out of scope)

1. Single read model service (materialized `recovery_session_state`) fed by purchase truth + schedule + log rollup.
2. Dashboard `phase_key` from that read model, not raw latest log only.
3. Align `lifecycle_intelligence` precedence with `evaluate_lifecycle_truth` (reply vs return).
4. Reply PURCHASE always writes `purchase_truth_records` or explicit non-purchase terminal tier.
5. Wire canonical evaluator to dashboard API (or replace shadow with owner).

---

## 7. Code index

| Concern | Location |
|---------|----------|
| Terminal log statuses | `main.py` (persist sites), `services/cartflow_merchant_clarity.py` `LOG_LABELS` |
| Schedule terminal | `services/recovery_restart_survival.py` |
| Purchase stop | `services/cartflow_purchase_truth.stop_if_purchased` |
| Conversion read | `services/cartflow_session_truth.has_conversion_truth` |
| Closure memory | `services/purchase_lifecycle_closure` |
| Wake gate | `main._run_recovery_sequence_after_cart_abandoned_impl` |
| Dashboard phase | `main._normal_recovery_dashboard_phase_key`, `_normal_recovery_coarse_status` |
| Merchant truth builder | `services/merchant_recovery_lifecycle_truth.build_merchant_recovery_lifecycle_truth` |
| Canonical evaluator (shadow) | `services/cartflow_lifecycle_truth.evaluate_lifecycle_truth` |
| Intelligence (observe) | `services/lifecycle_intelligence.decide_lifecycle_recovery` |
| Precedence helpers | `services/cartflow_merchant_lifecycle_precedence` |
| Guard / conflicts | `services/cartflow_lifecycle_guard` |
| Session consistency | `services/cartflow_session_consistency` |

---

## 8. Reviewer checklist

- [ ] Spot-check 3 production sessions: purchase, return, reply — grep order in §5
- [ ] Confirm `RecoverySchedule` row after purchase is `cancelled`
- [ ] Confirm dashboard `phase_key` matches precedence for purchased carts
- [ ] Accept **PARTIAL** for v1 product messaging (“influence / stop” vs “legal closure”)
