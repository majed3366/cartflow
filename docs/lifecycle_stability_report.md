# CartFlow Lifecycle Stabilization — Phase 0 Report

**Date (UTC):** 2026-05-27  
**Scope:** Read-only audit. No code changes, deletions, or refactors.  
**Inputs:** `candidate_remove.md`, `docs/lifecycle_truth_contract.md`, `docs/source_of_truth_map.md`, `docs/dependency_map.md`, `docs/active_vs_legacy.md`, plus spot-checks on `customer_lifecycle_states_v1.py`, `merchant_cart_row_classifier.py`, `recovery_truth_timeline_v1.py`, `merchant_dashboard_lazy.js`.

**Phase 0 goal:** Pause features. Stabilize **one** canonical customer lifecycle end-to-end before cleanup.

---

## Executive summary

| Area | Verdict |
|------|---------|
| Canonical path (widget → schedule → send → branches) | **Documented and mostly aligned** |
| Dashboard chip (`customer_lifecycle_label_ar`) | **Merchant-readable in Arabic** — primary UX truth |
| Tab filters vs chip | **Unstable** — same row can sit in «تم الإرسال» tab while chip says «عاد العميل للموقع» |
| Multi-layer labels (classifier + lifecycle + phase) | **Risk** — engineers need `recovery_key`; merchants should not |
| Forbidden transitions F1–F10 | **Mostly PASS**; cache-on-dashboard and schedule-after-purchase remain **RISK** |
| 10-second merchant explanation (no logs) | **Possible for ~70% of chips**; **unstable** for «نشطة», tab mismatch, and «تم الإرسال» vs «بانتظار تفاعل» |

**Recommendation for Phase 1 (future, not this task):** Single read model = lifecycle v1 only; tab bucket derived from `customer_lifecycle_state` key, not parallel classifier precedence.

---

## PART 1 — Candidate Remove Summary (read-only)

Sourced from `candidate_remove.md`. **No deletions performed.**

### SAFE TO REMOVE

- `GET /demo/cart` (alias) — after analytics verify
- `POST /dev/cartflow-delay-test`
- `cartflowFreshSessionForDelayTest` (`cart_abandon_tracking.js`) — DevTools-only
- `main._NORMAL_RECOVERY_PHASE_ORDER` — display-only; lifecycle v1 owns chips
- `skipped_delay` log alias (prefer `skipped_delay_gate`)
- Classifier `merchant_status_label_ar` when lifecycle v1 always attached (dead if JS only reads lifecycle fields)
- Duplicate e2e tests for same classifier behavior — merge in dedicated PR
- Untracked `scripts/_patch_*.py` — not product path; do not commit

### NEEDS REVIEW

- `GET /dev/widget-test`, `/dev/widget-test/cart`
- `GET /demo/cartflow/*` (`routes/demo_panel.py`)
- Bulk `GET /dev/*` in `main.py`
- `GET /api/recover/r`
- `widget_loader.js` legacy branch (`__CARTFLOW_ALLOW_LEGACY_WIDGET`)
- `cartflow_widget_runtime/cartflow_widget_legacy_bridge.js`
- `static/cartflow_dashboard_messages.js`
- `demo_pi_fresh` block in `demo_store.html`
- `services/demo_pi_fresh_session.py`
- `services/cartflow_lifecycle_truth.py` (shadow compare)
- `services/lifecycle_intelligence.py` observe paths
- `services/merchant_recovery_lifecycle_truth.py` (duplicate enrichment)
- `_normal_recovery_coarse_status` / exposed `coarse` fields
- Timeline statuses outside `CANONICAL_ORDER` (historical DB rows)
- VIP-only `CartRecoveryLog` statuses
- `merchant_status_label_ar` on VIP rows without lifecycle attach
- Duplicate filter logic: `merchant_dashboard_lazy.js` vs classifier `visible_tabs`
- `reset_demo=1` without `merchant_activation`
- Tests reading `cartflow_widget.js`; `test_abandonment_reason_behavior_final` legacy sections; `test_cartflow_lifecycle_truth_v1.py` shadow tests
- `services/cartflow_identity.py`, `services/decision_engine.py`, `static/merchant_trigger_templates.js`

