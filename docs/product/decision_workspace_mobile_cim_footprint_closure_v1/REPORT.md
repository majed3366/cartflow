# Decision Workspace — Mobile CIM Footprint Closure V1

**Status:** Living Store evidence captured — **STOP for real-device visual review**  
**Deploy:** `d52da0b`  
**Scope:** Mobile Commerce in Motion / evidence-field **vertical footprint only**

## Problem

Sparse `.cf2-evfield` used `min-height: 100px` + `gap: 16px`, creating a semi-empty band between «الأدلة ما زالت محدودة» and the first live evidence line.

## Fix (mobile Workspace only)

In `merchant_ui_v2_workspace.css` `@media (max-width: 1023px)`:

- Force `min-height: 0` on Workspace evidence fields (all densities)
- Compress gap / padding / bar height
- Keep bars + Living Route recognizable

**Not changed:** shell, hierarchy, copy, APIs, projection, desktop CIM (still `min-height: 100px` for sparse).

## Measured Living Store footprint

| Viewport | fieldHeight | gap confidence→first evidence | minHeight |
|----------|-------------|-------------------------------|-----------|
| Mobile 430 | **16px** | **24px** | 0px |
| Mobile 390 | **16px** | **24px** | 0px |
| Desktop | 100px | 114px | 100px (unchanged) |

All automated gates true — see `REGRESSION_RESULTS.md`.

## STOP

Last intended Workspace mobile composition refinement for this track.  
No PASS. No freeze. Await real-device visual review for final Workspace closure.
