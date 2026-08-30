# Phase 17 — First-100 validation

**Run:** 2026-08-30 on live `f613ec7145a5e29c56257187159bfe366c26b3c0` (deploy `bc48e3dd`).  
**Mode:** validation only. Pack: [32_FIRST_100_OPERATIONAL_SCALE.md](32_FIRST_100_OPERATIONAL_SCALE.md).

| Stage | Status |
|-------|--------|
| 10 | **PASS** — peak `checked_out=3`, TTE immediate, timeouts 0 |
| 25 | **PASS** — peak 6, TTE immediate, timeouts 0 |
| 50 | **PASS** — peak 4, TTE immediate, timeouts 0 |
| 100 | **FAIL** — peak 10/10, 6 critical + 6 unexpected 5xx/transport, 11 slow 503s; timeouts 0; equilibrium still 0 |

Highest proven safe stage: **50**. Isolation at 50: **PASS**. Post-test regression: **PASS**.  
First-100 operational scale safety: **NOT_CLOSED**. Visual remains paused.

Local NullPool 10/25/50/100 claims from the older First-100 pack remain **not** accepted.
