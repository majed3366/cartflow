# Root cause

## Proven (code + incident evidence)

**Primary cause:** the request-scoped `scoped_session` is opened on first touch (almost always merchant-auth user/store resolve) and is held until middleware `finally`. Hold time ≈ **request wall time after first checkout**, not query time.

That architecture, on a **5+5** pool, is sufficient for normal merchant activity to exhaust the pool:

1. Auth checkout happens **before** heavy-route admission (INV-DB-08 violated on `c453d336` before this pack).
2. Communication / Workspace / Carts can run concurrently (tabs, mobile+desktop).
3. Serialization and remaining provider I/O (VIP poll) extend the hold (H1, H3, H2).
4. `/health?db=1` and `/login` share the same pool → unrelated unavailability.

This is **not** a classic leaked connection that never returns. Incidents recovered without restart once traffic stopped (INV-DB-10 historically PASS for Settings). It **is** a lifecycle/ownership defect: the connection is correctly returned *late*.

## Not the root cause

| Hypothesis | Status |
|------------|--------|
| Pool too small — enlarge 5+5 | **Rejected.** Constitution: do not hide hold-time defects. |
| Scheduler contention | **Falsified** for Aug 29–30 (Scheduler unchanged / jobs OFF). |
| Postgres down | **Falsified** (DB healthy; API pool timeout). |
| Instrumentation-only false saturation | **Partial.** `pool.status()`-only snapshot hid numeric `checked_out` in one helper; incidents still had real 503s. |
| Single Settings route only | **Falsified.** Recurred after Settings remediation (dashboard fan-out; then First-100 still NOT_CLOSED). |

## Supporting evidence

- First-100 audit: “Hold time ≈ request duration after first checkout”
- Auth: `resolve_authenticated_store_slug` → `get_merchant_user_by_id` (DB) inside middleware wrapping every dashboard request
- Ownership audit: no request-level UoW; `j()` previously serialized while session open
- VIP poll: Twilio fetch + `time.sleep` while session could remain open (closed in this pack)

## Invariants that prevent recurrence

INV-DB-01, 02, 03, 07, 08, 09, 11, 12 — see `02_INVARIANTS.md` and `19_ADR_DB_RESOURCE_MODEL.md`.
