# First-100 Operational Scale Validation V1

**Date (UTC):** 2026-08-30  
**Live SHA:** `f613ec7145a5e29c56257187159bfe366c26b3c0`  
**Deploy:** `bc48e3dd-36ec-47d2-a342-fa9c835b4c74` SUCCESS 2026-08-30T19:00:50.844Z  
**Mode:** validation only. No redesign. No pool/Scheduler/autodeploy change.  
**Verdict:** **NOT_CLOSED**. Highest proven safe stage: **50 concurrent merchant sessions**.

## Phase 0 — production identity

| Field | Evidence |
|-------|----------|
| Live SHA (`X-CartFlow-Git-Sha`) | `f613ec7145a5e29c56257187159bfe366c26b3c0` |
| Deployment id | `bc48e3dd-36ec-47d2-a342-fa9c835b4c74` |
| API replicas | one service instance `dd9597c9-4074-4158-a42c-1ae347df75c5` (GraphQL `numReplicas` null; not scaled out) |
| Pool | QueuePool `size=5` `max_overflow=5` `max_connections=10` (unchanged) |
| PostgreSQL | Railway Postgres via API `DATABASE_URL`; baseline `IDLE=6` `IIT=0` `ACTIVE=0` `LOCK_WAIT=0` |
| Scheduler | `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` / `f91e799d` SUCCESS, unchanged |
| Autodeploy | API OFF, Scheduler OFF |

Identity certain. Validation proceeded.

## Workload contract (Phase 2)

Recorded **before** execution.

This is **not** 100 distinct `Store` rows. Production Living Store issues authenticated operator sessions on tenant `demo`. Each session is an independent cookie + device UA on the merchant surfaces a First-100 operator uses.

| Class | Share | One visit cycle |
|-------|-------|-----------------|
| LIGHT | ~50% | session mint → `GET /dashboard` → Home `GET /api/dashboard/summary` → `GET /api/merchant/store-connection` → `GET /api/recovery-settings` |
| NORMAL | ~35% | session mint → `/dashboard` → summary → `GET /api/dashboard/normal-carts` → store-connection |
| HEAVY | ~15% | session mint → `/dashboard` → Workspace projection → one Communication `Promise.all` (messages + followups + summary) |

Device: 80% mobile / 20% desktop. Start stagger 0.40–0.50s × index. Think time 1.8–3.0s. No refresh storms.

Home in product code loads `/api/dashboard/summary` (same path as Communication summary). Dashboard HTML is the critical entry; summary 503 `db_pressure` is scored as controlled heavy degradation when bounded.

## Stage results

### 10 merchants — PASS

4 light / 4 normal / 2 heavy. 52/52 HTTP 200. Peak `checked_out=3`, avg 0.67. Controlled 503s: 0. QueuePool timeouts: 0. Login observer 200. Light fail 0. Long holders 0.  
Equilibrium immediate / +1 / +5 / +15 / +45: `checked_out=0`, registry=0, unexpected IIT=0. **TTE = immediate (0s).**

First-run instrument false-FAIL: +15s showed one `pg_class` inspect IIT with `xact_s=0`, API `checked_out=0`, gone at +45s. Reclassified as explained schema flash (not request leftover). Second execution of 10 was clean at every sample.

### 25 merchants — PASS

12 light / 9 normal / 4 heavy. 129/129 200. Peak `checked_out=6`, avg 1.25. Rejections 0. Timeouts 0. Slowest critical `/dashboard` 7836ms (still 200). Slowest heavy workspace 8229ms (200).  
Equilibrium 0 at all samples. **TTE = 0s.**

### 50 merchants — PASS

24 light / 18 normal / 8 heavy. 258/258 200. Peak `checked_out=4`, avg 1.07. Rejections 0. Timeouts 0. Slowest critical `/dashboard` 1346ms. Slowest heavy messages 3605ms.  
Equilibrium 0 at all samples. **TTE = 0s.**

### 100 merchants — FAIL (first failed gate; stop)

50 light / 35 normal / 15 heavy. 511 requests. 488 200. Peak `checked_out=10` (pool max). Avg 3.08. QueuePool timeout delta **0**.  
Client classes: 6 critical-route failures (dashboard / session mint), 6 unexpected 5xx-or-transport, 11 slow `db_pressure` 503s (`>250ms` client; server FINALLY sample `normal-carts` 503 `request_ms=0.3`). Light/normal fail count 11. Login **observer** stayed 200.  
Slowest critical `/dashboard` 13182ms (one 200). Slowest heavy messages 17419ms (one 200).  
Server `[DB CHECKIN]` in the 100 window: longest **hold_ms=2068** on `/api/dashboard/messages` (wall ≫ hold → wait/queue, not a leaked checkout).  
**Equilibrium after 100 still absolute:** immediate through +45s `checked_out=0`, registry=0, unexpected IIT=0. No restart. No leak.

25 and 50 were not skipped. 100 is the first failed acceptance gate.

## Phase 13 — isolation (at 50)

