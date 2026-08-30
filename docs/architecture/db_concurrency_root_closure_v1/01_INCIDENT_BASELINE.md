# Phase 0 — Incident freeze

**Frozen (UTC):** 2026-08-30. No cleanup before this capture.

## Claimed live line

| Field | Value | Evidence |
|-------|-------|----------|
| Claimed live SHA | `c453d33680d4c70f9e52098cb7e6f8bf39cc5a1c` | Task statement; local commit exists (`fix: enforce DB hold budget, admission, and release-before-wait`) |
| Direct parent | `58a82f344cd3ba92c737cc7448e7e9d05910211f` | `git log` |
| HTTP `X-CartFlow-Git-Sha` | **absent** | Freeze probe 2026-08-30T15:57Z |
| Railway GraphQL deploy id | **UNKNOWN this freeze** | `service` query returned `Not Authorized` |
| `/ping` | 200 `{"ok": true}` | same probe |
| `/health` | 200 `{"ok": true, "service": "cartflow"}` | same probe; no pool fields on *this* live process yet |
| `/login` | 200 HTML | same probe |
| Autodeploy | OFF (controlled-deploy law) | Prior ops transcripts 2026-08-29–30 |
| Scheduler | Unchanged this program | Do not touch |

This freeze **cannot independently prove** that Railway is serving `c453d336`. Treat the SHA as the authorized engineering base. Re-probe deploy meta before any production deploy.

## Documented QueuePool class (not invented)

### I1 — Settings V2 fan-out (2026-08-29)

| | |
|--|--|
| First burst | `2026-08-29T18:56:15Z` |
| First/latest timeout in window | `/health?db=1` 503 at `2026-08-29T19:24:09Z`; recovered by `19:24:45Z` without restart |
| Live SHA then | `50cc5f9` → remediated `a2cf3df` deploy `305de4ac` |
| Routes | Settings APIs, `/login` ~95s, `/dashboard`, `/health?db=1` |
| User-visible | Settings unusable; login/dashboard site-wide slow |
| Pool | 5+5+5s |
| Cause class | 11+ concurrent DB-bound GETs + schema inspect |

### I2 — Dashboard startup fan-out (2026-08-30)

| | |
|--|--|
| First API wave | `2026-08-30T09:11:55Z` |
| Latest in window | review-session POST 500s ~`09:31Z` (~5.00s checkout wait) |
| SHA | `adac492` deploy `976393ee` |
| Routes | `/dashboard` → `/login`, `/health?db=1` 503, summary/projection/carts/Communication `Promise.all` |
| User-visible | Living Store recapture shows login despite bind `ok` |
| Follow-on | Inactive-surface init remediations on `58a82f3`; First-100 containment on `c453d336` |

### Historical class (same family, different config)

- 2026-05-17 recovery held connections across `asyncio.sleep` (pool 5+12)
- 2026-06-30 global stall with 30+30 pool (later reduced)

## Current configuration (code law)

| Item | API | Scheduler |
|------|-----|-----------|
| pool_size | 5 | 2 |
| max_overflow | 5 | 2 |
| pool_timeout | 5s | 5s |
| recycle | 300s | 300s |
| reset_on_return | rollback | rollback |

## Topology

- 1 API replica (`cartflow_api` / `CARTFLOW_PROCESS_ROLE=api`)
- Separate Scheduler service; expensive jobs default OFF
- Postgres identity previously proven `cartflow_restore_20260827` / `railway_private` (Aug 29–30 probes). **Not re-queried this freeze.**

## Affected user-visible behavior (class)

Unrelated `/login`, `/dashboard`, `/health?db=1`, and review-session POSTs fail or stall when any merchant surface saturates the shared 10-connection pool.

## Evidence preserved

- This pack + First-100 pack on `c453d336`
- Operational Scalability constitution (Settings incident)
- Agent transcripts [Settings / Living Store](24a5a716-d9ca-41fe-84aa-ba992209b341), [First-100](df00477a-0313-4682-97dd-a2c8e2b40286)
- Freeze JSON: `%TEMP%\cf_incident_freeze_phase0.json`
