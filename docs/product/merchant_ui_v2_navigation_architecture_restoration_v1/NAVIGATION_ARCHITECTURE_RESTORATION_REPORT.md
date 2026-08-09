# Merchant UI V2 — Navigation Architecture Restoration V1

**Status:** Implemented on Living Store — awaiting manual visual acceptance  
**Do NOT declare visual PASS. Do NOT freeze navigation.**  
**Deploy SHA:** `34d83c3`  
**Marker:** `data-cf2-appbar="global-upbar-v1"`  

---

## What was rejected

The recent mobile direction merged responsibilities:

- Active section text inside the CartFlow identity cluster
- Drawer treated as the only navigation hierarchy / chrome handoff
- Contextual sidebar forced off for Home + Workspace

That violated the CartFlow law: **Global Upbar ≠ Contextual Sidebar**.

This pass is a **structural restoration** in V2 visual language — not a legacy visual rollback.

---

## Architecture restored

### Global Upbar
Answers: “Where do I go in CartFlow?”

Primary destinations only:

- الرئيسية · مساحة القرار · المنتجات · السلال · التواصل · الإعدادات

Plus CartFlow identity, merchant/account utility, mobile menu.

**Does not** contain نظرة عامة / area subsections.

### Contextual Sidebar (desktop) / Context strip (mobile)
Answers: “Where am I inside this product area?”

| Area | Contextual items (real V2 only) |
|------|----------------------------------|
| الرئيسية | **نظرة عامة** (frozen Home executive board) |
| مساحة القرار | **ما يحتاج قرارك** (Workspace attention surface) |

**Not invented:** V1 `#home-month` / “الملخص العام” is **not** a live V2 composition, so **الملخص** was not added as a fake sidebar destination. When a real V2 summary subview exists, it can join Home context under the same law.

Stub areas (Products / Carts / Communication / Settings) keep ctx **off** until those compositions exist.

### Desktop geometry

```
┌──────────────────────────────────────────────┐
│ GLOBAL UPBAR                                 │
├─────────────┬────────────────────────────────┤
│ CONTEXTUAL  │       PAGE CONTENT             │
│ SIDEBAR     │                                │
└─────────────┴────────────────────────────────┘
```

- `--cf2-ctx-w: 168px`
- Stage inner width budget `min(1360px, 100%)` preserved for frozen Home composition

### Mobile geometry

- **Upbar:** Menu + CartFlow + Account (no section label in brand cluster)
- **Context strip:** below Upbar — area title + contextual chips (separate surface)
- **Drawer:** GLOBAL sections + account only — labeled “أقسام المنصة” / “الحساب”

---

## Clean replacement (not override)

Removed rather than layered:

- `.cf2-appbar__core` / `__core-rule` / `__section` identity+location merge
- `mobile-geometry-v2` centered/packed cluster rules
- Full-width drawer chrome replacing the Upbar
- `setContext` early-return that forced Home/Workspace `data-cf2-ctx="off"`

Frame CSS rewritten as one authoritative Upbar+Sidebar+mobile-strip model.

---

## Living Store evidence

| File | Surface |
|------|---------|
| `01_desktop_home_upbar_sidebar.png` | Desktop Home layers |
| `02_desktop_workspace_upbar_sidebar.png` | Desktop Workspace layers |
| `03_desktop_home_full.png` | Desktop Home full |
| `04_desktop_workspace_full.png` | Desktop Workspace full |
| `05_mobile_home_global_navigation.png` | Mobile global drawer |
| `06_mobile_home_context_navigation.png` | Mobile Home context strip |
| `07_mobile_workspace_global_navigation.png` | Mobile Workspace drawer |
| `08_mobile_workspace_context_navigation.png` | Mobile Workspace context strip |
| `09_mobile_home_page_scroll.png` | Home scroll |
| `10_mobile_workspace_page_scroll.png` | Workspace scroll |

Supporting probe: `production_probe.json`

---

## Mandatory review answers

| # | Question | Answer |
|---|----------|--------|
| 1 | Global Upbar independent from Contextual Sidebar? | **Yes** — separate DOM (`.cf2-appbar` vs `#cf2-ctx` / `#cf2-ctx-mobile`) |
| 2 | Upbar only primary destinations? | **Yes** — six platform sections + identity/account/menu |
| 3 | Sidebar only current-area navigation? | **Yes** — Home overview / Workspace attention only |
| 4 | Switching الرئيسية → مساحة القرار replaces context? | **Yes** — probe: overview → ما يحتاج قرارك |
| 5 | Home frozen composition untouched? | **Yes** — `home-stage-closure-v1` present; home JS/CSS not edited |
| 6 | Workspace composition untouched? | **Yes** — `workspace-final-v1`; workspace JS/CSS not edited |
| 7 | Mobile preserves global/contextual separation? | **Yes** — drawer = global; strip = context |
| 8 | Vertical page scrolling preserved? | **Yes** — document scroll contract retained; drawer locks only while open |
| 9 | Obsolete merged-nav rules removed? | **Yes** — clean frame rewrite; geometry/chrome merge removed |
| 10 | Legacy CSS dependency? | **No** — V2 namespace only; no `merchant_frame_v1` / PE cascade |

---

## Out of scope (honored)

- No Products / Carts / Communication / Settings page composition
- No navigation freeze
- No automated visual PASS

---

## STOP

Implementation + deploy (`34d83c3`) + Living Store screenshots + this report.  
**Await manual visual acceptance.**
