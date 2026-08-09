# 03 — Responsive Breakpoint Map

**Primary file:** `static/merchant_ui_v2_frame.css`  
**Breakpoints in force:** `min-width: 1024px` and `max-width: 1023px` only for shell nav.  
**No separate tablet band** — tablet ≤1023 inherits the mobile nav contract.

---

## Token baselines (all widths)

| Selector | Property | Value | File |
|----------|----------|-------|------|
| `:root` / ds | `--cf2-appbar-h` | `52px` | `merchant_ui_v2_ds.css` |
| `:root` / ds | `--cf2-ctx-w` | `168px` | `merchant_ui_v2_ds.css` |

---

## Default (desktop-first) rules affecting nav

| Selector | Property | Value | Effect |
|----------|----------|-------|--------|
| `.cf2-nav` | `display` | `flex` | Global platform links visible in App Bar |
| `.cf2-menu-btn` | `display` | `none` | Hamburger off |
| `.cf2-appbar__account` | `display` | `none` | Mobile account icon off |
| `.cf2-ctx-btn` | `display` | `none` | Contextual trigger off |
| `.cf2-ctx-backdrop` | `display` | `none` | Contextual dimmer off |
| `.cf2-ctx__toolbar` | `display` | `none` | Contextual close toolbar off |
| `.cf2-shell` | `grid-template-columns` | `var(--cf2-ctx-w) minmax(0,1fr)` | Sidebar + stage |
| `.cf2-shell[data-cf2-ctx="off"]` | `grid-template-columns` | `minmax(0,1fr)` | Stage only |
| `.cf2-drawer` | `display` | `none` (until `.is-open`) | Drawer closed |
| `body.is-drawer-open`, `body.is-ctx-open` | `overflow` | `hidden` | Scroll lock while overlay open |

---

## `@media (min-width: 1024px)` — L457–465

```css
@media (min-width: 1024px) {
  body[data-cf-ui="v2"] .cf2-appbar__mobile-only,
  body[data-cf-ui="v2"] .cf2-menu-btn,
  body[data-cf-ui="v2"] .cf2-ctx-btn,
  body[data-cf-ui="v2"] .cf2-ctx-backdrop,
  body[data-cf-ui="v2"] .cf2-ctx__toolbar {
    display: none !important;
  }
}
```

| Selector | Desktop value | Mobile value (from other query) | Effect |
|----------|---------------|----------------------------------|--------|
| `.cf2-appbar__mobile-only` | `none !important` | visible when applicable | Forces mobile-only chrome off on desktop |
| `.cf2-menu-btn` | `none !important` | `inline-flex` | No hamburger on desktop |
| `.cf2-ctx-btn` | `none !important` | `inline-flex` (if not `[hidden]`) | No ctx icon on desktop — sidebar in-flow |
| `.cf2-ctx-backdrop` | `none !important` | shown when `.is-open` | No overlay dimmer on desktop |
| `.cf2-ctx__toolbar` | `none !important` | `flex` | No mobile close chrome on desktop |

---

## `@media (max-width: 1023px)` — L467–628

### 1) App Bar chrome swap (THE Global disappearance rule)

```css
@media (max-width: 1023px) {
  body[data-cf-ui="v2"] .cf2-nav,
  body[data-cf-ui="v2"] .cf2-appbar__actions,
  body[data-cf-ui="v2"] .cf2-appbar__date,
  body[data-cf-ui="v2"] .cf2-appbar__desktop-only {
    display: none !important;
  }
}
```

| Selector | Desktop | Mobile | Effect |
|----------|---------|--------|--------|
| `.cf2-nav` | `flex` | `none !important` | **Removes Global platform navigation from visible App Bar** |
| `.cf2-appbar__actions` | `flex` | `none !important` | Hides desktop identity cluster |
| `.cf2-appbar__date` | visible | `none !important` | Hides date |
| `.cf2-appbar__desktop-only` | visible | `none !important` | Hides any desktop-only App Bar controls |

