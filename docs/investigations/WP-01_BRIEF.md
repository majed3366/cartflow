# Work Package Brief — WP-1

| Field | Value |
|-------|-------|
| Investigation ID | INV-001 |
| Work Package ID | WP-1 |
| Title | Platform Time Authority Foundation |
| Severity | Critical |
| Author | Engineering |
| Date opened (UTC) | 2026-07-16 |
| Branch | `feature/inv001-wp1` |
| Depends on | DoR Certification READY FOR WP-1 |
| Start authorized | Yes (task: READY FOR WP-1) |

## Objective

Introduce `services/time_authority/` as a first-class platform capability (authority, providers, query context, contracts, validators, compat) with **no consumer migration** and **no production behaviour change**.

## Scope

**In:** Package, public façade, clock providers, Query Time Context, DI/contextvars binding, compat layer, unit tests.

**Out:** Knowledge/Dashboard/Timeline/PT/Monthly/Attention/Simulation migration; filtering recipes (WP-3); HTTP middleware (WP-2 composition); `main.py` logic.

## Rollback

Revert branch / delete `services/time_authority/` + tests. No production consumers yet.

## Regression risk

None (additive only).

## `main.py`

Untouched.
