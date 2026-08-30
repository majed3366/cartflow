# Phase 10 — Query safety

No new query rewrites in this pack except what First-100 already bounded. Only evidence-backed caps are kept.

| Surface | Bound | Status |
|---------|-------|--------|
| Messages fetch | `MESSAGES_FETCH_CAP` | First-100 |
| Followups / reply map | `CUSTOMER_REPLY_MAP_LIMIT` | First-100 |
| Message log phone bulk | `MESSAGE_LOG_PHONE_BULK_LIMIT` | First-100 |
| Recovery schedule bulk | `RECOVERY_SCHEDULE_BULK_LIMIT` | First-100 |
| Carts list | existing page 50–250 | unchanged |
| Auth/session | single user + primary store | short phase now |
| Home summary | one summary read | unchanged |
| Settings | sequential overview (Settings remediation) | unchanged |
| Workspace enrich_fallback | admitted on miss only | unchanged |

No index migration. No snapshot rebuild on request path.
