# CartFlow Lifecycle Canonical Alias Map v1

**Date (UTC):** 2026-05-23  
**Scope:** Documentation only — prevents naming drift before Lifecycle Truth implementation.  
**Related:** `docs/cartflow_lifecycle_truth_audit_v1.md`

**Rules for this document:**

- **No renaming** of production strings.
- **No runtime changes.**
- **Canonical** = target abstract state for a future unified read model (aligns with `services/cartflow_lifecycle_guard.py`).

---

## 1. Canonical vocabulary (target)

| Canonical | Meaning (product) | Precedence rank (guard) |
|-----------|-------------------|-------------------------|
| `purchased` | Customer completed purchase; recovery must stop | 100 |
| `stopped` | Intentional or operational stop (manual, cap, template off) | 95 |
| `replied` | Customer replied on WhatsApp; follow-up suppressed / handoff | 88 |
| `returned` | Customer returned to site; anti-spam / no-send | 82 |
| `sent` | At least one recovery WhatsApp logged or in flight | 75 |
| `failed` | Send or provider failure | 70 |
| `duplicate_blocked` | Duplicate schedule/send prevented | 62 |
| `send_started` | Recovery claimed / dispatch in progress | 55 |
| `waiting` | Delay, queue, or gate not yet satisfied | 48–52 |
| `abandoned` | Cart abandoned; setup incomplete | 40 |
| `unknown` | Unmapped / missing signal | 0 |

Evidence: `cartflow_lifecycle_guard._PRECEDENCE` L37–50.

---

## 2. Alias map (alias → canonical → owner → active/legacy)

### 2.1 Purchased / converted

| Alias | Canonical | Owner module / surface | Active / legacy |
|-------|-----------|----------------------|-----------------|
| `purchase_detected` | `purchased` | `cartflow_purchase_truth` / `purchase_truth_records` | **ACTIVE** |
| `closed_purchase` | `purchased` | `purchase_lifecycle_closure` (`lifecycle_terminal_state`) | **ACTIVE** |
| `stopped_converted` | `purchased` | `CartRecoveryLog.status` (`main.py` conversion tail) | **ACTIVE** |
| `stopped_purchase` | `purchased` | Dashboard `phase_key` (`main._NORMAL_RECOVERY_PHASE_ORDER`) | **ACTIVE** |
| `recovery_complete` | `purchased` | Dashboard `phase_key` | **ACTIVE** (overlaps `stopped_purchase`) |
| `recovery_state=converted` | `purchased` | Cart-event API response (`main.py` L8757) | **ACTIVE** |
| `purchase_completed` | `purchased` | Lifecycle intelligence behavior; conversion payload | **ACTIVE** |
| `user_converted` | `purchased` | Purchase evidence extractor (`cartflow_purchase_truth`) | **ACTIVE** |
| `STATE_CONVERTED` | `purchased` | `cartflow_lifecycle_guard` abstract state | **ACTIVE** |
| `coarse=converted` | `purchased` | `_normal_recovery_coarse_status` | **ACTIVE** |
| `blocker_key=purchase_completed` | `purchased` | `cartflow_merchant_clarity` | **ACTIVE** |
| `_session_recovery_converted[recovery_key]` | `purchased` | In-memory session flag (`main.py` L2248) | **ACTIVE** (process-local) |
| `AbandonedCart.status=recovered` | `purchased` | ORM cart row | **ACTIVE** (weak / secondary) |
| `order_paid`, `checkout_completed`, `order_created`, `order_completed` | `purchased` | Purchase evidence events only | **ACTIVE** (ingest, not log status) |

### 2.2 Returned to site

| Alias | Canonical | Owner | Active / legacy |
|-------|-----------|-------|-----------------|
| `returned_to_site` | `returned` | `CartRecoveryLog` (`_DURABLE_RETURN_TO_SITE_LOG_STATUS`, `main.py` L2363) | **ACTIVE** |
| `skipped_anti_spam` | `returned` | `CartRecoveryLog` | **ACTIVE** |
| `customer_returned` | `returned` | Dashboard `phase_key` | **ACTIVE** |
| `user_returned` | `returned` | Blocker key / lifecycle intelligence reason | **ACTIVE** |
| `coarse=returned` | `returned` | `_normal_recovery_coarse_status` | **ACTIVE** |
| `STATE_RETURNED` | `returned` | `cartflow_lifecycle_guard` | **ACTIVE** |
| `_session_recovery_returned[recovery_key]` | `returned` | In-memory (`main.py` L2249) | **ACTIVE** (process-local) |
| `user_returned_to_site` | `returned` | Behavioral JSON (`cf_behavioral`) | **ACTIVE** |
| `customer_returned_to_site` | `returned` | Behavioral JSON | **ACTIVE** |

