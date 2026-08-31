# Merchant Platform Visual Assimilation Production Closure V1

**Date (UTC):** 2026-08-31  
**Previous production SHA:** `2bf18ebcdff069a1b16a7a896b6f6ecb494b92e8`  
**Final candidate / live SHA:** `de0997ee81d13b4be70128dd1ec0eb36b7c7d69a`  
**Deployment ID:** `6f1b9786-8e3a-4f15-9d0d-d333c672157d`  
**Deploy:** SUCCESS at `2026-08-31T04:52:46.467Z` (`serviceInstanceDeployV2` + exact `commitSha`; not `railway up`)  
**Autodeploy:** OFF  
**Scheduler:** `2b1e5665` / `f91e799d` unchanged  

## Lineage audit (`2bf18ebc` → `de0997ee`)

### `4c5ba5e3b4bf611c3f12c7b382b9b3acf329c776`

| File | Class |
|------|-------|
| `static/merchant_ui_v2_carts.css` | VISUAL_ASSIMILATION |
| `static/merchant_ui_v2_comms.css` | VISUAL_ASSIMILATION |
| `static/merchant_ui_v2_settings.css` | VISUAL_ASSIMILATION |
| `templates/merchant_app_v2.html` | MECHANICAL_CACHE_BUST |
| `tests/test_merchant_platform_visual_assimilation_reconciliation_v1.py` | TEST |
| `tests/test_settings_narrow_visual_refinement_v1.py` | TEST |
| `docs/SYSTEM_SUMMARY.md` | DOCUMENTATION |
| `docs/product/.../REPORT.md` | DOCUMENTATION |

### `011f7d8b1c12942f863527366fcae7847a6313aa`

| File | Class |
|------|-------|
| `docs/product/.../REPORT.md` | DOCUMENTATION |

### `de0997ee81d13b4be70128dd1ec0eb36b7c7d69a`

| File | Class |
|------|-------|
| `static/merchant_ui_v2_{carts,comms,settings}.css` | VISUAL_ASSIMILATION |
| `templates/merchant_app_v2.html` | MECHANICAL_CACHE_BUST |
| residual tests + review script | TEST |
| residual REPORT/REVIEW/pngs + SYSTEM_SUMMARY | DOCUMENTATION |

**UNRELATED_RUNTIME_CHANGE: 0**  
No `main.py` / `models.py` / `services/` / `routes/` / QueuePool / admission / Scheduler / session files.

## Candidate integrity

HEAD was `de0997ee` with a clean tree. Visual residual + Settings contracts **23/23 PASS**.

## Live identity

`GET https://smartreplyai.net/` → `X-CartFlow-Git-Sha: de0997ee81d13b4be70128dd1ec0eb36b7c7d69a`  
Dashboard HTML contains `resid1` / `assim1` / `qpool1`. Served CSS: no teal inset, Carts selected navy start, Settings rows transparent, no dashed empties.

## Production baseline

`/ping` `/health` `/health?db=1` `/login` = 200. QueuePool 5+5, `timeout_count=0`, `checked_out=0`, unexpected IIT = 0.

## Visual parity

Rendered evidence: `review/`.

- **Carts:** Living Store queue was incomplete-truth empty (`تعذر تأكيد الطابور`) — M1 solid open-start object, no dashed shell. Selected-row R1 proven by live CSS (navy start, no teal inset). No rows to click; not a visual regression.
- **Communication:** Non-empty history. List unboxed; selected navy start-edge; detail transparent with one start-edge. Not an inbox.
- **Settings:** Overview rows transparent / start-edge; selected navy; needs amber; detail one quiet edge; inner forms unchanged.

Mobile: no overflow. Settings overview → store detail → back. Communication is a history list. Carts empty object; detail/back not exercisable without a queue row.

Post-smoke: `checked_out=0`, IIT=0, timeout=0, peak 3 during surface visits, holders=0.

**MERCHANT PLATFORM VISUAL ASSIMILATION: CLOSED IN PRODUCTION**
