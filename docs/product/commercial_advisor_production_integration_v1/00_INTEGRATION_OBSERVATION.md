# Commercial Advisor Production Integration V1 — Integration Observation

**Date (UTC):** 2026-09-04  
**Mode:** Observe before code  
**Logic baseline:** `b1867d2c` — FROZEN  
**Signature:** `cf-cda` FINAL PASS (lab V1.1.1 cohesion)

## Product surfaces

| Surface | DOM root | Painter | CSS |
|---------|----------|---------|-----|
| Merchant Shell | `merchant_app_v2.html` | shell modules | shell CSS — **do not redesign** |
| Home gravity well | `#cf2-home-root` → `.cf2-home[data-cf2-organism="gravity-well"]` | `merchant_ui_v2_home.js` | `merchant_ui_v2_home.css` |
| Home COL strip | sibling `section.cf2-col` **after** gravity section | `renderColLayer()` | `.cf2-col*` in home CSS |
| Decision Workspace | `#cf2-workspace-root` | `merchant_ui_v2_workspace.js` | `merchant_ui_v2_workspace.css` |
| Workspace COL | `section.cf2-col-ws` prepended when focus | `renderColDecision()` | `.cf2-col-ws*` |

## Commercial block ownership (today)

- **Data:** `summary.commercial_opportunity_layer_v1` from attach after OGL (flag-gated).
- **Flag:** `CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1` default OFF (`flag_v1.py`).
- **Home primary:** `.cf2-col__primary` — title + units why/move/measure/recheck + evidence `<details>`.
- **Home secondaries:** `.cf2-col__secondary` — lighter; no `cf-cda`.
- **Workspace:** `sessionStorage cf2_col_focus_v1` → decision/why/do/dont/measure/recheck units.
- **`cf-cda`:** lab-only (`commercial_advisor_visual_identity_v1_1_1.*`); **not** linked from merchant shell.

## Operational ≠ Commercial

| Operational | Commercial |
|-------------|------------|
| Gravity well / OGL «ما الذي يحتاج انتباهي الآن؟» | COL «أين توجد أهم فرصة تجارية الآن؟» |
| Inside `.cf2-home` | Sibling `.cf2-col` outside gravity |
| Must remain primary operational truth | Must not visually merge into Needs You |

## Evidence disclosure

Home + Workspace COL: `<details>` collapsed by default; expand on user gesture.

## Mobile breakpoints

- Shell / home stage: `1024px` / `1023px`
- COL tighten: `max-width: 430px`
- Founder capture: **390** / **1280**

## Flag path

```
ENV CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1
  → attach_commercial_opportunity_layer_to_summary_v1
  → summary.commercial_opportunity_layer_v1
  → renderColLayer / (focus →) renderColDecision
```

Flag OFF: strip absent; rollback = leave flag OFF (no CSS/JS required for absence).

## Collision risks

1. Gravity-well mass vs CDA spine — mitigate: keep COL **outside** `.cf2-home`.
2. Shell / sidebar / mobile edge — CDA must not expand past content column.
3. Double identity (old `.cf2-col` chrome + CDA) — mitigate: CDA owns primary/workspace mass; keep strip question + secondaries chrome.
4. Lab CSS leaking lab page chrome (`.cavi-lab`) — mitigate: production CSS subset scoped under `[data-cf-ui="v2"] .cf-cda`.

## Rollback boundary

- Flag OFF restores pre-CDA COL absence (and if flag ON with old paint: revert home/workspace JS + drop CDA static link).
- No DB / scheduler / COL compose changes in this task.
- No Railway / env mutation in this task.

## Integration ownership (authorized)

| Layer | Owner this task |
|-------|-----------------|
| COL compose / ranking / truth | **FROZEN — do not touch** |
| Home primary paint | `merchant_ui_v2_home.js` + production CDA CSS/JS |
| Workspace COL paint | `merchant_ui_v2_workspace.js` + same |
| Shell / OGL / gravity | **untouched** |
| Lab routes | untouched (remain for reference) |
