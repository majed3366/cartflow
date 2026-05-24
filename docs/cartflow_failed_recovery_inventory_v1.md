# Failed Recovery Inventory v1

**Scope:** Read-only operator reference. No behavior changes.  
**API:** `GET /dev/recovery-health` → `recent_failures`, `failed_detail`  
**Code:** `services/recovery_failure_explanation_v1.py`

---

## Part 1 — Failure types

### RecoverySchedule (durable row)

| Status | Owner | Meaning | Risk | Action |
|--------|-------|---------|------|--------|
| `whatsapp_failed` | Schedule + often log | Provider did not complete send | Medium | Yes — check Twilio/template/number |
| `failed_resume` | Schedule | Resume/execution ended unsafe | Medium | Review logs + `last_error` |
| `failed_resume_stale` | Schedule (stale repair) | `running` too long, no send evidence | Low | Usually no — verify no double-send |
| `needs_review` | Schedule | Manual review flagged | Medium | Yes — human check |

### CartRecoveryLog (append-only)

| Status | Owner | Meaning | Risk | Action |
|--------|-------|---------|------|--------|
| `whatsapp_failed` | Normal recovery send path | Inline send failed | Medium | Yes — provider |
| `failed_retry` | WhatsApp queue worker | Retry in progress | Low | Monitor |
| `failed_final` | WhatsApp queue worker | Retries exhausted | Medium | Yes — provider |

### Lifecycle / observation (not schedule status)

| Signal | Owner | Meaning |
|--------|-------|---------|
| `[PURCHASE STOP]` | Purchase truth | Not a failure — intentional stop |
| `[RECOVERY BLOCKED]` | Lifecycle closure | Blocked send — often purchase/return |
| `[RECOVERY STALE DETECTED]` | Stale repair | May lead to `failed_resume_stale` or `completed` |

---

## Part 2 — Calm explanations (operator)

Mapped in code via `explain_failure_status()`:

| Status | Explanation |
|--------|-------------|
| `whatsapp_failed` | The message provider rejected the send or was unavailable. |
| `failed_resume` | Recovery could not safely resume or finish after restart or dispatch. |
| `failed_resume_stale` | A delayed recovery was left in running state past the stale threshold. |
| `needs_review` | Recovery stopped in a state that needs a human check. |
| `failed_retry` | A queued WhatsApp send failed; the worker will retry before giving up. |
| `failed_final` | WhatsApp delivery failed after the maximum retry attempts. |

Detail hints: `last_error` on schedule may set `reason_code=provider_timeout` or `cancelled_for_purchase`.

---

## Example health output

When `failed=1` and schedule row is `whatsapp_failed`:

```json
"failed": 1,
"failed_detail": {
  "aggregate_failed_schedules": 1,
  "latest": {
    "status": "whatsapp_failed",
    "reason": "provider_restriction_or_unavailable",
    "explanation": "The message provider rejected the send or was unavailable.",
    "action_needed": "yes",
    "time": "2026-05-19T12:00:00+00:00"
  }
},
"recent_failures": { "count": 1, "latest": { ... } }
```
