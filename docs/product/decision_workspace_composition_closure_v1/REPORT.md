# Decision Workspace — Final Product Composition Closure V1

**Status:** Living Store evidence captured — **STOP for visual review** (no freeze)  
**Deploy:** `52c7981`  
**URL:** https://smartreplyai.net/dashboard#workspace  
**Shell:** Protected (`shell-integration-v1`) — UtilityRow / GlobalUpbar / ContextualSidebar / PageStage / nav behavior **unchanged**  
**Content marker:** `workspace-composition-closure-v1`

## Objective

Complete visual and product composition of Decision Workspace **on top of** the approved Merchant Shell — content stage only.

## What changed (content stage only)

| Change | Why |
|--------|-----|
| Desktop: decision mass larger than head title | CartFlow conclusion owns the field; head is stance lead — removes equal-weight double headline |
| Mobile: head title larger than mass echo | Glance decision first; mass confirms under «ما يقرره CartFlow» |
| Drop redundant «مستوى الثقة» evidence bullets | Strength owned by `.cf2-ws__confidence` |
| Next rows = column (title → link) | Clear secondary reading; no wrap scramble |
| Wait terminus lead + note | Clear «what to do now» when no action |
| Stage padding via `:has(workspace)` | Rhythm under shell chrome (fixed dead selector) |
| Marker `workspace-composition-closure-v1` | Evidence identity |

**Preserved:** projection API, decision logic, evidence lines (minus confidence duplicate), Commerce Objects (one silent mark), Living Route + terminus, Commerce in Motion (`is-arriving`, route taper, density), Home frozen.

**Not touched:** UtilityRow, GlobalUpbar, ContextualSidebar, PageStage structure, mobile/desktop nav behavior.

## Living Store evidence

| # | Shot | Path |
|---|------|------|
| 1 | Desktop Workspace — full page | `screenshots/01_desktop_workspace_full.png` |
| 2 | Mobile Workspace — top | `screenshots/02_mobile_workspace_top.png` |
| 3 | Mobile Workspace — mid scroll | `screenshots/03_mobile_workspace_mid.png` |
| 4 | Mobile Workspace — lower section | `screenshots/04_mobile_workspace_lower.png` |
| 5 | Mobile — contextual sidebar closed | `screenshots/05_mobile_contextual_closed.png` |
| 6 | Mobile — contextual sidebar open | `screenshots/06_mobile_contextual_open.png` |

Probe: `production_probe.json`  
Capture: `scripts/_capture_decision_workspace_composition_closure_v1.py`

## Gates (Living Store)

| Gate | Result |
|------|--------|
| deployOk (`52c7981`) | **true** |
| markerPresent | **true** |
| shellUntouched | **true** |
| noOverflowX desktop/mobile | **true** |
| noConfDup | **true** |
| hierarchyDesktop (mass ≥ title) | **true** |
| hierarchyMobile (title ≥ mass) | **true** |
| commerceInMotion (CO + evfield + route + terminus) | **true** |
| ctxClosedShot / ctxOpenShot | **true** |

## Acceptance question (for visual review)

Can a merchant understand:

1. what decision is being considered,  
2. why CartFlow is saying it,  
3. how strong the evidence is,  
4. what it means,  
5. and what they should do next,

without confusion or visual overload?

**Engineering posture:** composition closed for review. **No PASS / no freeze** until visual approval.

## STOP

No further navigation work. No new page work. Await visual review.
