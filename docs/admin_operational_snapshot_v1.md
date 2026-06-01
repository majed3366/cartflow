# Admin Operational Snapshot Export v1

**Date (UTC):** 2026-06-01  
**Service:** `services/admin_operational_snapshot_v1.py`  
**Endpoint:** `GET /admin/operations/snapshot` (admin session auth)

## Purpose

Single read-only JSON export of operational truth for:

- Support handoffs (Zid, WhatsApp providers, internal ops)
- Incident investigation
- Integration debugging (e.g. OAuth + readiness + scheduler in one bundle)
- Future Admin Controls planning (evidence bundle, not a health score)

This is **not** a health score, alert engine, or repair tool. No behavior changes.

## Auth

Requires valid admin session cookie (`CARTFLOW_ADMIN_PASSWORD`). Returns `401` JSON when unauthorized.

## Query parameters

| Param | Description |
|-------|-------------|
| `store_slug` | Optional. Scopes store readiness, recovery counts, recent events, and support context to one store (`Store.zid_store_id`). |

## Response

`Content-Type: application/json`

```json
{
  "ok": true,
  "snapshot": { ... }
}
```

## Snapshot structure

| Section | Contents |
|---------|----------|
| **metadata** | `generated_at`, `environment`, `commit_sha`, `store_slug`, `generated_by`, `snapshot_version` |
| **runtime_health** | Scheduler, due scanner, runtime health, provider readiness, recovery readiness, operational control flags |
| **store_readiness** | Platform aggregate or per-store onboarding flags (widget, WhatsApp, recovery, connection) |
| **recovery_overview** | Counts: running, scheduled, completed, skipped, failed (no cart-level dumps) |
| **operational_signals** | Provider, onboarding, identity, lifecycle, trust warnings (existing signals only) |
| **recent_events** | Summarized last N events (schedule status, control pauses, log status) — no raw logs |
| **support_context** | `store_slug`, `zid_store_id`, `merchant_user_id`, OAuth configured booleans, readiness/runtime summary |

## Security / redaction

Never exported:

- OAuth tokens, secrets, passwords, credentials
- Phone numbers, message bodies
- Raw `context_json` on schedules/logs

Redaction runs via `redact_operational_snapshot()` before return.

## Example usage

```bash
# Platform-wide snapshot (after admin login cookie)
curl -sS -b "cartflow_admin_session=..." \
  "https://smartreplyai.net/admin/operations/snapshot"

# Store-scoped (Zid slug / zid_store_id)
curl -sS -b "cartflow_admin_session=..." \
  "https://smartreplyai.net/admin/operations/snapshot?store_slug=my-store-id"
```

## Example output (abbreviated)

```json
{
  "ok": true,
  "snapshot": {
    "metadata": {
      "snapshot_version": "admin_operational_snapshot_v1",
      "generated_at": "2026-06-01T12:00:00Z",
      "environment": "production",
      "commit_sha": "d088586",
      "store_slug": "demo-store",
      "generated_by": "admin_session"
    },
    "runtime_health": {
      "scheduler": { "ok": true, "role": "scheduler", "overdue_scheduled_count": 0 },
      "due_scanner": { "status": "healthy", "loop_running": true },
      "provider_readiness": { "ready": true, "mode": "production" }
    },
    "store_readiness": {
      "scope": "store",
      "ready": false,
      "blocking_steps": ["store_not_connected"],
      "widget_configured": true,
      "whatsapp_configured": true,
      "recovery_enabled": true
    },
    "recovery_overview": {
      "active_running": 1,
      "scheduled": 3,
      "completed": 12,
      "skipped": 2,
      "failed": 0
    },
    "operational_signals": {
      "provider_issues": [],
      "onboarding_blockers": ["store_not_connected"]
    },
    "recent_events": [
      { "at": "2026-06-01T11:55:00Z", "kind": "recovery_scheduled", "source": "recovery_schedule" }
    ],
    "support_context": {
      "store_slug": "demo-store",
      "zid_store_id": "demo-store",
      "merchant_user_id": 7,
      "store_connected": false,
      "has_oauth_access_token": false,
      "zid_platform_oauth_configured": true
    }
  }
}
```

## Tests

```bash
pytest tests/test_admin_operational_snapshot_v1.py -q
```