### DO NOT TOUCH

- `static/cartflow_widget.js` (until embed migration + V2 parity)
- `POST /api/cart-recovery/reason` (`routes/cart_recovery_reason.py`) — unknown external callers
- Duplicate `postReason` in legacy widget (parity required before monolith removal)
- `store_slug=default` in `coerce_cart_event_store_slug` — last-resort; merchant tests must avoid
- Public `demo` / `demo2` sandbox (non-activation)
- **`recovery_truth_timeline_v1.py`**
- **`customer_lifecycle_states_v1.py`**
- **`merchant_cart_row_classifier.py`** (until tab logic merged into lifecycle)
- **`merchant_cart_lifecycle_archive_v1.py`**
- **`cartflow_session_truth.py`** + in-memory `_session_recovery_*` (until send gates use timeline-only)
- **`merchant_test_widget_store_v1.py`** + test-widget identity contract in `main.py`

---

## PART 2 — Lifecycle Acceptance Path

**Frozen flow under test:**

```
Customer enters → Cart added → Reason selected → Recovery scheduled
→ Message sent → (A|B|C|D) → Dashboard ONE correct truth
```

**Merchant-facing chip:** `customer_lifecycle_label_ar` (lifecycle v1 overrides classifier on normal carts).  
**Tab filter:** `merchant_cart_bucket` from classifier — **can disagree with chip** (documented instability).

### Step 0 — Customer enters

| Field | Value |
|-------|--------|
| **Expected timeline** | (none) |
| **Expected dashboard label** | «السلة نشطة» (`active`) if row visible before reason/send |
| **Expected next action** | System monitors; widget may prompt |
| **Terminal?** | no |

**Stability:** **Unstable** — «نشطة» is vague; merchant cannot infer send/reason state without opening detail.

---

### Step 1 — Cart added

| Field | Value |
|-------|--------|
| **Expected timeline** | (none required); may later get `scheduled` after reason |
| **Expected dashboard label** | «السلة نشطة» or «بانتظار الإرسال» if abandon/schedule started |
| **Expected next action** | Choose reason / capture phone |
| **Terminal?** | no |

**Writes:** `POST /api/cart-event` (`cart_state_sync`, `cart_abandoned`).

---

### Step 2 — Reason selected

| Field | Value |
|-------|--------|
| **Expected timeline** | `scheduled` (on durable schedule persist) |
| **Expected dashboard label** | «بانتظار الإرسال» (`waiting_first_send`) |
| **Expected next action** | Wait for delay; ensure phone if missing |
| **Terminal?** | no |

**Writes:** `POST /api/cartflow/reason` → `CartRecoveryReason` → schedule arm (except `human_support` handoff-only).

---

### Step 3 — Recovery scheduled

| Field | Value |
|-------|--------|
| **Expected timeline** | `scheduled` → `delay_started` (when delay worker runs) |
| **Expected dashboard label** | «بانتظار الإرسال» |
| **Expected next action** | Automatic send at `RecoverySchedule.due_at` |
| **Terminal?** | no |

**Source:** `RecoverySchedule` + timeline; not cache.

---

### Step 4 — Message sent

| Field | Value |
|-------|--------|
| **Expected timeline** | `before_send` → `provider_queued` → `provider_sent` (+ optional `webhook_delivered`) |
| **Expected dashboard label** | «بانتظار تفاعل العميل» (`waiting_customer_reply`) — lifecycle; tab may show «تم الإرسال — بانتظار تفاعل العميل» (classifier `sent`) |
| **Expected next action** | Wait for customer |
| **Terminal?** | no |

