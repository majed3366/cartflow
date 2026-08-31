# Merchant Platform Visual Assimilation Production Reconciliation V1

**Date (UTC):** 2026-08-31  
**Base / live production SHA:** `2bf18ebcdff069a1b16a7a896b6f6ecb494b92e8`  
**New candidate SHA:** see git HEAD of `feat/merchant-platform-visual-assimilation-reconciliation-v1`  
**Old visual candidate (do not deploy):** `9d078cc0a3eba47c327374da8b9e21451e07e140`  
**Old visual ancestor:** `58a82f344cd3ba92c737cc7448e7e9d05910211f`  
**Mode:** audit → surgical port of approved M1–M3 only. No deploy.

## Phase 1 — historical visual hunk inventory

`git diff 58a82f3…9d078cc` touched 9 files. Classified hunks:

| # | Hunk | Class | vs `2bf18ebc` |
|---|------|-------|----------------|
| 1 | Carts `.cf2-carts__empty` dashed → solid + open-start edge | VISUAL_M1 | STILL_NEEDED / SAFE_TO_PORT |
| 2 | Communication `.cf2-comms__empty` same | VISUAL_M1 | STILL_NEEDED / SAFE_TO_PORT |
| 3 | Settings overview/detail selector split | VISUAL_M3 | STILL_NEEDED / SAFE_TO_PORT |
| 4 | Settings detail one object edge | VISUAL_M3 | STILL_NEEDED / SAFE_TO_PORT |
| 5 | Settings row transparent start edge | VISUAL_M2 | STILL_NEEDED / SAFE_TO_PORT |
| 6 | Settings `is-needs` amber start | VISUAL_M2 | STILL_NEEDED / SAFE_TO_PORT |
| 7 | Settings `is-selected` navy start; remove teal inset | VISUAL_M2 | STILL_NEEDED / SAFE_TO_PORT |
| 8 | Settings `is-selected.is-needs` navy wins | VISUAL_M2 | STILL_NEEDED / SAFE_TO_PORT |
| 9–11 | `merchant_app_v2.html` CSS cache `-assim1` | MECHANICAL | STILL_NEEDED |
| 12 | Settings refinement test dual-teal assertion | MECHANICAL | STILL_NEEDED |
| 13 | Old LOCAL_REVIEW / follow-up JSON | UNRELATED / STALE | REJECTED (old SHA screenshots) |
| 14 | Old implementation REPORT | STALE | Rewritten as this pack |
| 15 | Old `test_merchant_platform_visual_assimilation_implementation_v1.py` | MECHANICAL | Reimplemented on current line |

**OLD VISUAL HUNKS REVIEWED: 15**  
**PORTED: 12** (1–12)  
**ALREADY PRESENT: 0**  
**OBSOLETE: 0**  
**REJECTED AS STALE: 3** (13–15 originals; tests/docs rewritten)

No hunk was CONFLICTING_WITH_CURRENT_PRODUCTION. Surrounding CSS on `2bf18ebc` still matched the old visual base for these selectors.

## What was not ported

- Home CSS / JS  
- Decision Workspace CSS / JS  
- Shell / frame CSS  
- Product / carts / comms / settings semantics or fetch paths  
- DB / QueuePool / admission / Scheduler / Reality Simulator  
- Whole-commit cherry-pick of `9d078cc`

## Structural law

Carts and Communication empties (including loading copy that uses the same empty class) are truthful solid objects with a quiet navy open-start — not dashed placeholders. Settings overview rows stay surface cards; attention and selection are start-edge only (no teal inset + navy outline collision). Settings detail has one object edge; inner `.setting-card` / `.ma-fw-card` stay 1px quiet borders.

## Operational preservation

`settings-queuepool-pressure-remediation-v1`, no Settings `Promise.all`, `SURFACE_PRODUCT_INIT`, `settingsSurfaceActive()`, cache tokens `qpool1` / `nvis1-fanout1` remain.
