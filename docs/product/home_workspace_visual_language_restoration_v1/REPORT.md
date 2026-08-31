# Home & Decision Workspace Visual Language Restoration V1

**Date (UTC):** 2026-08-31  
**Status:** LOCAL CANDIDATE — NO DEPLOY  
**Base production SHA:** `de0997ee81d13b4be70128dd1ec0eb36b7c7d69a`  
**Direct parent (branch HEAD before this commit):** `5a612d0f52d0efa638360568ce100bdb86bb4366`  
**LKG SHA:** `41777ae8c8a51bd44c6e3d7f02189eea8dec504e`  
**First deployed family:** `8bf7a827`

This is a controlled restoration of proven visual vocabulary into the **current** Home board and Workspace Decision Object. Not a historical revert. Shell, data contracts, and product semantics stay authoritative.

---

## Phase 1 — Restoration invariants

| ID | Invariant | Held |
|----|-----------|------|
| INV-VR-01 | Current product semantics are authoritative | YES |
| INV-VR-02 | Current data contracts are authoritative | YES |
| INV-VR-03 | Current Merchant Shell is unchanged | YES |
| INV-VR-04 | Only LKG-proven primitives restored | YES |
| INV-VR-05 | Primitives communicate current truth; no fake evidence | YES |
| INV-VR-06 | Home and Workspace remain different compositions | YES |
| INV-VR-07 | Mobile keeps the language structurally | YES |
| INV-VR-08 | No DB / session / QueuePool / Scheduler / admission change | YES |

---

## Phase 2 — LKG primitive inventory (`41777ae8`)

| # | Primitive | Classification | Surface |
|---|-----------|----------------|---------|
| 1 | Commerce Object rail / `.cf2-co-row` | **CANONICAL_AND_RESTORABLE** | Home + Workspace |
| 2 | Evidence Density / `.cf2-evfield` | **CANONICAL_AND_RESTORABLE** | Home + Workspace |
| 3 | Momentum Trace / `.cf2-mtrace` | **HOME_ONLY** · **DATA_CONTRACT_DEPENDENT** | Home |
| 4 | Living Route / `.cf2-route` | **WORKSPACE_ONLY** | Workspace (already on current line) |
| 5 | Decision Mass / `.cf2-dmass` | **WORKSPACE_ONLY** | Workspace (already on current line) |
| 6 | Decision densification (`is-forming` / `is-ready`) | **WORKSPACE_ONLY** | Workspace (already on current line) |
| 7 | Decision tension / `[data-cf2-tension]` | **CANONICAL_AND_RESTORABLE** | Both (already on current line) |
| 8 | Recovery / wait / `.cf2-reason__wait` | **WORKSPACE_ONLY** | Workspace (already on current line) |
| 9 | Core Silence / `cf2-dobj--quiet` | **WORKSPACE_ONLY** | Workspace (already on current line) |
| 10 | Knowledge Capsule / `.cf2-capsule` | **HOME_ONLY** | Home monitor items |
| 11 | `مركز الجاذبية` | **HOME_ONLY** | Home |
| 12 | `مشهد تنفيذي` + spine | **HOME_ONLY** | Home |
| 13 | `cf2-scene` two-column gravity + density aside | **OBSOLETE** vs current one-scene board | Home LKG layout |
| 14 | Vertical 88px poster rail | **DECORATIVE_ONLY** on current architecture | LKG column |
| 15 | Directional start / open-start board | **CANONICAL_AND_RESTORABLE** | Already current |
| 16 | Open-C / taper / scoop | **CANONICAL_AND_RESTORABLE** | Language CSS + Home taper restored |

**LKG PRIMITIVES INVENTORIED: 16**

---

## Phase 3 — Current renderer map (`de0997ee`)

