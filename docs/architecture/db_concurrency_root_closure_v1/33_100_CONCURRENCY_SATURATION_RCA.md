# 100-Concurrency Saturation Root Cause V1

**Date (UTC):** 2026-08-30  
**Live SHA:** `f613ec7145a5e29c56257187159bfe366c26b3c0`  
**Mode:** investigation only. No pool/admission/query/infra change.

## Phase 1 — smallest reproduction

Same mixed contract as First-100 (50/35/15, stagger, think time, Living Store `demo`).

| n | peak checked_out | messages hold p50/p95/max | messages wall p50/max | dashboard wall p50/max | critical | 503 | PG LOCK_WAIT | timeout |
|---|------------------|---------------------------|----------------------|------------------------|----------|-----|--------------|---------|
| 50 (prior) | 4 | (not logged as p50) / max 2068 at 100 only | — / 3605 | — / 1346 | 0 | 0 | 0 | 0 |
| **60** | **3** | **5.2 / 8.5 / 2109** | **3602 / 5549** | **855 / 4299** | **0** | **2** (normal-carts admission) | **0** | **0** |

**FIRST REPRODUCIBLE SATURATION STAGE: 60** — the ~2s messages **hold** appears here. Pool is **not** full (peak 3/10). 70–100 not required once the hold transition reproduced.

SATURATION TRANSITION: **threshold / outlier**. p95 hold stays milliseconds; a minority of messages checkouts jump to ~2s.

20 concurrent messages-only: 2 admitted / 18 `db_pressure` 503 (matches `HEAVY_PER_ROUTE_LIMIT=2`). Peak `checked_out=4`. Lock wait 0.

## Phase 2 — hold decomposition

Request `6b16a9dc5f0f4e84` `GET /api/dashboard/messages` (60-stage, 200):

- **61 checkouts + 61 checkins** on one AnyIO worker
- hold p50 **5.2ms**; 2 holds ≥100ms; **1 hold = 2109.4ms** (`pg:23403`)
- `request_ms=2145.3` ≈ long hold
- FINALLY: `holders_before=2` (other in-flight work), status 200

| Component | Evidence |
|-----------|----------|
| POOL_WAIT | Not in `hold_ms` (starts at checkout). `timeout_count=0` so waits &lt;5s. |
| DB_QUERY_TIME | Typical statement 0.1–10ms. Not 2s for most SQL. |
| DB_LOCK_WAIT | **NO** (`LOCK_WAIT=0` all samples). |
| DB_NETWORK_TIME | Not isolated; short statements imply not 2s RTT. |
| ORM / app while held | **YES** — lifecycle/timeline enrich + refresh aggregates while a connection remains checked out for ~2s. |
| TRANSACTION_FINALIZATION | COMMIT/ROLLBACK seen; not the 2s span. |

The ~2s is **one spanning checkout**, not 2s of SQL on every statement. It matches handler wall. Single-merchant earlier: hold 0.1–7.9ms, wall ~2s (work **after** checkin). Under 60+: that ~2s **moves into** a held checkout.

## Phase 3 — Postgres during pressure

- `ACTIVE` peak 2; `LOCK_WAIT` 0; `LONG_RUNNING` 0
- IIT samples: `recovery_truth_timeline_events` SELECT (`ClientRead`, `xact_s=0–1`) and `pg_catalog.pg_class` inspect
- `ClientRead` + idle-in-transaction = backend waiting on the **application**, not a lock

POSTGRES PRIMARY WAIT: **ClientRead** (app still holding).  
POSTGRES LOCK CONTENTION: **NO**.  
DB CPU / I/O BOTTLENECK: **NOT_PROVEN**.

## Phase 4 — hot query

| | |
|--|--|
| Route | `GET /api/dashboard/messages` |
| Purpose | `sent_logs_for_store` (`cart_recovery_logs`) + refresh-token aggregates + delivery/reply maps + **per-row** `timeline_status_set` → `get_recovery_truth_timeline` (`recovery_truth_timeline_events`) |
| Concurrent executions | 2 admitted messages (per-route cap); each ~60 pool checkouts |
| Normal duration | statement p50 ~5ms |
| Pressure duration | one spanning checkout ~2109ms; wall 3.6–5.5s at 60, 17s at 100 |
| Index | `store_slug` on logs; timeline by `recovery_key`. Plans not captured (no EXPLAIN on prod). |

Do not optimize in this task.

## Phase 5 — admission vs capacity

| | |
|--|--|
| Heavy HTTP cap | global **4**, per-route **2** |
| Pre-DB admit | messages, followups, normal-carts only |
| Workspace | handler-level admit |
| Summary / Home / dashboard / Settings / session mint | **not** in `HEAVY_GET_ROUTES` |
| One Communication UI action | **3 HTTP** (messages + followups + summary). Admission counts **2** heavy requests, not 3, and **not** ~60 inner checkouts. |
| Critical reserve | **NO**. Comment claims leftover slots; uncapped routes + multi-checkout heavy can still fill 10. |
| Can admitted heavy consume all 10? | **YES** in overlap with uncapped work. Two messages already showed `checked_out=4 overflow=2` mid-request. |

COMMUNICATION DB DEMAND MULTIPLIER: **3 HTTP × (messages ≈ 60 pool checkouts)**.

## Phase 6 — 100-stage critical failures

