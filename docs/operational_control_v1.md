# Operational Control v1 — Targeted control foundation

**Date (UTC):** 2026-05-19  
**Commit:** `feat: add targeted operational control foundation v1`

Additive gates only — does not change Purchase Truth, lifecycle rules, queue execution, recovery logic, widget, merchant dashboard, or existing schedule rows.

## Principle

```text
Isolate → Pause affected component → Investigate → Verify → Resume
(Do NOT stop the whole platform.)
```

## Controls

| Control | Flag / effect | What continues |
|---------|---------------|----------------|
| Pause WA | `wa_send_allowed=false` | Lifecycle, logs, purchase truth, in-flight recovery logic |
| Pause scheduling | `schedule_creation_allowed=false` (new rows only) | Running / existing `RecoverySchedule` rows |
| Pause store | Per `store_slug` | Other stores |
| Pause reason | `reason_allowed=false` for tag | Other reasons |
| Pause continuation | `continuation_allowed=false` | Recovery sends + inbound replies |
| Pause provider | `provider_paused=true` | Mock/fallback hint in block response |

**Dry-run:** `[CONTROL DRY RUN]` — preview + verification, no state change.

**Audit:** `[OPERATIONAL CONTROL EVENT] operator=… reason=… scope=… duration=… effect=…`

## Admin UI

- `GET /admin/control` — sections for each control, verification panel, history, resume
- `POST /admin/control/apply`, `POST /admin/control/resume`
- `GET /api/admin/operational-control/state`, `…/verification` (session auth)

All toggles **off by default** until operator enables pause on submit.

## Code map

| Layer | Path |
|-------|------|
| State + API | `services/operational_control_v1.py` |
| WA gate | `services/whatsapp_send.py` → `send_whatsapp` / mock |
| Schedule gate | `services/recovery_restart_survival.py` → `persist_recovery_schedule_durable` (new row only) |
| Continuation gate | `services/cartflow_reply_intent_engine.py` → `process_continuation_after_customer_reply` |
| Routes | `routes/operational_control_admin.py` |
| Template | `templates/admin_operational_control.html` |

## Capability matrix

| Control | Expected | Observed (v1) | PASS / FAIL |
|---------|----------|---------------|-------------|
| Pause WA | No new WA; recovery continues | Gate at `send_whatsapp` | **PASS** |
| Pause scheduling | No new schedules; running continue | Gate on new `RecoverySchedule` insert | **PASS** |
| Pause store | Scoped by slug | `paused_stores` set | **PASS** |
| Pause reason | Scoped by tag | `paused_reasons` prefix match | **PASS** |
| Pause continuation | No auto-reply continuation | Early return in continuation processor | **PASS** |
| Pause provider | `provider_paused=true`, fallback hint | Twilio path blocked | **PASS** |
| Dry-run | `[CONTROL DRY RUN]`, no pause | `dry_run=True` on apply | **PASS** |
| Verification | Stores + recoveries + runtime | `build_operational_control_verification()` | **PASS** (in-process) |
| Audit trail | `[OPERATIONAL CONTROL EVENT]` | Ring buffer + log/print | **PASS** (per worker) |
| Admin UI | All sections + resume | `/admin/control` | **PASS** |

## Gaps

### Closed ✅

- Targeted pause for WA, scheduling (new), store, reason, continuation, provider
- Dry-run + verification + event log
- Admin control page (replaces placeholder)

### Remaining 🟡

- State is **in-process** — multi-worker / restart clears pauses unless shared store added
- No automatic expiry by `duration` field yet (metadata only)
- Manual retry still dev-only (`/dev/recovery-restart-survival-verify`)

### Dangerous 🔴

- Per-worker split brain if load-balanced without sticky sessions
- No persisted audit DB — events lost on restart (bounded deque only)

## Deploy & real verification

| Step | Action | PASS if |
|------|--------|---------|
| 1 | Deploy commit to Railway | Build succeeds |
| 2 | Login `/admin/control` | Page shows flags all allowed |
| 3 | Dry-run pause WA | `[CONTROL DRY RUN]` in logs; `wa_send_allowed` still true |
| 4 | Pause WA + reason | Test cart-event / recovery path: no Twilio send; schedule may still run |
| 5 | Resume all | Flags true; send works again |
| 6 | Pause scheduling only | New abandon gets no new schedule row; running row still executes |

**Automated:** `pytest tests/test_operational_control_v1.py -q`
