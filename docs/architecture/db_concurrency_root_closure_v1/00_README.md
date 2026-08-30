# Database Concurrency & Connection Lifecycle Root Closure V1

**Status:** Request-scoped ownership class **closed in production**. Startup unowned hold remains. First-100 / visual paused.  
**Live SHA:** `76c0d4111afe5fedeb8e3f4fc24b7ede7915f9ab`  
**Branch:** `feat/db-concurrency-root-closure-v1`  
**Date (UTC):** 2026-08-30

This pack closes the *class* of failures in which normal merchant request activity can exhaust the API QueuePool and make unrelated traffic unavailable.

It is **not** another route patch, pool-size change, visual task, or First-100 soak.

## Binding predecessor

First-100 DB Resource Safety V1 (`docs/architecture/first_100_db_resource_safety_v1/`) is on this SHA. It added hold-budget classes, heavy-route admission *inside* some handlers, and release-before-wait at WhatsApp / Zid / password-reset. Its own verdict was **NOT_CLOSED**: local proof used NullPool; production mixed-surface verification did not run.

This program treats that work as **partial containment**, not root closure.

## Engineering sequence

OBSERVE → REPRODUCE → HYPOTHESES → FALSIFY → ROOT CAUSE → INVARIANTS → DESIGN → IMPLEMENT MINIMALLY → FAILURE TESTS → EQUILIBRIUM → (deploy only when authorized) → PRODUCTION VERIFY → CLOSE

## Pool law (unchanged)

API QueuePool remains `pool_size=5`, `max_overflow=5`, `pool_timeout=5s`. Do not enlarge to hide hold-time defects.

## Document index

| File | Phase |
|------|--------|
| [01_INCIDENT_BASELINE.md](01_INCIDENT_BASELINE.md) | 0 Freeze |
| [02_INVARIANTS.md](02_INVARIANTS.md) | 1 Binding invariants |
| [03_OBSERVABILITY_CONTRACT.md](03_OBSERVABILITY_CONTRACT.md) | 2 Observe before fix |
| [04_POSTGRES_SQLALCHEMY_RECONCILIATION.md](04_POSTGRES_SQLALCHEMY_RECONCILIATION.md) | 3 Both-sides truth |
| [05_MINIMAL_REPRODUCTION.md](05_MINIMAL_REPRODUCTION.md) | 4 Smallest failure |
| [06_HYPOTHESIS_MATRIX.md](06_HYPOTHESIS_MATRIX.md) | 5 H1–H10 |
| [07_SESSION_OWNERSHIP_AUDIT.md](07_SESSION_OWNERSHIP_AUDIT.md) | 6 Ownership |
| [08_STATIC_LIFECYCLE_AUDIT.md](08_STATIC_LIFECYCLE_AUDIT.md) | 8 Static violations |
| [09_ROOT_CAUSE.md](09_ROOT_CAUSE.md) | Proven cause |
| [10_REMEDIATION_DESIGN.md](10_REMEDIATION_DESIGN.md) | 7 Design |
| [11_IMPLEMENTATION_REPORT.md](11_IMPLEMENTATION_REPORT.md) | What changed |
| [12_QUERY_SAFETY.md](12_QUERY_SAFETY.md) | 10 Query bounds |
| [13_CONCURRENCY_MODEL.md](13_CONCURRENCY_MODEL.md) | 11 Classes + admission |
| [14_FAILURE_INJECTION.md](14_FAILURE_INJECTION.md) | 12 Cleanup under failure |
| [15_EQUILIBRIUM_HARNESS.md](15_EQUILIBRIUM_HARNESS.md) | 13 Permanent harness |
| [16_LOCAL_VALIDATION.md](16_LOCAL_VALIDATION.md) | 14 QueuePool local |
| [17_PRODUCTION_VALIDATION.md](17_PRODUCTION_VALIDATION.md) | 16 Not run until authorized |
| [18_FIRST_100_VALIDATION.md](18_FIRST_100_VALIDATION.md) | 17 Paused |
| [19_ADR_DB_RESOURCE_MODEL.md](19_ADR_DB_RESOURCE_MODEL.md) | 18 Binding ADR |
| [20_FINAL_VERDICT.md](20_FINAL_VERDICT.md) | Acceptance |
| [21_RESIDUAL_CHECKOUT_OWNER.md](21_RESIDUAL_CHECKOUT_OWNER.md) | Residual owner ID |
| [22_OWNERSHIP_INVARIANTS.md](22_OWNERSHIP_INVARIANTS.md) | INV-OWN-01…08 |
| [23_SESSION_MODEL_AUDIT.md](23_SESSION_MODEL_AUDIT.md) | Pre-fix session model |
| [24_OWNERSHIP_DESIGN.md](24_OWNERSHIP_DESIGN.md) | Design A/B/C |
| [25_STATIC_OWNERSHIP_SEARCH.md](25_STATIC_OWNERSHIP_SEARCH.md) | Residual thread-local search |
| [26_OWNERSHIP_ROOT_FIX.md](26_OWNERSHIP_ROOT_FIX.md) | Local candidate |
| [27_PRODUCTION_OWNERSHIP_PROOF.md](27_PRODUCTION_OWNERSHIP_PROOF.md) | Production proof |
| [28_STARTUP_UNOWNED_OWNER.md](28_STARTUP_UNOWNED_OWNER.md) | Startup leftover owner |
| [29_STARTUP_INVARIANTS.md](29_STARTUP_INVARIANTS.md) | INV-START-01…06 |

## Process isolation

Scheduler is unchanged. Autodeploy remains OFF. Visual work remains paused. No deploy from this pack until explicitly authorized.