| Surface | Data input | Semantic block | Primitive before | After |
|---------|------------|----------------|------------------|-------|
| Home | `GET /api/dashboard/summary` → `home_executive_summary_v1` | primary / know / watch / learning | silent clipped CO + bars + stance | + labeled CO family, spine, gravity, momentum, capsules |
| Workspace | `GET /api/cart-workspace/v1/projection` → `zone_b` | Decision Object + next | silent mark + route + dmass | + visible `cf2-co-row` from `mapWorkspaceObjects` |
| Shell | template + `merchant_ui_v2_app.js` | UtilityRow / GlobalUpbar / ContextualSidebar | current | **unchanged** |
| Language | `CartFlowUiV2Lang` | helpers | present, unused by Home | Home/WS call helpers again |

---

## What was restored / not restored

**RESTORED (8 named restorations):**

1. Commerce Object family (`.cf2-co-row`) on Home and Workspace  
2. Home Evidence Density remains and stays visible when truth is weak  
3. Momentum Trace when ≥2 real HES lanes exist  
4. `مشهد تنفيذي` spine  
5. `مركز الجاذبية`  
6. Knowledge-capsule grammar on Home monitor items  
7. Home taper  
8. Workspace visible CO family (`mapWorkspaceObjects`, max 3)

**NOT RESTORED (7):**

1. LKG `cf2-scene` two-column gravity/density — would undo current executive board (INV-VR-01/06)  
2. Vertical 88px poster rail — decorative on current one-column stage  
3. LKG single App Bar — INV-VR-03  
4. LKG `split()` without `isDuplicateTruth` — stale product grouping  
5. LKG hardcoded `عرض التفاصيل ←` — current weak/ready labels stay  
6. Full CO gallery on Workspace next-cards — would clone Home  
7. Fake momentum / fabricated dense Evidence Field when lanes or evidence are absent  

---

## Hunk classification

| File | Class |
|------|--------|
| `static/merchant_ui_v2_home.js` | HOME_VISUAL_RESTORATION |
| `static/merchant_ui_v2_home.css` | HOME_VISUAL_RESTORATION |
| `static/merchant_ui_v2_workspace.js` | WORKSPACE_VISUAL_RESTORATION |
| `static/merchant_ui_v2_workspace.css` | WORKSPACE_VISUAL_RESTORATION |
| `templates/merchant_app_v2.html` | MECHANICAL_CACHE_BUST (`langrest1`) |
| `tests/test_home_workspace_visual_language_restoration_v1.py` | TEST |
| `docs/product/home_workspace_visual_language_restoration_v1/` | DOCUMENTATION |
| `scripts/_capture_home_workspace_visual_language_restoration_v1.py` | DOCUMENTATION |
| `scripts/_capture_workspace_fixture_langrest_v1.py` | DOCUMENTATION |

`merchant_ui_v2_language.js` / `.css` / `merchant_ui_v2_app.js` / `merchant_ui_v2_frame.css` / carts / comms / settings / DB / admission: **unchanged**.

**UNRELATED RUNTIME CHANGES: 0**

---

## Incomplete-truth behavior

| Truth | Home | Workspace |
|-------|------|-----------|
| FULL | Rail from `mapHomeObjects`; momentum if ≥2 lanes; denser field | CO family + ready mass / armed terminus |
| PARTIAL | Rail + gathering/aligned field + current stance | CO family + forming mass |
| INCOMPLETE | Rail includes insufficient/uncertainty; sparse field; no invented extra bars | CO family from tension; wait copy; sparse field from real line count |
| EMPTY | Spine + `attention`/`insufficient` row + current empty copy; **no** fabricated density field | Quiet object: `attention` / `insufficient` / `waiting` + Core Silence route |

Rendered Living Store Home (incomplete): spine, three COs (انتباه / أدلة ناقصة / عدم يقين), gravity, sparse bars, `دليل — قرار` momentum, current stance. Identity holds.

---

## Phase 11 — Rendered A/B

