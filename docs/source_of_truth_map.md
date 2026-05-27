# CartFlow Source-of-Truth Map

**Date (UTC):** 2026-05-27  
**Scope:** Read-only architecture freeze. No runtime behavior changes.  
**Goal:** A new engineer can explain any cart row state in under five minutes by following this map.

---

## How to read this document

For each concept we document:

| Field | Meaning |
|-------|---------|
| **SOURCE** | Authoritative durable store or derivation rule |
| **WRITES** | Who creates or mutates it |
| **READS** | Who consumes it for product decisions |
| **OWNER** | Module that should own future changes |
| **TERMINAL** | Whether this value can end a lifecycle (stop sends / close row) |
| **CANONICAL?** | Whether this is the preferred truth for new code (`yes` / `no` / `partial`) |

**Identity rule (frozen):** `recovery_key = {store_slug}:{session_part}` where `session_part` = `session_id` → else `cart_id` → else cart fingerprint (`main._recovery_key_from_payload`).

---

## 1. `session_id`

| | |
|--|--|
| **SOURCE** | Browser `sessionStorage` key `cartflow_recovery_session_id`; mirrored in `cartflow_recovery_return_state_v1` (localStorage) |
| **WRITES** | `static/cart_abandon_tracking.js` (`getRecoverySessionId`, `startNewMerchantTestLifecycle`); server `demo_store_reset_demo` / `demo_pi_fresh_session`; test-widget identity contract reset (`main._merchant_test_widget_identity_contract`) |
| **READS** | All `POST /api/cart-event` payloads; `POST /api/cartflow/reason`; `POST /api/conversion`; `AbandonedCart.recovery_session_id`; `RecoverySchedule.session_id`; `CartRecoveryLog.session_id` |
| **OWNER** | Client: `cart_abandon_tracking.js`; Server ingest: `main.api_cart_event` |
| **TERMINAL** | No (identity only) |
| **CANONICAL?** | **yes** (client-origin session scope; server trusts payload after merchant-auth coercion) |

---

## 2. `cart_id`

| | |
|--|--|
| **SOURCE** | Browser `sessionStorage` `cartflow_cart_event_id`; platform `zid_cart_id` on `AbandonedCart`; synthetic `cf_w_*` / `cf_tw_*` when missing |
| **WRITES** | `cart_abandon_tracking.js`; cart-event upsert (`AbandonedCart.persist_from_abandon` paths in `main`); test-widget reset |
| **READS** | VIP thresholds; dashboard row merge; `CartRecoveryLog.cart_id`; purchase truth ingest; session-truth log fallback |
| **OWNER** | `main` abandon upsert + `cart_abandon_tracking.js` |
| **TERMINAL** | No |
| **CANONICAL?** | **partial** — row merge uses `cart_id`; **recovery scheduling keys off `session_id` first** (see `recovery_key`) |

---

## 3. `recovery_key`

| | |
|--|--|
| **SOURCE** | Derived: `{store_slug}:{session_part}` (`main._recovery_key_from_payload`) |
| **WRITES** | Implicit on every cart-event, schedule persist, timeline write, purchase ingest, archive row |
| **READS** | Timeline, purchase truth, archive, session-truth cache, dashboard resolve (`merchant_dashboard_recovery_resolve_v1`), classifier inputs |
| **OWNER** | `main` + `services/recovery_store_context.reconcile_recovery_identity` |
| **TERMINAL** | No (composite key) |
| **CANONICAL?** | **yes** — **primary correlation ID** for one recovery lifecycle |

---

## 4. `reason_tag`

| | |
|--|--|
| **SOURCE** | `CartRecoveryReason.reason` (latest per `store_slug` + `session_id`); widget payload fields `reason_tag` / `abandon_reason_tag`; `AbandonmentReasonLog` |
| **WRITES** | `POST /api/cartflow/reason` (`routes/cartflow.py`); `POST /api/cart-recovery/reason`; phone-capture preserve logic (`recovery_reason_preserve.py`); demo `fresh=1` seeds |
| **READS** | Recovery message templates; continuation engine (`cartflow_reply_intent_engine`); dashboard suggestion copy; `[CONTINUATION TRACE]` |
| **OWNER** | `routes/cartflow.py` + `CartRecoveryReason` model |
| **TERMINAL** | No (steers content, not lifecycle end) |
| **CANONICAL?** | **yes** for **objection / template selection**; not for send/reply/purchase proof |

**Note:** `human_support` is **handoff-only** — does not re-arm recovery schedule (`assist-handoff` path).

---

## 5. Timeline status

| | |
|--|--|
| **SOURCE** | Table `recovery_truth_timeline_events` (`RecoveryTruthTimelineEvent`) |
| **WRITES** | `services/recovery_truth_timeline_v1.record_recovery_truth_event` — callers: schedule persist, delay/send hooks in `main`, WhatsApp delivery webhook, reply transition engine, continuation engine |
| **READS** | `GET /dev/recovery-truth`; `merchant_cart_row_classifier` (reply/engaged/sent proof); `customer_lifecycle_states_v1`; test-widget identity reusability |
| **OWNER** | `services/recovery_truth_timeline_v1.py` |
| **TERMINAL** | **partial** — `provider_sent` + `customer_reply` + `continuation_started` are **progression**; purchase/archive are **terminal elsewhere** |