**Proof:** `provider_send_proven` = timeline `provider_sent` **or** `CartRecoveryLog` `mock_sent`/`sent_real` (not session cache).

---

### Branch A — Customer returns (site only, no WhatsApp reply)

| Field | Value |
|-------|--------|
| **Expected timeline** | (no `customer_reply`) |
| **Expected dashboard label** | «عاد العميل للموقع — نراقب هل يكمل الطلب» (`return_to_site`) |
| **Expected next action** | Pause/suppress spam; watch checkout |
| **Terminal?** | no |

**Durable:** `CartRecoveryLog.returned_to_site` + behavioral flags. **Blocked:** must not show «رد العميل» or «تفاعل العميل» (code: `_return_to_site_detected` returns false if `customer_reply_proven`).

**Tab instability:** Row often appears under **Sent** tab while chip says return — merchant may be confused in <10s without training.

---

### Branch B — Customer replies (WhatsApp)

| Field | Value |
|-------|--------|
| **Expected timeline** | `customer_reply` → optional `continuation_started` |
| **Expected dashboard label** | «رد العميل»; if continuation sent: «تفاعل العميل — أرسل النظام متابعة» |
| **Expected next action** | Automated continuation or merchant review |
| **Terminal?** | no |

**Proof:** Timeline-only for reply (`customer_reply_proven` ignores behavioral).

---

### Branch C — Customer ignores (next template pending)

| Field | Value |
|-------|--------|
| **Expected timeline** | `provider_sent` (no `customer_reply`) |
| **Expected dashboard label** | «بانتظار المتابعة التالية» + line «المتابعة القادمة بعد: X» (`waiting_next_scheduled`) |
| **Expected next action** | Second message at schedule |
| **Terminal?** | no |

**Conditions:** sent proven + ignored phase + future `due_at` + templates remaining.

---

### Branch C′ — Customer ignores (templates exhausted)

| Field | Value |
|-------|--------|
| **Expected timeline** | `provider_sent` only |
| **Expected dashboard label** | «مؤرشفة» (auto-exhaust display) or archive prompt — **not** «مغلق» |
| **Expected next action** | Reopen or leave in history |
| **Terminal?** | **yes** (automation stopped) |

**Note:** Display archive without merchant click uses lifecycle `STATE_ARCHIVED` copy; DB archive row may still be separate — **ambiguity** (see Part 3).

---

### Branch D — Customer purchases

| Field | Value |
|-------|--------|
| **Expected timeline** | (purchase does not require timeline row) |
| **Expected dashboard label** | «تم الشراء» or «تمت الاستعادة» (`completed`) |
| **Expected next action** | None (automation stopped) |
| **Terminal?** | **yes** |

**Source:** `purchase_truth_records` (`has_purchase`) — canonical.

---

### Branch E — Merchant archives (overlay, any non-terminal state)

| Field | Value |
|-------|--------|
| **Expected timeline** | Unchanged (history preserved) |
| **Expected dashboard label** | «✓ مؤرشفة» (compact archived visual) |
| **Expected next action** | «إعادة فتح» only |
| **Terminal?** | **yes** (operational queue) |

**Source:** `merchant_cart_lifecycle_archives` table.

---

## PART 3 — Forbidden Transition Audit

Contract: `docs/lifecycle_truth_contract.md` §4 (F1–F10) and simplified checks requested.

