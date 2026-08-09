# 04 — JavaScript Navigation Map

**Sole shell owner:** `static/merchant_ui_v2_app.js`  
Home/Workspace scripts do not control shell open/close or Global/Contextual routing.

---

## Canonical model

```
NAV.global[]          → labels/ids for platform sections
NAV.contextual{}      → per-section sidebar items (or null)
        ↓
setActiveNav(section) → marks ALL [data-cf2-nav] (upbar + drawer)
setContext(section)   → paints #cf2-ctx OR clears it
showPage(section)     → toggles .cf2-page[data-cf2-page]
        ↓
PRESENTATION BINDINGS (not owned by model):
  Desktop Upbar  → .cf2-nav          (HTML duplicate of NAV.global)
  Global Drawer  → #cf2-drawer       (HTML duplicate of NAV.global)
  Contextual     → #cf2-ctx          (JS-built from NAV.contextual)
  App Bar chrome → .cf2-menu-btn / #cf2-ctx-btn / #cf2-mobile-account
```

**Critical asymmetry:** Contextual is painted from `NAV.contextual`. Global lists are **not** painted from `NAV.global` — they are static HTML copies consumed only for click binding + active state.

---

## Dependency map (rendering + state)

```
GLOBAL NAV MODEL (NAV.global)
        │
        ├── (labels) sectionLabel() / CartFlowUiV2.nav
        │
        ├── [NOT rendered] ──✗── does not build .cf2-nav or #cf2-drawer
        │
        └── setActiveNav() ──→ .cf2-nav__item + .cf2-drawer__item  (active only)
                                      │
STATIC HTML .cf2-nav  ────────────────┤── bind() click → go(id) → hash → loadSection
STATIC HTML #cf2-drawer items ────────┘

CONTEXTUAL NAV MODEL (NAV.contextual)
        │
        └── setContext() → paintCtxMarkup() → #cf2-ctx.innerHTML
                │
                ├── desktop: in-flow sidebar (CSS)
                └── mobile: openCtxDrawer() / closeCtxDrawer() + #cf2-ctx-backdrop

UPBAR CHROME
        ├── .cf2-menu-btn        → toggleDrawer()
        ├── #cf2-ctx-btn         → toggleCtxDrawer()
        ├── #cf2-mobile-account  → openDrawer()
        ├── #cf2-account-btn     → openDrawer()
        └── .cf2-brand           → go("home")
```

---

## Handler inventory

| Function | Lines | Controls | Notes |
|----------|-------|----------|-------|
| `currentHash` | 47–52 | hash → section id | aliases `communication` → `comms` |
| `sectionLabel` | 54–59 | label from `NAV.global` | |
| `contextualFor` | 61–65 | lookup `NAV.contextual` | |
| `setActiveNav` | 67–73 | active Global section | all `[data-cf2-nav]` |
| `paintCtxMarkup` | 75–98 | Contextual HTML | includes mobile close toolbar |
| `setContext` | 100–132 | Contextual show/paint + `#cf2-ctx-btn` visibility | always `closeCtxDrawer()` first |
| `bindCtxClose` | 134–139 | `#cf2-ctx-close` → close | rebound after each paint |
| `showPage` | 141–147 | content page visibility | |
| `setMenuExpanded` | 149–154 | hamburger aria | |
| `closeDrawer` | 156–166 | Global drawer close + scroll unlock | |
| `openDrawer` | 168–177 | Global drawer open; closes ctx first; scroll lock | |
| `toggleDrawer` | 179–182 | hamburger toggle | |
| `closeCtxDrawer` | 184–198 | Contextual overlay close | |
| `openCtxDrawer` | 200–214 | Contextual overlay open; closes Global first | no-op if no ctx items |
| `toggleCtxDrawer` | 216–219 | ctx button toggle | |
| `loadSection` | 221–241 | full section transition | closes both overlays; loads Home/Workspace |
| `go` | 243–250 | hash write or direct load | |
| `bind` | 252–284 | all click + hashchange wiring | |
| DOMContentLoaded | 286–289 | `bind()` + `loadSection(currentHash())` | |

---

## Event bindings (`bind`)

| Trigger | Handler |
|---------|---------|
| click `[data-cf2-nav]` | `go(data-cf2-nav)` |
| click `.cf2-menu-btn` | `toggleDrawer` |
| click `#cf2-mobile-account` | `openDrawer` |
| click `#cf2-account-btn` | `openDrawer` |
| click `.cf2-drawer__close` | `closeDrawer` |
| click `.cf2-drawer-backdrop` | `closeDrawer` |
| click `#cf2-ctx-btn` | `toggleCtxDrawer` |
| click `#cf2-ctx-backdrop` | `closeCtxDrawer` |
| click `.cf2-brand` | `preventDefault` + `go("home")` |
| `hashchange` | `loadSection(currentHash())` |

---

## Body scroll lock

| State class | Set by | Cleared by | CSS |
|-------------|--------|------------|-----|
| `body.is-drawer-open` | `openDrawer` | `closeDrawer` | `overflow: hidden` (frame.css L28–30) + inline `overflow` |
| `body.is-ctx-open` | `openCtxDrawer` | `closeCtxDrawer` | same |

Mutual exclusion: opening Global closes Contextual and vice versa.

---

## DOM relocation / reparenting

**None.** Grep of shell JS shows no `appendChild` moves of nav nodes. Mobile “drawers” are CSS presentation of existing nodes (`#cf2-drawer`, `#cf2-ctx`).

---

## Public API

```js
window.CartFlowUiV2 = {
  go, nav: NAV, sections: SECTIONS, ctx: NAV.contextual,
  openCtxDrawer, closeCtxDrawer
}
```

---

## Answers to Audit 2 (Global source of truth) — JS view

1. **One canonical model?** Semantically yes (`NAV`), but Global **markup** is duplicated outside it.
2. **Separate desktop/mobile copies?** Yes — `.cf2-nav` and `#cf2-drawer` are two HTML lists.
3. **Same list rendered into multiple containers?** Conceptually duplicated; not rendered from one builder.
4. **Moved by JS?** No.
5. **Mobile deliberately drawer-only?** Yes — enforced by CSS; JS assumes hamburger → drawer as Global path.
6. **What removes platform links from mobile Upbar?** CSS `display: none !important` on `.cf2-nav` (not JS).
