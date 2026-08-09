# 05 — Legacy / V2 Collision Report

Classification legend:

| Tag | Meaning |
|-----|---------|
| ACTIVE | Live in current V2 production path |
| DEAD | Removed from live V2 template/CSS/JS; may remain in docs/scripts/tests |
| HIDDEN | Present in DOM but not visible at a breakpoint |
| OVERRIDDEN | Present but forced off by stronger CSS/JS |
| DUPLICATED | Same semantic list in multiple hosts |
| LEGACY | V1-only path (`merchant_app.html` / frame_v1) |

---

## Concept search results

| Concept / selector | Classification | Evidence |
|--------------------|----------------|----------|
| `appbar` / `.cf2-appbar` | ACTIVE | Template L21; frame.css GLOBAL UPBAR |
| `data-cf2-appbar="nav-reset-v1"` | ACTIVE | Current marker |
| `topbar` / `.cf-topbar` | LEGACY | V1 `merchant_app.html` + `merchant_frame_v1.css` |
| `upbar` (docs/comments) | ACTIVE (alias) | Comments call App Bar “GLOBAL UPBAR”; no `.cf2-upbar` class |
| `global-nav` | DEAD as class name | No `.global-nav`; Global = `.cf2-nav` + drawer |
| `.cf2-nav` | ACTIVE + HIDDEN on mobile | Visible ≥1024; `display:none !important` ≤1023 |
| `mobile-nav` | DEAD as class | Mobile Global = `#cf2-drawer` |
| `drawer` / `#cf2-drawer` | ACTIVE | Global drawer |
| `contextual` / `#cf2-ctx` | ACTIVE | Contextual host |
| `ctx` / `.cf2-ctx-*` | ACTIVE | Toolbar, items, backdrop, btn |
| `sidebar` (V2) | ACTIVE as `#cf2-ctx` | Not classed `.sidebar` in V2 |
| `.sidebar` / `.ma-context-sidebar` / `.cf-rail` | LEGACY | V1 rail merges Global+Contextual |
| `page-chrome` / `#cf2-page-chrome` | DEAD in live code | Mentioned only as “never invent” in comments; removed by nav-reset-v1 |
| `section-chrome` / `#cf2-section-chrome` | DEAD | Same |
| `context-sheet` / `#cf2-ctx-sheet` | DEAD | Prior closure/final iterations; removed |
| `nav-reset` / `nav-reset-v1` | ACTIVE marker | `data-cf2-appbar="nav-reset-v1"` |
| `nav-closure` / `nav-closure-v2` | DEAD marker | Superseded; docs pack retained |
| `nav-ctx` / `nav-ctx-chrome-v3` | DEAD marker | Superseded |
| `mobile-reality` / `mobile-reality-v1` | DEAD marker | Tests still expect it (stale) |
| `mobile-geometry` / `mobile-geometry-v2` | DEAD marker | Docs only |
| `pills` / App Bar section pills | DEAD | Explicitly banned in CSS comment; removed in closure v2 / reset |
| `section trigger` / `تنقل القسم` | DEAD in V2 | Was V3 page-chrome; removed |
| `في هذا القسم` | LEGACY in V1 ctx panels; DEAD as V2 content trigger | V1 `ma-ctx-label`; V2 no content-flow trigger |
| floating context strip | DEAD | Removed in final correction / reset |

---

## Duplicated Global list

| Host | Status |
|------|--------|
| `.cf2-nav` buttons | ACTIVE desktop / HIDDEN mobile |
| `#cf2-drawer` buttons | ACTIVE (primary mobile Global path; also openable on desktop via account) |
| `NAV.global` JS array | ACTIVE model — **not** used to generate either host |

→ **DUPLICATED** presentation of Global destinations (2 HTML lists + 1 JS model).

---

## Historical V2 iteration packs (docs/scripts — not live chrome)

| Pack | Marker | Status |
|------|--------|--------|
| `merchant_ui_v2_navigation_architecture_reset_v1` | `nav-reset-v1` | ACTIVE (current) |
| `merchant_ui_v2_navigation_ctx_chrome_v3` | `nav-ctx-chrome-v3` | SUPERSEDED |
| `merchant_ui_v2_navigation_architecture_closure_v2` | `nav-closure-v2` | SUPERSEDED |
| `merchant_ui_v2_navigation_final_correction_v1` | `nav-final-v1` | SUPERSEDED |
| `merchant_ui_v2_navigation_architecture_restoration_v1` | `global-upbar-v1` | SUPERSEDED |
| `merchant_ui_v2_mobile_app_bar_geometry_v2` | `mobile-geometry-v2` | SUPERSEDED |
| `merchant_ui_v2_mobile_app_bar_visual_final_v1` | `mobile-visual-final-v1` | SUPERSEDED |
| `merchant_ui_v2_app_bar_mobile_reality_correction_v1` | `mobile-reality-v1` | SUPERSEDED |
| `merchant_ui_v2_app_bar_final_closure_v1` | `final-closure-v1` | SUPERSEDED |

Capture scripts under `scripts/_capture_merchant_ui_v2_*navigation*` / `*app_bar*` remain on disk for evidence replay — **not** loaded by the merchant template.

---

## Stale test collision

`tests/test_merchant_ui_v2.py` (per explore) still expects older App Bar marker / section chrome strings vs live `nav-reset-v1`.  
Classification: **OVERRIDDEN/STALE test contract** relative to production shell (tests are not deleting live nodes; they diverge from reality).

---

## V1 vs V2 ownership collision (conceptual)

| Layer | V1 live | V2 live |
|-------|---------|---------|
| Global destinations | Inside rail `.cf-rail__primary` | Upbar `.cf2-nav` **and** drawer |
| Contextual | Inside same rail `.ma-ctx-panel` | Separate `#cf2-ctx` |
| Mobile | One hamburger drawer = Global+Contextual merged | Two overlays: Global drawer + Contextual overlay |
| Top/App bar | Labels/brand/account; not platform pills | Desktop = platform pills; Mobile = chrome only |

V2 correctly **split** Global vs Contextual into separate hosts, but mobile still **hides** the Global Upbar host — recreating the V1 “hamburger is how you reach destinations” feel for Global.

---

## Collision verdict

No competing live V2 third layer remains (page-chrome / ctx-sheet / pills removed).  
The remaining collision is **intentional dual Global presentation** (Upbar vs Drawer) gated by 1023px, plus **legacy V1** on the rollback path. Symptom patches failed because they fought Contextual presentation while leaving this Global dual-host contract intact.