1 heavy session (3 Workspace + Communication cycles) + 49 light sessions.  
258/258 200. Light fail 0. Login fail 0. Peak `checked_out=2`. Equilibrium 0.  
**ISOLATION: PASS.** One heavy merchant did not monopolize shared capacity at the proven envelope.

## Phase 14 — saturating resource

At **50** (highest pass): nothing at its practical limit. Pool peak 4/10. No admission. No lock waits. No QueuePool timeout.

At **failed 100**: first hard limit hit is the **API QueuePool** (`checked_out=10/10`). Wall times (13–17s) exceeded DB hold (~2s). That is pool wait / application concurrency under a full pool, not a held leftover.

## Phase 15 — first failure class

**DB_POOL_SATURATION**

Contributing symptoms (not separate first classes): application-concurrency wait (slow walls, some client 5xx/critical), light/normal damage under the full pool (`CROSS_MERCHANT_STARVATION` as effect). Not a leak (`RESOURCE_LEAK` falsified by post-100 equilibrium). Not QueuePool timeout. Not lock contention (`LOCK_WAIT=0`).

No patch in this task.

## Phase 16 — infrastructure

**NEW INFRASTRUCTURE JUSTIFIED: NO**

50 concurrent mixed sessions are safe on the current 1× API + QueuePool 5+5+5s + one Postgres. 100 failed on that pool’s measured cap. Redis / PgBouncer / Celery / Kafka / extra Postgres / read replicas / larger pool / more replicas are **not** authorized by this validation. A later root-cause task may decide whether replica count or hold-time is the cheaper close.

## Phase 17 — post-test regression

Single Living Store session: login, Home, Workspace, Carts, Communication, Settings — all 200.  
`/ping` `/health` `/health?db=1` `/login` 200.  
Post-test live snap: `checked_out=0`, holders=0, IIT=0, `timeout_count=0`.  
One explained 0s `pg_catalog` IIT appeared on regression +5s sample (API idle); later snap IIT=0.

**POST-TEST REGRESSION: PASS.** Scale testing did not leave the runtime degraded.

## Required report

LIVE SHA: `f613ec7145a5e29c56257187159bfe366c26b3c0`

WORKLOAD MODEL: 50/35/15 light/normal/heavy interleaved; 80/20 mobile/desktop; staggered human pacing; one Communication composition per heavy; Living Store `demo` operator sessions (not N Store rows)

10 MERCHANTS: PASS  
10 PEAK CHECKED_OUT: 3  
10 CONTROLLED REJECTIONS: 0  
10 QUEUEPOOL TIMEOUTS: 0  
10 TIME TO EQUILIBRIUM: 0s (immediate)

25 MERCHANTS: PASS  
25 PEAK CHECKED_OUT: 6  
25 CONTROLLED REJECTIONS: 0  
25 QUEUEPOOL TIMEOUTS: 0  
25 TIME TO EQUILIBRIUM: 0s

50 MERCHANTS: PASS  
50 PEAK CHECKED_OUT: 4  
50 CONTROLLED REJECTIONS: 0  
50 QUEUEPOOL TIMEOUTS: 0  
50 TIME TO EQUILIBRIUM: 0s

100 MERCHANTS: FAIL  
100 PEAK CHECKED_OUT: 10  
100 CONTROLLED REJECTIONS: 11 (plus 6 critical + 6 unexpected 5xx/transport)  
100 QUEUEPOOL TIMEOUTS: 0  
100 TIME TO EQUILIBRIUM: 0s (idle recovered; stage still FAIL)

HIGHEST PROVEN SAFE STAGE: 50 concurrent merchant sessions

CRITICAL ROUTE AVAILABILITY: PASS through 50; FAIL at 100 (6 critical-route failures). Observer `/login` stayed 200 at 100.

CROSS-MERCHANT ISOLATION: PASS (measured at 50)

UNEXPECTED IIT: 0 (request-owned / held xact). Explained 0s schema flashes only.

UNEXPLAINED LONG HOLDERS: 0

LONGEST DB HOLD: 2068ms (`/api/dashboard/messages` during 100). Isolation/regression checkins 0.1–10ms.

SLOWEST CRITICAL REQUEST: `/dashboard` 13182ms at 100 (200); at 50: 1346ms

SLOWEST HEAVY REQUEST: `/api/dashboard/messages` 17419ms at 100 (200); at 50: 3605ms

FIRST SATURATING RESOURCE: API QueuePool (hits 10/10 at 100; 4/10 at 50)

CONTROLLED DEGRADATION: PASS through 50 (no need). At 100, admission existed but critical routes also failed → not an acceptable-only-heavy degrade.

POST-TEST CHECKED_OUT: 0  
POST-TEST IIT: 0  
POST-TEST REGRESSION: PASS

SYSTEM RETURNS TO ABSOLUTE EQUILIBRIUM: YES (after every stage, including failed 100)

NEW INFRASTRUCTURE JUSTIFIED: NO

FIRST-100 OPERATIONAL SCALE SAFETY: **NOT_CLOSED**

SAFE TO RESUME VISUAL WORK: **NO**

STOP.
