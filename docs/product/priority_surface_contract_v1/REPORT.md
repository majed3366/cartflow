# Priority Surface Contract V1 — REPORT

**Date (UTC):** 2026-09-06  
**Mode:** Controlled minor product integration  
**Deploy:** NO  

## Law

| Lane | Owner | Merchant label |
|------|-------|----------------|
| Commercial Priority | `mission_catalog_v1` | **المهمة التجارية الحالية** |
| Operational Obligation | OGL / executive publication (HES gravity) | **إجراء تشغيلي مطلوب** |

- Open CDC dominates continuity **inside the commercial lane only**.
- Operational obligations **do not** consume Mission Portfolio capacity.
- `col_only` families (e.g. `communication_followup`) are **not** painted as commercial mission primary/secondaries.

## What changed

| Area | Change |
|------|--------|
| `static/merchant_ui_v2_home.js` | Lane labels; suppress competing “most important” headings; mission_ready commercial filter |
| `static/merchant_ui_v2_workspace.js` | Commercial Console vs operational card labels; mission_ready Console gate |
| `static/merchant_ui_v2_workspace.css` | Minimal `.cf2-ws__lane` (existing type scale) |
| `templates/merchant_app_v2.html` | Cachebust `psc1` |

## What did **not** change

Mission Catalog ranking · CDC · Portfolio · OGL pick order · HES gravity selection · COL compose/truth · schema · Scheduler · AI/external · query delta

## Reality scenarios (gate)

| ID | Result |
|----|--------|
| A contact ops + merchandising commercial | PASS |
| B shipping/hesitation ops attention + price commercial | PASS |
| C open CDC commercial + independent contact ops | PASS |
| D commercial insufficient + ops | PASS |
| E commercial mission only | PASS |
| F operational obligation only | PASS |

Gate: `tests/test_priority_surface_contract_v1.py` (+ projection string updates).

## Screenshots

Canonical: `docs/product/priority_surface_contract_v1/founder_review_v1/`  
Desktop: `C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Priority_Surface_Contract_V1\`

1. `01_home_two_lane_mobile.png`
2. `02_home_commercial_only_mobile.png`
3. `03_home_operational_only_mobile.png`
4. `04_workspace_two_lane_mobile.png`
5. `05_home_two_lane_desktop.png`
6. `06_workspace_two_lane_desktop.png`

---

## FINAL REPORT

```
COMMERCIAL PRIORITY OWNER:
mission_catalog_v1

OPERATIONAL OBLIGATION OWNER:
operational_guidance_v1 / executive publication (HES gravity)

ACTIVE CDC DOMINANCE:
PASS

OPERATIONS CONSUME MISSION CAPACITY:
NO

HOME TWO-LANE CONTRACT:
PASS

WORKSPACE TWO-LANE CONTRACT:
PASS

TWO COMPETING "MOST IMPORTANT" HEADINGS:
0

FRONTEND RANKING LOGIC:
0

MISSION RANKING CHANGED:
NO

OGL LOGIC CHANGED:
NO

CDC CHANGED:
NO

PORTFOLIO CHANGED:
NO

AI CALLS:
0

EXTERNAL API CALLS:
0

NEW SCHEDULER WORK:
0

NEW DB TABLE:
NO

QUERY DELTA:
0

N+1:
0

REALITY SCENARIOS:
6 PASS (A–F)

SCREENSHOTS:
6

FOUNDER DESKTOP PATH:
C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Priority_Surface_Contract_V1

DESKTOP COPY READY:
YES

READY FOR FOUNDER PRODUCT REVIEW:
YES

DEPLOY:
NO
```

STOP.
