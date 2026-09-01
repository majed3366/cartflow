# Controlled Production Visual Fix V1 — Report

## Scope

Fix only founder-visible failures proven in Production Visual Falsification RCA V1 on:

Home · Workspace · Carts · Communication · Settings

**Preserved:** `merchant_ui_v2` shell, `merchant_app_v2.html` structure, `semantic-visual-model-v1`, page-specific organisms, QueuePool/DB ownership, Scheduler, autodeploy OFF, config parity gate.  
**No** new truth. **No** platform redesign. **Sidebar:** unchanged (APPROVED `.cf2-ctx` pattern).

---

## Fixes

| Surface | Change |
|---------|--------|
| **Settings** | Row padding uses longhands; `.row.ledger-row` reserve **34px** desktop / **32px** mobile (8 inset + joint + **8px min gap**). Joint size preserved (18 / 16). |
| **Workspace** | Void is interrupted route channel (dashed start-edge + spine stubs), not ellipse oval. Uncertainty→void mapping unchanged. |
| **Carts** | Single `.cf2-carts__withheld-mass` + rail; remove dual empty skeleton shells. |
| **Communication** | Empty copy: transparent, radius 0, start-edge only; scaffold remains. |
| **Home** | Mobile primary spine **5px** (was 8); satellites keep relational max-widths 92%/78%/64% + offsets. Desktop gravity **10px** preserved. |

Cache: `rdfix1-pvfix1` on V2 static assets.

---

## Blind-spot gates closed

`tests/test_controlled_production_visual_fix_v1.py` (PVFIX-01…07) + updated FRC mobile home assertions:

| Blind spot | Closed by |
|------------|-----------|
| Runtime overlap / collision | Settings reserve math + no padding shorthand |
| Min geometry/text separation | **8px** min gap encoded (34/32 pad) |
| Semantic geometry legibility | Void not oval; dashed channel + stubs |
| Empty-state page identity | Comms empty not surface card |
| Relative visual weight | Mobile spine 5px not 8px |
| Relationship visibility | Mobile satellite max-widths / offsets |
| Mobile transform survival | Relational widths survive `@media` |
| Production evidence sufficiency | RCA pack required (not pixel-perfect screenshots) |

**CONTRACT BLIND SPOTS CLOSED: 7 / 7**  
**REAL-DEVICE GATE BLIND SPOTS CLOSED: 5 / 5**

---

## Real-device review (candidate local)

| Item | Value |
|------|-------|
| Server | `127.0.0.1:8790` |
| Session | `/dev/living-store-home-review` |
| Env | `ENV=development`, `CARTFLOW_CART_WORKSPACE_V1=true`, UI V2 on |
| Viewports | Mobile 390×844 · Desktop 1280×900 |

| Check | Result |
|-------|--------|
| Settings mobile: padIS 32px, joint 16, gap text/chip **8px**, overlap **0** | PASS |
| Settings desktop: padIS 34px, joint 18, gap **8px**, overlap **0** | PASS |
| Workspace void: radius 0, not oval; sits between evidence→mass; remnant 32 / standard 44 | PASS |
| Carts withheld mass: transparent, dashed 4px, no skeleton shells | PASS |
| Comms empty: transparent, radius 0, scaffold present | PASS |
| Home mobile: spine **5px**; sat widths differ (e.g. 262 vs 182); maxW 92%/64% | PASS |
| Home desktop: spine **10px** | PASS |
| Sidebar `.cf2-ctx` | PRESERVED |

---

## FINAL REPORT

```
BASE SHA: c20627167c759145b65b591bc4df75a8dd6262a3

CANDIDATE SHA: (frozen at commit — see git log / pack stamp)

DIRECT PARENT: (parent of candidate commit)

SETTINGS COLLISION: PASS
WORKSPACE SEMANTIC LEGIBILITY: PASS
CARTS WITHHELD-STATE LEGIBILITY: PASS
COMMUNICATION EMPTY-STATE IDENTITY: PASS
HOME SPINE BALANCE: PASS
HOME SATELLITE RELATIONSHIP: PASS

SIDEBAR PATTERN PRESERVED: YES

CONTRACT BLIND SPOTS CLOSED: 7 / 7
REAL-DEVICE GATE BLIND SPOTS CLOSED: 5 / 5

SEMANTIC MODEL CHANGED: NO
NEW TRUTH INVENTED: 0

MOBILE: PASS
REAL-DEVICE REVIEW: PASS

SAFE FOR EXACT-SHA DEPLOY: YES

DEPLOYMENT PERFORMED: NO

STOP.
```