| Check | Contract ref | Result | Evidence / notes |
|-------|----------------|--------|------------------|
| **return ≠ reply** | F1, F10 | **PASS** | `customer_lifecycle_states_v1._return_to_site_detected` and `merchant_cart_row_classifier._return_to_site_truth` bail out when `customer_reply_proven(rk)`. Tests: `test_customer_lifecycle_states_v1`, `test_merchant_cart_row_classifier_e2e`. |
| **cache ≠ sent** (dashboard) | F3 | **PASS** | `provider_send_proven` uses timeline + log statuses + `sent_count`; **does not** read `_session_recovery_sent`. Cache only in `has_sent_truth` for **send gates**, not chip. |
| **cache ≠ sent** (scheduling) | F3, F7 | **RISK** | `has_sent_truth` cache-first can block duplicate schedule paths; after restart cache cold → DB fallback. Wrong-worker cache hit could affect **automation**, not chip. |
| **archive ≠ completed** | F5 + user check | **RISK** | Archive is **overlay** — merchant can archive active sent row (not purchased). Exhausted-without-reply shows «مؤرشفة» in lifecycle **without** requiring `MerchantCartLifecycleArchive` row. Two meanings of «archived». |
| **reply ≠ purchase** | precedence | **PASS** | Purchase checked before reply in lifecycle classify order; `has_purchase` terminal. |
| **sent ≠ waiting** | user check | **RISK** | Product copy overload: classifier «تم الإرسال — بانتظار تفاعل العميل» vs lifecycle «بانتظار تفاعل العميل» vs contract `sent` vs `waiting_send`. Same row, different strings — merchant may think state changed when only layer changed. |
| **purchased + active schedule** | F4 | **RISK** | Guards exist (`has_conversion_truth`, purchase ingest); not re-verified in runtime this audit — treat until E2E proof in Phase 1. |
| **continuation without reply** | F9 | **RISK** | Depends on `cartflow_reply_intent_engine` always writing `customer_reply` before `continuation_started`. |
| **test identity reuse** | F6 | **PASS** | `main._merchant_test_widget_identity_contract` + client reset (recent commit). |
| **demo slug on activation** | F8 | **PASS** | `coerce_cart_event_store_slug` + activation resolver. |
| **archived full active copy** | F5 | **PASS** | Archive UX collapses explanation (`customer_lifecycle_is_archived_visual`). |

### F1–F10 summary table

| ID | Result |
|----|--------|
| F1 | **PASS** |
| F2 | **PASS** (dashboard) |
| F3 | **PASS** (dashboard) / **RISK** (gates) |
| F4 | **RISK** |
| F5 | **PASS** |
| F6 | **PASS** |
| F7 | **RISK** |
| F8 | **PASS** |
| F9 | **RISK** |
| F10 | **PASS** |

---

## PART 4 — Dashboard Truth Verification

**UI rule (frozen):** Status chip = `customer_lifecycle_label_ar` first (`merchant_dashboard_lazy.js`).  
**Tab** = `merchant_cart_bucket` from classifier — listed where different.

| Chip (merchant sees) | Source | Ambiguity? |
|----------------------|--------|------------|
| **Waiting send** — «بانتظار الإرسال» | **Lifecycle** `waiting_first_send` | **Low** — timeline `scheduled`/`delay_started` or phase `pending_send`; classifier tab `waiting` usually aligns. |
| **Sent** — «تم الإرسال — بانتظار تفاعل العميل» | **Classifier** label when lifecycle is `waiting_customer_reply` but attach sets lifecycle label to «بانتظار تفاعل العميل» | **Yes** — two Arabic strings for same phase; merchant training: trust **chip**, not tab header alone. |
| **Sent (lifecycle nuance)** — «بانتظار تفاعل العميل» | **Lifecycle** `waiting_customer_reply` + **timeline/logs** `provider_sent` | **Medium** — sounds like «waiting» not «sent»; contract `sent` vs copy mismatch. |
| **Returned** — «عاد العميل للموقع — نراقب هل يكمل الطلب» | **Lifecycle** `return_to_site` + **logs** `returned_to_site` / **behavioral** return flags; **not** timeline reply | **High tab ambiguity** — classifier bucket `return_to_site` maps to **Sent tab** (`UI_FILTER_SENT`). Merchant sees «sent» tab + «returned» chip. |
| **Replied** — «رد العميل» | **Timeline** `customer_reply` only | **Low** |
| **Engaged** — «تفاعل العميل — أرسل النظام متابعة» | **Timeline** `customer_reply` + `continuation_started` | **Low** |
| **Waiting next** — «بانتظار المتابعة التالية» (+ ETA line) | **Lifecycle** `waiting_next_scheduled` + **DB** `RecoverySchedule.due_at` | **Low** — ETA requires reading second line; still understandable <10s. |
| **Purchased** — «تم الشراء» / «تمت الاستعادة» | **DB** `purchase_truth_records` + lifecycle `completed` | **Low** |
| **Archived** — «✓ مؤرشفة» | **DB** `merchant_cart_lifecycle_archives` + lifecycle `archived` visual | **Medium** — exhausted auto-label also uses archived copy without DB row. |
| **Active** — «السلة نشطة» | **Lifecycle** fallback `active` | **Unstable** — non-specific; merchant cannot explain journey step. |
| **Needs intervention** — «تحتاج تدخل» | **Lifecycle** + **logs** failed/VIP | **Medium** — clear urgency, unclear cause without detail block. |

