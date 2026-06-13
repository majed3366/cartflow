# Recovery Schedule Materialization Fix v1 Report

**Date (UTC):** 2026-06-13  
**Scope:** Fix + tests + dashboard truth. Resolves audit root cause for cart **4188** class (`cart_state_sync` + reason, no pending arm marker).

**Prior audit:** `docs/cartflow_recovery_schedule_materialization_audit_v1_report.md`

---

## Executive summary

Normal recovery schedules now materialize when:

1. `AbandonedCart` exists (including via **`cart_state_sync`**),
2. `CartRecoveryReason` is saved via `POST /api/cartflow/reason`,
3. Normal lane + existing phone/template/guard rules pass.

The post-reason hook no longer **requires** in-memory pending arm markers from `handle_cart_abandoned`.

| Requirement | Status |
|-------------|--------|
| Durable fallback when pending arm missing | **Done** — `services/recovery_schedule_materialization_v1.py` |
| No duplicate schedules | **Done** — DB check + existing in-memory claim |
| VIP not scheduled as normal recovery | **Done** — VIP lane skip in durable path; existing VIP branch unchanged |
| Phone requirements not bypassed | **Done** — `_normal_recovery_phone_ready_for_schedule` unchanged |
| Explicit block when phone deferred (`after_reason`) | **Done** — `schedule_blocked_missing_phone` log status |
| Dashboard truth without schedule row | **Done** — lifecycle labels; no **الإرسال الأول بعد** without materialized schedule |
| Tests | **6/6 pass** — `tests/test_recovery_schedule_materialization_v1.py` |

---

## 1. Root cause (recap)

| Step | Before fix |
|------|------------|
| Zid bridge | `cart_state_sync` → `_handle_cart_state_sync` → `AbandonedCart` only |
| Reason POST | `_schedule_normal_recovery_after_cart_recovery_reason_saved` |
| Pending markers | `_consume_normal_recovery_pending_*` → both `None` |
| Result | Early `return` — **no** `_arm_recovery_schedule_from_saved_reason_payload` |

---

## 2. Implementation

### 2.1 Durable fallback module

**File:** `services/recovery_schedule_materialization_v1.py`

**Entry:** `try_durable_normal_recovery_materialization_after_reason()`

| Step | Action |
|------|--------|
| 1 | `reason_tag_saved_for_session` — verify `CartRecoveryReason` |
| 2 | `find_abandoned_cart_for_reason_arm` — by `cart_id` / `session_id` |
| 3 | `active_recovery_schedule_exists` — skip if `scheduled`/`running` row exists |
| 4 | VIP check via `is_vip_cart` — skip normal arm (`skipped_vip`) |
| 5 | `build_reason_arm_synth_payload` + `_arm_recovery_schedule_from_saved_reason_payload` |

### 2.2 Hook change

**File:** `main.py` → `_schedule_normal_recovery_after_cart_recovery_reason_saved`

When `arm_ctx is None and phone_ctx is None`, invoke durable fallback **instead of** silent `return`.

Pending-marker path (legacy `cart_abandoned` → `waiting_for_reason` / `waiting_for_phone`) is **unchanged**.

### 2.3 Duplicate prevention

**File:** `main.py` → `_execute_cart_abandon_recovery_schedule_continue`

Before `_try_claim_recovery_session`, query `active_recovery_schedule_exists` for recovery-key aliases. If a row exists → return `recovery_state: scheduled`, `skipped_duplicate_schedule: true`.

Combined with:

- In-memory `_try_claim_recovery_session`
- `persist_recovery_schedule_durable` upsert by `(recovery_key, step, multi_slot_index)`

### 2.4 Phone block — explicit status

**File:** `main.py` → `_execute_cart_abandon_recovery_schedule_continue`

When phone not ready on **reason-arm path** (`skip_abandon_upsert=True`):

- Log status: **`schedule_blocked_missing_phone`** (was `skipped_missing_phone` on this path only)
- Legacy abandon path still uses **`skipped_missing_phone`**

### 2.5 Dashboard / lifecycle truth

**File:** `services/customer_lifecycle_states_v1.py`

New labels:

| Label | When |
|-------|------|
| **بانتظار اكتمال بيانات التواصل** | Pre-send, **no** materialized schedule, phone blocked / missing |
| **لم يتم تجهيز الإرسال بعد** | Pre-send, **no** materialized schedule, phone OK but no schedule row |

Rules:

- **No** `customer_lifecycle_next_followup_line_ar` containing **الإرسال الأول بعد** unless `schedule_materialized` (`due_at` or prefetched schedule delay from DB row).
- Existing `waiting_first_send` + ETA only when a schedule row backs the countdown.

---

## 3. Code path after fix (cart 4188 class)

```
cart_state_sync → AbandonedCart
POST /api/cartflow/reason (price)
  → _schedule_normal_recovery_after_cart_recovery_reason_saved
  → pending consume miss
  → try_durable_normal_recovery_materialization_after_reason
  → _arm_recovery_schedule_from_saved_reason_payload
  → _execute_cart_abandon_recovery_schedule_continue
     → [phone OK] → _schedule_recovery_multi_slots → RecoverySchedule rows
     → [phone missing] → schedule_blocked_missing_phone, no row
```

---

## 4. Tests

**File:** `tests/test_recovery_schedule_materialization_v1.py`

| Test | Result |
|------|--------|
| `cart_state_sync` + reason + phone → `RecoverySchedule` created | **PASS** |
| `cart_state_sync` + reason + missing phone → no schedule + `schedule_blocked_missing_phone` | **PASS** |
| Legacy `cart_abandoned` waiting_for_reason → reason → schedule | **PASS** |
| Repeated reason POST → no duplicate scheduled rows | **PASS** |
| Due scanner `found >= 1` after materialization + backdated `due_at` | **PASS** |
| Lifecycle: no **الإرسال الأول** line without schedule | **PASS** |

```bash
python -m pytest tests/test_recovery_schedule_materialization_v1.py -v
```

---

## 5. Files changed

| File | Change |
|------|--------|
| `services/recovery_schedule_materialization_v1.py` | **New** — durable arm logic |
| `main.py` | Hook fallback; duplicate DB guard; phone log status on reason-arm |
| `services/customer_lifecycle_states_v1.py` | Dashboard labels; ETA gated on materialized schedule |
| `tests/test_recovery_schedule_materialization_v1.py` | **New** — 6 tests |
| `docs/SYSTEM_SUMMARY.md` | Changelog row |

---

## 6. Sign-off

| Item | Status |
|------|--------|
| Fix for audit root cause | **Complete** |
| Phone / VIP / duplicate guards | **Preserved** |
| Dashboard truth when schedule missing | **Complete** |
| Deploy | **Not performed** (code + tests only) |