**Canonical timeline chain (frozen order):**  
`scheduled` → `delay_started` → `before_send` → `provider_queued` → `provider_sent` → `webhook_delivered` → `customer_reply` → `continuation_started`

| Status | CANONICAL for dashboard? |
|--------|-------------------------|
| `provider_sent` | **yes** — «تم الإرسال» requires this (or durable log fallback in classifier) |
| `customer_reply` | **yes** — «رد العميل» |
| `continuation_started` | **yes** — «تفاعل العميل — أرسل النظام متابعة» |
| `scheduled` / `delay_started` | **yes** — waiting / pre-send |

---

## 6. Dashboard state (merchant-facing label)

Two layers run on every normal cart row (`main._build_merchant_normal_cart_row_payload`):

### Layer A — Tab bucket (`merchant_cart_row_classifier`)

| | |
|--|--|
| **SOURCE** | Computed per row — **not stored** |
| **WRITES** | `classify_merchant_cart_row` only |
| **READS** | `merchant_dashboard_lazy.js` filters (الكل / بانتظار / تم الإرسال / …) |
| **OWNER** | `services/merchant_cart_row_classifier.py` |
| **TERMINAL** | No |
| **CANONICAL?** | **yes** for **tab placement** |

### Layer B — Lifecycle v1 (`customer_lifecycle_states_v1`)

| | |
|--|--|
| **SOURCE** | Computed per row — **not stored** |
| **WRITES** | `classify_customer_lifecycle_state_v1` / `attach_customer_lifecycle_state_v1` |
| **READS** | Status chip + explanation block in `merchant_dashboard_lazy.js` |
| **OWNER** | `services/customer_lifecycle_states_v1.py` |
| **TERMINAL** | No |
| **CANONICAL?** | **yes** for **status chip + narrative** (overrides `merchant_status_label_ar` from layer A) |

### Layer C — Legacy enrichment (`merchant_recovery_lifecycle_truth`)

| | |
|--|--|
| **SOURCE** | Computed debug/explanation fields from logs + behavioral |
| **WRITES** | `attach_merchant_recovery_lifecycle_truth` |
| **READS** | Dashboard detail panels, diagnostics |
| **OWNER** | `services/merchant_recovery_lifecycle_truth.py` |
| **TERMINAL** | No |
| **CANONICAL?** | **no** — supplementary; do not add new product gates here |

---

## 7. Archive state

| | |
|--|--|
| **SOURCE** | Table `merchant_cart_lifecycle_archives` (`MerchantCartLifecycleArchive.is_archived`) |
| **WRITES** | `POST /api/dashboard/cart-lifecycle/archive` / `reopen` → `merchant_cart_lifecycle_archive_v1` |
| **READS** | `customer_lifecycle_states_v1` (`STATE_ARCHIVED`); dashboard archive buttons |
| **OWNER** | `services/merchant_cart_lifecycle_archive_v1.py` |
| **TERMINAL** | **yes** (merchant view — row hidden from active work; does not delete timeline) |
| **CANONICAL?** | **yes** for **merchant archive UX** |

Auto-archive path: exhausted templates + no reply (lifecycle classifier) — persistence still manual/auto via same table.

---

## 8. Return state

| | |
|--|--|
| **SOURCE** | **Multi-source** (see precedence) |
| **WRITES** | `CartRecoveryLog.status` `returned_to_site`; `AbandonedCart.raw_payload.cf_behavioral`; in-memory `_session_recovery_returned`; `lifecycle_closure_records_v1` |
| **READS** | Send guards (`whatsapp_send`, `cartflow_lifecycle_guard`); classifiers (`_return_to_site_truth`); lifecycle v1 `STATE_RETURN_TO_SITE` |
| **OWNER** | `main` return hooks + `behavioral_recovery/user_return.py` |
| **TERMINAL** | **partial** — suppresses outbound WhatsApp; not purchase terminal |
| **CANONICAL?** | **partial** — durable log + behavioral for **detection**; **timeline `customer_reply` blocks return-only classification** |

**Client paths:** `cartflow_return_tracker.js` → `POST /api/cart-event`; commercial `cart_state_sync` add/remove in `main.api_cart_event`.

---

## 9. Purchase state

| | |
|--|--|
| **SOURCE** | Table `purchase_truth_records` (`services/cartflow_purchase_truth.py`) |
| **WRITES** | `POST /api/conversion`; Zid webhook ingest; reply-claim ingest (lower confidence); cart-event `purchase_completed` |
| **READS** | `has_purchase(recovery_key)`; `has_conversion_truth`; classifier `PRIMARY_RECOVERED`; lifecycle `STATE_COMPLETED` |
| **OWNER** | `services/cartflow_purchase_truth.py` + `services/purchase_truth.py` facade |
| **TERMINAL** | **yes** — stops recovery (precedence rank 100 in guard) |
| **CANONICAL?** | **yes** |