Individual request-ids for the 6 First-100 critical fails were not persisted. Proven constraints:

- QueuePool `timeout_count` delta **0** → not `WAITING_FOR_POOL` via timeout
- Observer `/login` **200**
- One server FINALLY 503 in that window: `normal-carts` admission `request_ms=0.3` (not critical)
- 60-stage: **0** critical fails at the same ~2s hold

Inferred (not per-id proven): **APPLICATION_QUEUEING** and/or **CLIENT_TIMEOUT / TRANSPORT** on `/dashboard` and Living Store mint. Mint **re-hashes pbkdf2-26000 and UPDATEs the same `merchant_users` row** every session — a workload amplifier, not production login.

## Phase 7 — hypotheses

| | Verdict | Evidence |
|--|---------|----------|
| H1 query becomes ~2s | **PARTIAL** | Typical SQL 5ms; one spanning checkout ~2s includes many statements + app. |
| H2 lock/wait | **FALSIFIED** | `LOCK_WAIT=0`. |
| H3 app work while checked out | **SUPPORTED** | 61 checkouts/request; timeline IIT `ClientRead`; hold ≈ `request_ms`. |
| H4 Communication multiplies occupancy | **SUPPORTED** | 3-way `Promise.all`; summary uncapped; messages inner ×60. |
| H5 admission does not reserve critical | **SUPPORTED** | No reserved slots; dashboard/summary/mint uncapped. |
| H6 admission counts requests not connections | **SUPPORTED** | 1 admitted messages ≠ 1 checkout. |
| H7 thread/execution pool delays lifecycle | **PARTIAL** | Sync routes on AnyIO; 100 overlap can queue; not proven as the 2s hold. |
| H8 DB CPU/I/O true bottleneck | **NOT_PROVEN** | No lock/IO wait class; ClientRead dominant. |
| H9 hot query/index path | **SUPPORTED** | `recovery_truth_timeline_events` + `cart_recovery_logs` on messages; `inspect`/`pg_class`. |
| H10 client/transport independent of DB | **PARTIAL** | Explains some 100 5xx/critical without timeout; 2s hold is server-side. |

## Phase 8 — causal chain

Living Store mixed load on one `demo` tenant  
→ Communication + Home hit messages/summary; messages runs tens of sequential pool checkouts and keeps one connection for ~2s (lifecycle/timeline enrich)  
→ admission treats that as **one** heavy request  
→ uncapped summary/dashboard/settings/mint add more checkouts (mint: pbkdf2 + same-row UPDATE)  
→ at 100, overlap fills **10/10**  
→ dashboard/session walls grow / some fail; **no leak**, equilibrium returns.

## Report fields

LIVE SHA: `f613ec7145a5e29c56257187159bfe366c26b3c0`  
LAST PROVEN SAFE STAGE: 50  
FIRST REPRODUCIBLE SATURATION STAGE: **60** (hold expansion; not 10/10)  
SATURATION TRANSITION: threshold / outlier  
NORMAL MESSAGES DB HOLD: p50 **5.2ms** / p95 **8.5ms**  
PRESSURE MESSAGES DB HOLD: max **2109ms** (one spanning checkout; wall 3.6–17s)  

DB HOLD BREAKDOWN:  
- query: ~5ms typical statement  
- lock/wait: **0**  
- materialization: inside spanning hold  
- application while held: **yes** (~61 checkouts, timeline N+1)  
- transaction finalization: not the 2s  

HOT QUERY: `recovery_truth_timeline_events` by `recovery_key` (+ `cart_recovery_logs` history)  
HOT QUERY NORMAL DURATION: ~5ms  
HOT QUERY PRESSURE DURATION: spanning UoW ~2109ms  
POSTGRES PRIMARY WAIT: ClientRead  
POSTGRES LOCK CONTENTION: **NO**  
DB CPU / I/O BOTTLENECK: **NOT_PROVEN**  
COMMUNICATION DB DEMAND MULTIPLIER: **3 HTTP; messages ≈ 60 checkouts**  
HEAVY ADMISSION LIMIT: **4 global / 2 per route**  
CRITICAL CAPACITY RESERVED: **NO**  

CRITICAL FAILURE CAUSES: 6 at 100 not individually id’d; **0** QueuePool timeouts; inferred **APPLICATION_QUEUEING** / **CLIENT_TIMEOUT** / **TRANSPORT**; mint pbkdf2 same-row UPDATE is a confounder.

FIRST VISIBLE SATURATING RESOURCE: API QueuePool **at 100 only**. The **first** abnormal signal is messages **hold/checkout multiplicity** at 60 with peak 3/10.

ACTUAL ROOT CAUSE: Heavy admission counts **HTTP requests**, not **connection demand**. One messages handler performs ~60 QueuePool checkouts and can hold one connection for ~2s while doing timeline/lifecycle work. Uncapped Home summary and session mint add more demand. At 100 this fills 10/10 and critical walls fail. Not a leak. Not Postgres lock contention.

ROOT CAUSE: **PROVEN** (mechanism).  

RESOURCE LEAK: **NO**  
EQUILIBRIUM: **PASS**  
NEW INFRASTRUCTURE JUSTIFIED: **NO**  
SAFE TO DESIGN ROOT FIX: **YES**  
SAFE TO RERUN FIRST-100: **NO**  
SAFE TO RESUME VISUAL WORK: **NO**  

STOP.
