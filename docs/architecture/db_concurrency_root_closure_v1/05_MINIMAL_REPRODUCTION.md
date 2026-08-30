# Phase 4 — Minimal reproduction

Preferred smallest scenario (from living incidents, not 100 sessions):

## Proven smallest saturators

| ID | Scenario | Evidence |
|----|----------|----------|
| A | One Settings first-load (pre-`a2cf3df`) | 11+ concurrent DB GETs vs 10 slots |
| B | One dashboard bind + all-surface init (pre-`58a82f3`) | 2026-08-30 09:11:55Z wave |
| C | Communication 3 parallel GETs + second tab | At budget edge; plus auth checkouts |
| D | Mobile + desktop same merchant | Two auth+surface stacks |

## Mandatory timeline (suspect path: authenticated dashboard GET)

| Mark | Event | Before this pack | After this pack (designed) |
|------|-------|------------------|----------------------------|
| T0 | Request start | middleware | same + request_id |
| T1 | Checkout | auth `get_merchant_user_by_id` | same, then **identity release** |
| T2 | Last DB use | often late in handler | last query in short phase |
| T3 | Non-DB work | JSON/HTML while held | after `j()` / identity release |
| T4 | Response produced | session still open | session already released |
| T5 | Session close | middleware `finally` | already closed; `finally` idempotent |
| T6 | Checkin | with T5 | with T2/T3, not T4 |

## Local QueuePool reproduction (this pack)

`tests/test_db_concurrency_root_closure_v1.py`:

- 4 concurrent checkouts on QueuePool 5+5 → all close → `checked_out` returns to 0
- Exception after `SELECT 1` → checkin
- Early return → checkin

**Not reproduced here:** live merchant cookies against production. First-100 soak remains paused.