### Source type matrix (requested)

| Chip family | timeline? | cache? | classifier? | behavioral? | DB? |
|-------------|-----------|--------|---------------|-------------|-----|
| Waiting send | yes | no | yes (tab) | no | schedule |
| Sent / waiting reply | yes | no | yes (tab) | no | logs |
| Returned | no* | no | yes (tab) | yes | logs |
| Replied / engaged | yes | no | yes (bucket) | no** | no |
| Waiting next | partial | no | no | no | schedule |
| Purchased | no | no | yes (tab) | no | purchase_truth |
| Archived | no | no | no | no | archive table |

\*Return is not a timeline status today.  
\*\*`customer_reply_proven` explicitly deletes behavioral parameter.

**Cache:** Not used for any chip label. **Do not explain dashboard from `[SESSION TRUTH CACHE HIT]` logs.**

---

## Merchant 10-second explanation test (no logs, no Railway, no recovery_key)

| Question | Can merchant answer from chip alone? |
|----------|--------------------------------------|
| «هل أُرسلت رسالة؟» | **Yes** if chip says بانتظار تفاعل / تفاعل / رد / متابعة قادمة |
| «هل رد العميل؟» | **Yes** if «رد العميل» or «تفاعل العميل» |
| «هل اشترى؟» | **Yes** if «تم الشراء» / «تمت الاستعادة» |
| «هل عاد للموقع فقط؟» | **Yes** if return chip — **but** Sent tab contradicts without training |
| «هل انتهت المتابعة؟» | **Partial** — «مؤرشفة» vs purchased both look «done» |
| «ما الخطوة التالية؟» | **Yes** if explanation block visible — **No** if merchant only glances at chip during archive compact mode |
| «أين السلة في الرحلة؟» for «نشطة» | **No** — **unstable** |

**Overall:** **Stable enough** for reply/purchase/send-waiting; **unstable** for return+tab combo, active fallback, and dual «archived» meanings.

---

## Phase 0 conclusions (no code)

1. **Do not start cleanup** until tab bucket is derived from `customer_lifecycle_state` (or documented merchant training for return+sent tab).
2. **Do not remove** classifier until tabs are migrated — **NEEDS REVIEW** items stay queued.
3. **Phase 1 stabilization target (future):** One writer (timeline) + one reader (lifecycle v1) + tab from lifecycle key; session cache send-gates only.
4. **Acceptance path B/C/D** are the best stabilized branches; **A (return)** and **active** need UX/copy freeze, not more classifier patches.

---

## References

- `docs/source_of_truth_map.md`
- `docs/lifecycle_truth_contract.md`
- `docs/dependency_map.md`
- `docs/active_vs_legacy.md`
- `candidate_remove.md`

---

**Report type:** Phase 0 stabilization audit only.  
**Next commit message:** `docs: add lifecycle stability report before cleanup`