**Author comment in CSS (L472–476):** explicitly states mobile closed App Bar = Menu · Contextual control · CartFlow · Account; **“No section name pills.”**

This is the concrete code that causes platform links (الرئيسية … الإعدادات) to disappear from the visible mobile Upbar.

### 2) Reveal hamburger / ctx / account

| Selector | Desktop | Mobile | Effect |
|----------|---------|--------|--------|
| `.cf2-menu-btn` | `none` | `inline-flex` 40×40 | Hamburger becomes Global entry |
| `.cf2-ctx-btn` | `none` | `inline-flex` 40×40 | Contextual entry in App Bar |
| `.cf2-ctx-btn[hidden]` | — | `none !important` | Still hidden when section has no ctx |
| `.cf2-appbar__account` | `none` | `inline-flex` + `margin-inline-start: auto` | Account opens Global drawer |

### 3) Collapse shell to single column

| Selector | Desktop | Mobile | Effect |
|----------|---------|--------|--------|
| `.cf2-shell` | two-column grid | `grid-template-columns: minmax(0,1fr)` | Sidebar leaves content flow |

### 4) Restyle `#cf2-ctx` as overlay

| Selector | Desktop | Mobile | Effect |
|----------|---------|--------|--------|
| `.cf2-ctx` | in-flow column | `display: none; position: fixed; … width: min(280px,82vw); z-index: 60` | Contextual not visible until open |
| `.cf2-ctx[hidden]` | none | `none !important` | Hard hide when no ctx |
| `body.is-ctx-open .cf2-ctx:not([hidden])` | n/a | `display: block` | Open contextual overlay |
| `.cf2-ctx.is-open` | n/a | `display: block` | Same |
| `.cf2-ctx__toolbar` | none | `flex` | Close control appears |
| `.cf2-ctx-backdrop` | none | fixed dimmer; `.is-open` → `display: block` | Backdrop for contextual |

### 5) Global drawer positioning tweak

| Selector | Desktop | Mobile | Effect |
|----------|---------|--------|--------|
| `.cf2-drawer` | top sheet from end | `inset-inline-start: 0` (RTL start), radius adjust | Drawer presents as mobile Global nav panel |

### 6) Stage padding

| Selector | Desktop | Mobile | Effect |
|----------|---------|--------|--------|
| `.cf2-stage` | `12px 24px 28px` | `14px 16px 40px` | Content padding only |

---

## Related V2 CSS with 1024 / 1023 (NOT shell ownership)

These affect page layout, not Global/Contextual ownership:

| File | Approx | Role |
|------|--------|------|
| `merchant_ui_v2_home.css` | ~287 / ~320 | Home board responsive |
| `merchant_ui_v2_workspace.css` | ~252 / ~313 | Workspace responsive |
| `merchant_ui_v2_language.css` | ~895 `max-width: 1023px` | Language surfaces |

---

## Inherited V1 parallel (proof of contract ancestry)

`static/merchant_frame_v1.css`:

```css
@media (max-width: 1023px) {
  /* hide topbar section chrome */
  .cf-topbar__sections, .ma-gtb-sections, … { display: none !important; }
  /* rail becomes hamburger drawer */
  .cf-rail { transform: translateX(100%); … }
  #ma-sidebar-toggle:checked ~ .cf-rail { transform: translateX(0); }
}
```

V1 already encoded: **≤1023px → navigation via hamburger drawer, not persistent top platform list.**  
V2 reused the same breakpoint and applied it to `.cf2-nav`.

---

## Breakpoint forensics verdict

| Question | Answer |
|----------|--------|
| What hides Global from mobile Upbar? | `.cf2-nav { display: none !important }` inside `@media (max-width: 1023px)` |
| Is tablet different from phone? | No — both ≤1023 |
| Does JS hide `.cf2-nav`? | No |
| Is drawer-only Global deliberate? | Yes — CSS comments + original V2 commit (see `06_GIT_HISTORY_FINDINGS.md`) |