### 2.3 Replied / customer interaction

| Alias | Canonical | Owner | Active / legacy |
|-------|-----------|-------|-----------------|
| `skipped_followup_customer_replied` | `replied` | `CartRecoveryLog` / recovery sequence | **ACTIVE** |
| `skipped_user_rejected_help` | `replied` | `CartRecoveryLog` / WhatsApp queue | **ACTIVE** |
| `behavioral_replied` | `replied` | Dashboard `phase_key` | **ACTIVE** |
| `customer_replied` | `replied` | Behavioral flag / blocker | **ACTIVE** |
| `coarse=replied` | `replied` | `_normal_recovery_coarse_status` | **ACTIVE** |
| `STATE_REPLIED` | `replied` | `cartflow_lifecycle_guard` | **ACTIVE** |
| `customer_replied` (continuation_state) | `replied` | `cartflow_reply_intent_engine` | **ACTIVE** |
| `INTENT_STOP` / `INTENT_PURCHASE` (reply) | `replied` or `purchased` | `reply_intent_handling` | **ACTIVE** (intent splits purchase out) |

### 2.4 Sent

| Alias | Canonical | Owner | Active / legacy |
|-------|-----------|-------|-----------------|
| `mock_sent` | `sent` | `CartRecoveryLog` | **ACTIVE** |
| `sent_real` | `sent` | `CartRecoveryLog` / analytics | **ACTIVE** |
| `first_message_sent` | `sent` | Dashboard `phase_key` | **ACTIVE** |
| `reminder_sent` | `sent` | Dashboard `phase_key` | **ACTIVE** |
| `coarse=sent` | `sent` | `_normal_recovery_coarse_status` | **ACTIVE** |
| `STATE_SENT` | `sent` | `cartflow_lifecycle_guard` | **ACTIVE** |
| `recovery_state=sent` | `sent` | Cart-event API (`main.py` L8554) | **ACTIVE** |
| `_session_recovery_sent[recovery_key]` | `sent` | In-memory (`main.py` L2247) | **ACTIVE** (process-local) |
| `behavioral_link_clicked` | `sent` | Dashboard `phase_key` (click, not WA) | **ACTIVE** (maps to `clicked` coarse — related) |
| `coarse=clicked` | `sent` | Coarse bucket for link click | **ACTIVE** (UI nuance) |

### 2.5 Waiting / delay / queue

| Alias | Canonical | Owner | Active / legacy |
|-------|-----------|-------|-----------------|
| `queued` | `waiting` | `CartRecoveryLog` | **ACTIVE** |
| `skipped_delay_gate` | `waiting` | `CartRecoveryLog` | **ACTIVE** |
| `skipped_delay` | `waiting` | `CartRecoveryLog` | **LEGACY** (prefer `skipped_delay_gate`; guard maps both L200–201) |
| `pending_send` | `waiting` | Dashboard `phase_key` | **ACTIVE** |
| `pending_second_attempt` | `waiting` | Dashboard `phase_key` | **ACTIVE** |
| `coarse=pending` | `waiting` | `_normal_recovery_coarse_status` | **ACTIVE** |
| `STATE_WAITING_DELAY` / `STATE_QUEUED` | `waiting` | `cartflow_lifecycle_guard` | **ACTIVE** |
| `recovery_state=scheduled` | `waiting` | Cart-event API | **ACTIVE** |
| `RecoverySchedule.status=scheduled` | `waiting` | Durable scheduler | **ACTIVE** |
| `RecoverySchedule.status=running` | `waiting` | In-flight worker claim | **ACTIVE** (in progress) |
| `recovery_state=waiting_for_phone` | `waiting` | API (setup gate) | **ACTIVE** |
| `recovery_state=waiting_for_reason` | `waiting` | API (setup gate) | **ACTIVE** |
| `BEHAVIOR_DELAY_WAITING` | `waiting` | `lifecycle_intelligence` | **ACTIVE** |
| `decision=WAIT` | `waiting` | Lifecycle intelligence | **ACTIVE** |

### 2.6 Stopped (non-purchase)

