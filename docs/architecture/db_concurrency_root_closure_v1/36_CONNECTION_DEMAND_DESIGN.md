# Connection-demand design (Options A–E)

**Status:** Selected **E = A + B**. C and D deferred (not required after demand reduction).  
**Date (UTC):** 2026-08-30  
**Law:** eliminate unnecessary DB demand before limiting users.

## Options

| Option | What | Decision |
|--------|------|----------|
| **A — Materialize once** | One bounded DB phase → plain row dicts → `close_request_uow_if_clean` → last_send / JSON compose | **DO** |
| **B — Bounded batch reads** | Skip post-schema `inspect.has_table`; one timeline IN; one schedule IN; keep existing log/delivery/reply batches | **DO** |
| **C — Weighted admission** | `messages = measured_weight` | **NOT NOW.** After A+B, remaining demand is one scoped-session checkout reused for the DB phase — same class as other heavy GETs. `try_acquire` cost stays 1 until a new measurement shows a material remaining multiplier. |
| **D — Critical reservation** | Extra reserved slots beyond HEAVY 4/2 | **NOT NOW.** HEAVY_GLOBAL_LIMIT=4 already leaves 6 of 10 for login/health/Home/navigation. Extra reservation would starve normal product reads. |
| **E — Combination** | A+B first; C/D only if evidence remains | **SELECTED** (A+B only) |

## Why not C/D first

Admission throttling must not hide an inefficient query/use pattern. The proven 61-checkout / 2.1s hold is inspect N+1 + spanning session hold, not “too many merchants.”

## Admission model after A+B

| | Before | After |
|--|--------|--------|
| Unit | 1 HTTP request | 1 HTTP request, documented as matching remaining connection demand (1 scoped checkout) |
| Heavy set | messages / followups / normal-carts | unchanged |
| Global / per-route | 4 / 2 | unchanged |
| Reject | before DB | before DB |
| Messages weight | implicit 1 (wrong vs ~60 checkouts) | explicit 1 (justified after multiplicity removal) |
| Extra critical reserve | none (heavy cap only) | none (heavy cap sufficient) |

## Non-changes

QueuePool 5+5+5s. Scheduler 2/2. No Redis/PgBouncer/replicas. Merchant-visible row fields unchanged.