---

## 10. Reply state

| | |
|--|--|
| **SOURCE** | Timeline `customer_reply` + `continuation_started` (**preferred**); secondary: `CartRecoveryLog` skipped statuses; `cf_behavioral` |
| **WRITES** | Inbound WhatsApp → `recovery_transition_engine` + `cartflow_reply_intent_engine` |
| **READS** | Classifier buckets `customer_reply` / `customer_engaged`; lifecycle v1; continuation trace dashboard |
| **OWNER** | `services/recovery_transition_engine` + `cartflow_reply_intent_engine` |
| **TERMINAL** | **partial** — stops automated sequence; may still allow handoff |
| **CANONICAL?** | **yes** when proven in **timeline**; **no** when behavioral-only |

---

## 11. Cache state (session truth)

| | |
|--|--|
| **SOURCE** | In-process dicts: `_session_recovery_sent`, `_session_recovery_converted`, `_session_recovery_returned` (`main.py`) |
| **WRITES** | Send completion, conversion marks, purchase closure rehydrate; cleared on test-widget identity reset |
| **READS** | `services/cartflow_session_truth.has_sent_truth` / `has_conversion_truth` (cache-first, then DB fallback) |
| **OWNER** | `services/cartflow_session_truth.py` + `main` dict mutation sites |
| **TERMINAL** | **no** (optimization layer) |
| **CANONICAL?** | **no** — **cache only**; durable truth = timeline + `CartRecoveryLog` + `purchase_truth_records` |

**Log signature:** `[SESSION TRUTH CACHE HIT]` / `CACHE MISS` / `DB FALLBACK` / `REHYDRATED`.

**Risk:** Multi-worker or restart → cache cold; DB fallback must remain correct (already implemented).

---

## Part 4 — Dashboard label → source matrix

**Rule:** If lifecycle v1 attached a label, **trust `customer_lifecycle_label_ar`**. Else trust `merchant_status_label_ar` from classifier.

| Dashboard label (AR) | Tab filter | Primary source | Secondary / fallback |
|----------------------|------------|----------------|----------------------|
| بانتظار الإرسال | waiting | Classifier `PRIMARY_WAITING`; lifecycle `waiting_first_send` | `RecoverySchedule` scheduled; timeline `scheduled`/`delay_started`; phase `pending_send` |
| تم الإرسال — بانتظار تفاعل العميل | sent | Classifier `PRIMARY_SENT` | Timeline `provider_sent` OR logs `mock_sent`/`sent_real`; **not** cache alone |
| بانتظار تفاعل العميل | sent (lifecycle chip) | Lifecycle `waiting_customer_reply` | Sent proven + no timeline reply |
| رد العميل | attention | Classifier `PRIMARY_CUSTOMER_REPLY` | **Timeline `customer_reply` only** |
| تفاعل العميل — أرسل النظام متابعة | attention | Classifier `PRIMARY_CUSTOMER_ENGAGED` | Timeline `customer_reply` + `continuation_started` |
| عاد العميل للموقع — نراقب هل يكمل الطلب | sent tab | Classifier `PRIMARY_RETURN_TO_SITE` | Logs `returned_to_site` / behavioral return; **blocked if timeline reply** |
| يحتاج متابعة | attention | Classifier `PRIMARY_NEEDS_FOLLOWUP` | Intervention logs, VIP manual, failed sends |
| تم الاسترجاع | recovered | Classifier `PRIMARY_RECOVERED` | `has_purchase(rk)` OR `AbandonedCart.status=recovered` |
| لا يوجد رقم للتواصل | nophone | Classifier `PRIMARY_NO_PHONE` | Phone resolution helpers |
| بانتظار المتابعة التالية | sent (lifecycle) | Lifecycle `waiting_next_scheduled` | `RecoverySchedule.due_at` future + ignored/help rejected |
| تحتاج تدخل | attention | Lifecycle `needs_intervention` | Failed WhatsApp, VIP manual provider issue |
| تمت الاستعادة / تم الشراء | recovered | Lifecycle `completed` | Purchase truth or recovered status |
| ✓ مؤرشفة | all (faded) | Lifecycle `archived` + `is_archived_visual` | `MerchantCartLifecycleArchive` table |

**Not used for labels:** `_session_recovery_sent` alone, demo panel text, `lifecycle_intelligence` shadow labels (observe-only).

---

## Quick “explain this row” checklist (< 5 min)

1. Read `recovery_key` on the row payload.
2. `GET /dev/recovery-truth?recovery_key=...` → timeline statuses.
3. Check `has_purchase` / archive flag / latest `CartRecoveryLog` statuses.
4. Compare timeline to `customer_lifecycle_state` on the same API row (`GET /api/dashboard/normal-carts`).
5. If mismatch: see `docs/lifecycle_truth_contract.md` forbidden transitions and `docs/active_vs_legacy.md` for legacy paths.

**Related audits:** `docs/cartflow_lifecycle_alias_map.md`, `docs/cartflow_purchase_truth_audit_v1.md`, `docs/cartflow_session_truth_audit.md`.