| Alias | Canonical | Owner | Active / legacy |
|-------|-----------|-------|-----------------|
| `stopped_manual` | `stopped` | Dashboard `phase_key` | **ACTIVE** |
| `skipped_attempt_limit` | `stopped` | `CartRecoveryLog` | **ACTIVE** |
| `skipped_reason_template_disabled` | `stopped` | `CartRecoveryLog` | **ACTIVE** |
| `skipped_missing_reason_tag` | `stopped` | `CartRecoveryLog` / API | **ACTIVE** (setup — also `abandoned`) |
| `skipped_missing_phone` / `skipped_no_verified_phone` | `stopped` | `CartRecoveryLog` / API | **ACTIVE** (setup) |
| `skipped_missing_last_activity` | `stopped` | `CartRecoveryLog` | **ACTIVE** |
| `coarse=stopped` | `stopped` | Coarse bucket | **ACTIVE** |
| `STATE_STOPPED` | `stopped` | `cartflow_lifecycle_guard` | **ACTIVE** |
| `RecoverySchedule.status=cancelled` | `stopped` | Durable (incl. purchase cancel) | **ACTIVE** |
| `vip_manual_handling` | `stopped` | VIP path (normal automation off) | **ACTIVE** (lane-specific) |

### 2.7 Failed / duplicate

| Alias | Canonical | Owner | Active / legacy |
|-------|-----------|-------|-----------------|
| `whatsapp_failed` | `failed` | `CartRecoveryLog` / schedule | **ACTIVE** |
| `failed_retry` | `failed` | WhatsApp queue log | **ACTIVE** |
| `failed_final` | `failed` | WhatsApp queue terminal | **ACTIVE** |
| `skipped_duplicate` | `duplicate_blocked` | `CartRecoveryLog` / API | **ACTIVE** |
| `recovery_state=skipped_duplicate` | `duplicate_blocked` | Cart-event API | **ACTIVE** |
| `STATE_DUPLICATE_BLOCKED` | `duplicate_blocked` | `cartflow_lifecycle_guard` | **ACTIVE** |
| `_session_recovery_started` (claim) | `duplicate_blocked` | In-memory schedule claim | **ACTIVE** (related) |

### 2.8 Abandoned / unknown setup

| Alias | Canonical | Owner | Active / legacy |
|-------|-----------|-------|-----------------|
| `AbandonedCart.status=detected` | `abandoned` | ORM default | **ACTIVE** |
| `AbandonedCart.status=abandoned` | `abandoned` | ORM | **ACTIVE** |
| `blocked_missing_customer_phone` | `abandoned` | Dashboard phase | **ACTIVE** |
| `coarse=blocked` | `abandoned` | Coarse bucket | **ACTIVE** |
| `STATE_ABANDONED` | `abandoned` | Guard | **ACTIVE** |

---

## 3. Cross-alias notes (do not merge in code yet)

| Topic | Guidance |
|-------|----------|
| `recovery_complete` vs `stopped_purchase` | Both map to `purchased` for truth; UI may show different Arabic copy. |
| `skipped_delay` vs `skipped_delay_gate` | Prefer documenting `skipped_delay_gate`; keep `skipped_delay` as **LEGACY** alias. |
| `mock_sent` vs `sent_real` | Both `sent`; sandbox vs production provider path. |
| `scheduled` (API) vs `queued` (log) vs `RecoverySchedule.scheduled` | All `waiting`; different layers. |
| Reply **HANDOFF** vs log `skipped_followup` | Same customer moment; different log vocabulary (see completion audit). |

---

## 4. Owner quick reference

| Owner | Canonical states primarily expressed |
|-------|--------------------------------------|
| `cartflow_purchase_truth` | `purchased` |
| `purchase_lifecycle_closure` | `purchased` |
| `lifecycle_intelligence` | `purchased`, `returned`, `replied`, `waiting`, `unknown` |
| `CartRecoveryLog` | All (append-only history) |
| `RecoverySchedule` | `waiting`, `stopped`, `failed` |
| `main` session dicts | `purchased`, `sent`, `returned` (+ claim keys) |
| Dashboard `phase_key` / `coarse` | Presentation aliases |
| `cartflow_lifecycle_guard` | Normalization for diagnostics |

---

## 5. Verification

- Mapped aliases traced to `services/cartflow_lifecycle_guard.py` (`map_recovery_log_status_to_state`, `map_dashboard_phase_to_state`) and `docs/cartflow_lifecycle_truth_audit_v1.md` §2.
- No production enum was modified.

**After review:** commit `docs: add lifecycle hygiene audit v1` — push only when approved.
