# Merchant Surface Realization V1 — Production Visual Review

**Date (UTC):** 2026-07-22  
**PR:** [#57](https://github.com/majed3366/cartflow/pull/57) → `main` @ `b8400c67`  
**Production URL:** https://smartreplyai.net/dashboard  

## Deploy verification

| Check | Result |
|-------|--------|
| `merchant_experience_integration_v1.js` live (MSR markers) | **pass** |
| Home health / attention questions in JS | **pass** |
| Decision why / evidence / confidence cards | **pass** |
| Carts focus root consumer | **pass** |
| Communication as state | **pass** |
| MEIF / OT / TABF probes `ok` | **pass** |
| Foundations generators unchanged | **pass** (UI-only PR) |

Dashboard HTML requires merchant session (`/dashboard` → login). After login, MSR mounts paint from `/api/dashboard/summary` MEIF packages.

## Review stance

Success criterion is merchant understanding of underlying foundations—not cosmetic beauty.

Surfaces now lead with merchant questions and expose OT explainability / trust / chronology already present in MEIF packages.
