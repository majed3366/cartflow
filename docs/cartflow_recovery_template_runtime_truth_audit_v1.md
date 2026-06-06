# Recovery Template Runtime Truth Audit v1

**Date (UTC):** 2026-06-06  
**Task:** Template / Runtime Truth — price reason `السعر مرتفع` vs dashboard template (60 min + custom text)

## Executive summary

Production read-only audit plus local reproduction proved **three independent divergence classes**:

| Layer | Saved dashboard truth | Runtime before fix | Divergence point |
|-------|----------------------|-------------------|------------------|
| **Schedule arming** | Template saved; abandon → reason → phone should arm | No `RecoverySchedule` when `cf_cart_*` key used | `main._schedule_normal_recovery_after_cart_recovery_reason_saved` consumed `store:session` pending mark stored under `store:cart_id` |
| **Delay** | 60 min (`reason_templates.messages`) | 180–300 s legacy fallback possible when store row missing at arm/send | `services/recovery_multi_message.resolve_recovery_schedule_timing` → `legacy_recovery_delay` (`services/recovery_delay.py`) |
| **WhatsApp body** | `reason_templates.message` / `messages[0].text` | Offer/guided fallback (`WHATSAPP_REASON_TEMPLATES`, `get_recovery_message`) | `main` multi-slot branch; `resolve_recovery_whatsapp_message_with_reason_templates` ignored `messages[0].text` when `message` empty |

**Source of truth after fix:** `Store.reason_templates_json` (dashboard POST `/api/dashboard/trigger-templates`) for both delay (`messages[stage].delay/unit`) and first-message text (`message` or `messages[0].text`), resolved at schedule arm (`delay_poll`) and send (`resolve_recovery_whatsapp_message_with_reason_templates`).

---

## Production evidence (fresh merchant, read-only)

Script: `scripts/_recovery_template_truth_audit.py`  
Artifacts: `scripts/_recovery_template_truth_audit_out/`

### 1. Dashboard template saved

| Field | Value |
|-------|-------|
| Table | `Store.reason_templates_json` |
| store_slug | `tpltruth-fd8210-745418` |
| store_id | 158 |
| price message | `PRICE_TEMPLATE_TRUTH_TEST_60_MIN` |
| price delay | 60 minute |
| updated_at | 2026-06-06T18:50:01Z |

`GET /dev/store-template-debug` confirmed dashboard row **equals** runtime row (id=158). Timing resolver: `effective_delay_seconds=3600`, `source=reason_templates.messages`.

### 2. Incomplete first audit run (cart flow gap)

Initial script posted only `cart_state_sync` + `/api/cartflow/reason` (no `cart_abandoned`). Result:

- Dashboard row visible with `reason_tag=price`, chip `💰 السعر مرتفع`
- **No** `RecoverySchedule` rows
- `merchant_followup_next_line_ar` null (correct — nothing scheduled)
- `/dev/recovery-operational-truth?recovery_key=store:cf_cart_*` returned `reason_tag=null` (suffix parsed as session_id)

### 3. Answers to audit questions (pre-fix)

1. **Why different delay than dashboard?** When schedule arms without `reason_templates` on the resolved store row, `resolve_recovery_schedule_timing` falls back to `legacy_recovery_delay` (e.g. 300 s for `price_high`, 180 s default for `price`). When schedule never arms (pending-key mismatch), dashboard shows waiting copy without a real `due_at`.
2. **Why WhatsApp body differed?** Multi-message branch uses `get_recovery_message` guided defaults when slot text empty; single-message path fell through to `WHATSAPP_REASON_TEMPLATES` offer copy when `message` field empty but `messages[0].text` populated.
3. **What was runtime reading?** Not wrong store in audited merchant (id=158 match). Failures were: pending-key consume miss, legacy delay fallback, guided/offer message fallback — not stale dashboard cache.
4. **Dashboard delay display?** `merchant_followup_next_line_ar` comes from **RecoverySchedule.due_at** (`services/merchant_followup_clarity_v1.py`), not template config directly.
5. **Which source won before fix?** Inconsistent: template resolver correct in isolation, but arm/send paths could skip it.

---

## Local reproduction (root cause proof)

```text
pytest tests/test_assist_handoff_no_recovery_schedule_v1.py  # FAILED before fix
# pending after abandon: ['demo:cf_cart_*']
# reason POST without cart_id: pending NOT consumed (arm_calls=0)
```

**Root cause:** `_mark_normal_recovery_pending_reason_tag` stored under `store:cart_id`; `_schedule_normal_recovery_after_cart_recovery_reason_saved` consumed `store:session_id` only.

---

## Fix scope (smallest root-cause)

1. **`main.py`** — pending arm alias (`store:session` + `store:cart_id`), consume tries cart_id from body / `AbandonedCart`, pop aliases together.
2. **`main.py`** — multi-slot send tries `resolve_recovery_whatsapp_message_with_reason_templates` before guided defaults.
3. **`services/reason_template_recovery.py`** — resolve `messages[0].text`; emit `[RECOVERY TEMPLATE TRUTH]` on template hit.
4. **`main.py`** — `/dev/recovery-operational-truth` resolves `cf_cart_*` recovery_key suffix via `AbandonedCart.zid_cart_id`.

---

## Tests added

`tests/test_recovery_template_runtime_truth_v1.py` (5 cases) + `tests/test_reason_template_recovery.py` (messages array text).

---

## Production proof (post-deploy checklist)

- [ ] Screenshot: dashboard price template 60 min + `PRICE_TEMPLATE_TRUTH_TEST_60_MIN`
- [ ] Screenshot: cart row `merchant_followup_next_line_ar` ≈ 60 min
- [ ] WhatsApp / message log body equals saved template
- [ ] Logs contain `[RECOVERY TEMPLATE TRUTH]` with matching `dashboard_template_hash` / `payload_hash`

Re-run: `python scripts/_recovery_template_truth_audit.py` (includes `cart_abandoned` step after script update).
