# Phase 11 — API concurrency model

Pool remains **10** API connections (5+5). Scheduler separate.

| Class | Examples | Rule |
|-------|----------|------|
| **critical** | `/ping`, `/health` (no db), `/login`, cookie parse, auth identity resolve | Never heavy-admitted. Auth is a short DB phase. Health pool snapshot is in-process only. |
| **normal** | Home summary, Settings overview, carts detail after list | One checkout at a time per request after identity close. |
| **heavy** | `/api/dashboard/messages`, `/followups`, `/normal-carts`; Workspace enrich on cache miss | Global **4**, per-route **2**. Middleware admits messages/followups/normal-carts **before** auth DB. Projection admits in handler on miss only. |
| **background** | refresh-state, diagnostics, evidence flags OFF | First to 503 / empty / STALE. |

## Admission rejection

- HTTP **503** `{ok:false, error:db_pressure}` for authenticated heavy GET
- Cookie-less heavy GET: **401** without checkout
- Client: degrade / show empty / retry later — do not stampede
- Rejection does not checkout (INV-DB-08)

## Per-merchant limit

Not implemented. Shared pool isolation remains **PARTIAL**. Justified: one-merchant incidents already saturate; per-merchant semaphores need evidence after short-hold is proven in production.

## Retry

No server retry of rejected heavy reads. Clients must not `Promise.all` a rejected storm.