| View | LKG reference | Current (`de0997ee`) | Restored candidate |
|------|---------------|----------------------|--------------------|
| Home desktop | `merchant_ui_v2_visual_language_maturity_v1/09_desktop_home.png` | production-closure `desktop_home_ref.png` | `review/desktop_home.png` |
| Home mobile | maturity `11_mobile_home.png` | residual `mobile_home_ref.png` (loading) | `review/mobile_home.png` |
| Workspace desktop | maturity `10_desktop_workspace.png` | production-closure operational card | live load error `desktop_workspace.png`; renderer fixture `desktop_workspace_fixture.png` |
| Workspace mobile | maturity `12_mobile_workspace.png` | residual error | live load error `mobile_workspace.png`; renderer fixture `mobile_workspace_fixture.png` |

**WHAT was lost?** Home CO rail / gravity / momentum / spine; Workspace visible CO family.

**WHAT was restored?** Those emitters on the current board / Decision Object.

**WHAT intentionally remains current?** V1.3 one-scene Home board, HES split + stance labels, Workspace operational route/mass, Merchant Shell, `SURFACE_PRODUCT_INIT`.

**WHAT was intentionally NOT restored?** LKG two-column Home, poster rail, old App Bar, stale copy/grouping.

Local Workspace **projection** still fails (`تعذّر تحميل مساحة القرار`) — same as prior residual/production-closure local reviews. Error copy and fetch path are unchanged. Fixture paint proves the restored compositor (`rail=1 route=1 dmass=1 evfield=1`).

---

## Logo-hidden

Home again carries labeled Commerce Objects, gravity, momentum, and open-C glyphs. Workspace Decision Object (when painted) carries the CO family + living route + mass. Carts / Communication / Settings keep assimilated open-start grammar. Without the wordmark, Home + Workspace are the identity anchors.

---

## Operational smoke

`ENV=development` pytest: restoration suite + `test_merchant_ui_v2` + residual + assimilation = **38 passed**.

Dashboard HTML hosts `langrest1`, UtilityRow, ctx handle. `SURFACE_PRODUCT_INIT` / active-only startup unchanged. Messages read-model / request UoW / QueuePool markers (`qpool1`) unchanged. No First-100 rerun.

---

## FINAL REPORT

```
BASE SHA: de0997ee81d13b4be70128dd1ec0eb36b7c7d69a
LKG SHA: 41777ae8c8a51bd44c6e3d7f02189eea8dec504e
NEW CANDIDATE SHA: (this commit)
DIRECT PARENT: 5a612d0f52d0efa638360568ce100bdb86bb4366

LKG PRIMITIVES INVENTORIED: 16
RESTORED: 8 — CO family, Evidence Density (kept+visible), Momentum Trace, مشهد تنفيذي, مركز الجاذبية, Home capsules, Home taper, Workspace cf2-co-row
NOT RESTORED: 7 — LKG two-column scene, 88px poster rail, old App Bar, LKG split/copy, next-card CO gallery, fake momentum, fabricated empty density

HOME RENDERER: RESTORED
WORKSPACE RENDERER: RESTORED
CURRENT SHELL: PRESERVED
CURRENT DATA CONTRACTS: PRESERVED
HOME PRODUCT SEMANTICS: PRESERVED
WORKSPACE PRODUCT SEMANTICS: PRESERVED
INCOMPLETE-TRUTH VISUAL IDENTITY: PASS
HOME DESKTOP: PASS
HOME MOBILE: PASS
WORKSPACE DESKTOP: PASS (fixture paint; live local projection still errors — path unchanged)
WORKSPACE MOBILE: PASS (fixture paint; live local projection still errors — path unchanged)
LOGO-HIDDEN COHERENCE: PASS
CARTFLOW PRIMITIVE PRESENCE: RESTORED
UNRELATED RUNTIME CHANGES: 0
OPERATIONAL SMOKE: PASS
SESSION / DB SAFETY: PRESERVED
PRODUCTION VISUAL REGRESSION: CLOSED_LOCALLY
MERCHANT VISUAL SYSTEM V1: REMAINS_PROVISIONAL
SAFE FOR REAL-DEVICE REVIEW: YES
SAFE FOR PRODUCTION DEPLOY: NO
```

**STOP.** No production deploy.
