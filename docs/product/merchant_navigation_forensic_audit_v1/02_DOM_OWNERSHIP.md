# 02 — DOM Ownership

**Rule for this audit:** every row is a live node/component in Merchant UI V2 production shell.  
**Template:** `templates/merchant_app_v2.html`  
**CSS:** `static/merchant_ui_v2_frame.css`  
**JS:** `static/merchant_ui_v2_app.js`

---

## A. Global navigation

### A1. Desktop Upbar platform list

| Field | Value |
|-------|-------|
| File | `templates/merchant_app_v2.html` L43–50 |
| Element | `<nav class="cf2-nav">` → `<button class="cf2-nav__item" data-cf2-nav="…">` |
| id / class / data | `.cf2-nav`, `.cf2-nav__item`, `data-cf2-nav="{home\|workspace\|products\|carts\|comms\|settings}"` |
| Desktop | Visible flex row in App Bar (`display: flex` default L80–88 frame.css) |
| Mobile | **Hidden** — `@media (max-width: 1023px) { .cf2-nav { display: none !important } }` L485–490 |
| Who creates | Static HTML (not generated from `NAV.global` at runtime) |
| Who hides/shows | CSS media query only (no JS display toggle on `.cf2-nav`) |
| Who changes contents | Static; JS only toggles `.is-active` / `aria-current` via `setActiveNav()` |

### A2. Global drawer platform list

| Field | Value |
|-------|-------|
| File | `templates/merchant_app_v2.html` L105–127 |
| Element | `<aside id="cf2-drawer" class="cf2-drawer">` → `.cf2-drawer__item[data-cf2-nav]` |
| id / class / data | `#cf2-drawer`, `.cf2-drawer`, `.cf2-drawer__item`, `data-cf2-nav` |
| Desktop | Markup present; drawer can open from identity button; mobile-only chrome not required for open |
| Mobile | **Sole visible Global destinations** when opened via hamburger / account |
| Who creates | Static HTML (second copy of the six labels) |
| Who hides/shows | CSS `.cf2-drawer` default `display: none`; `.is-open` → `display: flex`. JS `openDrawer` / `closeDrawer` add/remove `.is-open` + `body.is-drawer-open` |
| Who changes contents | Static; JS `setActiveNav` marks active item |

### A3. Canonical model (not a DOM node)

| Field | Value |
|-------|-------|
| File | `static/merchant_ui_v2_app.js` L12–35 `NAV.global` |
| Role | Source of truth for labels/ids used by `sectionLabel`, `setContext`, exposed as `window.CartFlowUiV2.nav` |
| Renders into DOM? | **No** — does not build `.cf2-nav` or `.cf2-drawer` lists |

---

## B. Contextual navigation

### B1. Contextual host

| Field | Value |
|-------|-------|
| File | Template empty host L71; contents from JS |
| Element | `<aside class="cf2-ctx" id="cf2-ctx" hidden>` |
| id / class / data | `#cf2-ctx`, `.cf2-ctx`; shell attr `.cf2-shell[data-cf2-ctx="on\|off"]` |
| Desktop | Grid column (`--cf2-ctx-w`); visible when `data-cf2-ctx="on"` and not `[hidden]` |
| Mobile | `position: fixed` overlay; closed = `display: none`; open = `.is-open` / `body.is-ctx-open` |
| Who creates | Template creates empty aside; `setContext()` fills `innerHTML` |
| Who hides/shows | `setContext()` sets `hidden` / `data-cf2-ctx`; mobile CSS + `openCtxDrawer` / `closeCtxDrawer` |
| Who changes contents | `paintCtxMarkup(conf, activeId)` → `ctx.innerHTML = …` |

### B2. Contextual items (runtime)

| Field | Value |
|-------|-------|
| Created by | `paintCtxMarkup` L75–98 |
| Elements | `.cf2-ctx__toolbar` + `#cf2-ctx-close`; `.cf2-ctx__area`; `.cf2-ctx__item[data-cf2-ctx-item]` |
| Model | `NAV.contextual[section]` |

### B3. Mobile contextual trigger

| Field | Value |
|-------|-------|
| File | Template L25–38 |
| Element | `<button id="cf2-ctx-btn" class="cf2-ctx-btn cf2-appbar__mobile-only" hidden>` |
| Desktop | `display: none !important` via `@media (min-width: 1024px)` L457–464 |
| Mobile | Shown when section has contextual items (`setContext` clears `hidden`) |
| Who toggles open | `toggleCtxDrawer` on click |

---

## C. App Bar / Upbar

| Field | Value |
|-------|-------|
| File | Template L21–67 |
| Element | `<header class="cf2-appbar" role="banner" data-cf2-appbar="nav-reset-v1">` |
| Classes | `.cf2-appbar`, sticky L42–55 frame.css |
| Desktop contents | Brand + `.cf2-nav` + date + identity |
| Mobile contents | Menu + ctx-btn + Brand + account icon (**no** platform section list) |
| Who creates | Template |
| Who changes contents | No runtime rebuild of App Bar structure; only aria on menu/ctx buttons |

---

## D. Global Drawer

| Field | Value |
|-------|-------|
| Markup | Template L106–127 + backdrop L106 |
| Elements | `.cf2-drawer-backdrop`, `#cf2-drawer.cf2-drawer`, `.cf2-drawer__head`, `.cf2-drawer__close`, sections |
| Open state | `.is-open` on drawer + backdrop; `body.is-drawer-open`; `body.style.overflow = "hidden"` |
| Owners | `openDrawer` / `closeDrawer` / `toggleDrawer` in `merchant_ui_v2_app.js` |
| Triggers | `.cf2-menu-btn` → toggle; `#cf2-mobile-account`, `#cf2-account-btn` → open; close button + backdrop → close; `loadSection` always closes |

---

## E. Contextual Sidebar

| Field | Value |
|-------|-------|
| Same node as B1 | `#cf2-ctx` |
| Desktop presentation | In-flow grid column |
| Mobile presentation | Fixed overlay drawer (CSS restyle — **no DOM reparenting**) |
| Proof of no reparent | No `appendChild` / move of `#cf2-ctx` in `merchant_ui_v2_app.js` |

---

## F. Contextual mobile sheet / drawer

| Field | Value |
|-------|-------|
| Current | **Not a separate product.** Overlay = same `#cf2-ctx` + `#cf2-ctx-backdrop` |
| Backdrop | Template L130; shown by `openCtxDrawer` |
| Historical separate sheet | `#cf2-ctx-sheet` / page-chrome — **removed** from live template (see Audit 5) |

---

## G. Legacy navigation containers still present

### G1. Merchant UI V1 (rollback path `?cf_ui=v1`)

| Field | Value |
|-------|-------|
| File | `templates/merchant_app.html` |
| Global | `.cf-rail__primary .ma-gtb-section[data-ma-section]` inside `#ma-context-sidebar` |
| Contextual | `.ma-ctx-panel[data-ma-ctx]` inside **same** rail |
| Topbar | `.cf-topbar.ma-global-topbar` — brand/menu/title labels, **not** platform pills |
| Mobile | Entire rail becomes hamburger drawer (`#ma-sidebar-toggle` + `merchant_frame_v1.css` ≤1023) |
| Status | ACTIVE on V1 path; NOT mounted when V2 template is served |

### G2. V2 experiment remnants in live tree

| Selector | Status in live V2 template |
|----------|----------------------------|
| `#cf2-page-chrome` | ABSENT |
| `#cf2-section-chrome` | ABSENT |
| `#cf2-ctx-sheet` | ABSENT |
| `.cf2-appbar__section` | ABSENT |
| `تنقل القسم` / content `في هذا القسم` trigger | ABSENT from V2 template |

---

## Ownership summary matrix

| Concern | Creates | Shows/hides | Mutates contents |
|---------|---------|-------------|------------------|
| Global Upbar links | HTML | CSS ≤1023 hide | JS active class only |
| Global Drawer links | HTML | JS open/close + CSS | JS active class only |
| Contextual sidebar | JS `innerHTML` | JS + CSS | JS `setContext` |
| App Bar shell | HTML | CSS responsive chrome swap | JS aria only |
| Body scroll lock | — | JS drawer/ctx open | `body.style.overflow` |
