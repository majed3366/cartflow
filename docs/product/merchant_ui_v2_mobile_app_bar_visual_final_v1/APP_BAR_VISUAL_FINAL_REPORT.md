# Merchant UI V2 — Mobile App Bar Visual Composition Final V1

**Status:** Implemented on Living Store — awaiting visual approval  
**Deploy SHA:** `d825b36`  
**Marker:** `data-cf2-appbar="mobile-visual-final-v1"`  
**Prior:** Reality correction `4e03720` restored visibility; this pass closes **composition**.

---

## Verdict

The closed mobile App Bar now reads as **one CartFlow chrome object** with three zones:

`[ account edge ] · [ CartFlow mark+word | section ] · [ menu edge ]`

Not four equal siblings across the row.

---

## Report answers

### 1. What was wrong AFTER the `4e03720` reality fix?

All four required elements were visible and correctly ordered, but they were laid out as **equal-weight flex siblings** (`account · brand · section · menu`) with matching visual weight (bordered utility boxes + bold white section title). The bar was anatomically complete and compositionally unfinished.

### 2. Why was the previous bar technically correct but visually unacceptable?

DOM presence, bbox visibility, and no-clip gates could PASS while the merchant still perceived **four unrelated controls**. There was no identity↔location relationship, no hierarchy, and competing chrome (bordered account/menu squares vs brand vs section).

### 3. What is the final App Bar hierarchy?

1. **Identity + location core** (primary) — CartFlow mark + wordmark + active section  
2. **Menu + account edges** (supporting utilities) — quiet, borderless, balanced  

### 4. How are CartFlow identity and active section related visually?

They share a single `.cf2-appbar__core` cluster, centered in the bar’s middle column, joined by a restrained teal vertical rule. Section type is quieter than the wordmark (smaller size, weight 600, softer white). They read as **product + place**, not two labels.

### 5. What obsolete/duplicate CSS or markup was removed?

- Replaced the Reality Correction flex/`order` patch block with **one authoritative mobile composition** (CSS grid, three columns).  
- Wrapped brand + section in `.cf2-appbar__core` (desktop uses `display: contents` so desktop flex row is unchanged).  
- Removed bordered “card” treatment on mobile account/menu (were competing as equal tiles).  
- Retired marker `mobile-reality-v1` → `mobile-visual-final-v1`.

### 6. Does the bar remain one row at 390px and 430px?

Yes. Probe gates `composition390` / `composition430` **PASS** (`noWrap`, `noOverflow`).

### 7. Does Home/Workspace use the exact same architecture?

Yes. Same markup and CSS; only `#cf2-appbar-section` text changes (`الرئيسية` / `مساحة القرار`).

### 8. Does drawer open/close preserve the final bar?

Yes. `afterDrawerClose` **PASS**; body lock released after close.

### 9. Is vertical page scrolling unaffected?

Yes. Injected-height scroll probe confirms document scroll works; drawer closed does not leave `overflow: hidden` residue. Home/Workspace page modules untouched (`home-stage-closure-v1`, `workspace-final-v1`).

### 10. Were Home and Workspace page compositions untouched?

Yes. No edits to `merchant_ui_v2_home.*` or `merchant_ui_v2_workspace.*` page composition. Only frame template + `merchant_ui_v2_frame.css` App Bar rules.

---

## Implementation summary

| Zone | Treatment |
|------|-----------|
| Account edge | 40×40 ghost control, no border tile |
| Core | `justify-self: center`; mark+word + teal rule + quieter section |
| Menu edge | Matching ghost control, balanced with account |
| Desktop | `.cf2-appbar__core { display: contents }` — prior desktop layout preserved |

---

## Gates (Living Store probe)

| Gate | Result |
|------|--------|
| compositionHome | PASS |
| compositionWorkspace | PASS |
| composition390 | PASS |
| composition430 | PASS |
| wordmarkNotClipped | PASS |
| sectionHome / sectionWorkspace | PASS |
| afterDrawerClose | PASS |
| afterHomeWorkspaceSwitch / backHomePreserved | PASS |
| drawerBodyLockReleased | PASS |
| pageVerticalScroll | PASS |
| desktopIdentityIntact | PASS |
| home / workspace composition untouched | PASS |
| markerFinal | PASS |

Full JSON: [`production_probe.json`](production_probe.json)

---

## Evidence

| File | Role |
|------|------|
| [01_mobile_home_closed.png](01_mobile_home_closed.png) | Home closed — full frame |
| [02_mobile_workspace_closed.png](02_mobile_workspace_closed.png) | Workspace closed — full frame |
| [03_mobile_home_appbar_closeup.png](03_mobile_home_appbar_closeup.png) | Home App Bar close-up |
| [04_mobile_workspace_appbar_closeup.png](04_mobile_workspace_appbar_closeup.png) | Workspace App Bar close-up |
| [05_mobile_drawer_open.png](05_mobile_drawer_open.png) | Drawer open |
| [06_mobile_after_drawer_close.png](06_mobile_after_drawer_close.png) | Bar after drawer close |
| [07_mobile_after_home_workspace_switch.png](07_mobile_after_home_workspace_switch.png) | After Home → Workspace |
| [08_mobile_390px.png](08_mobile_390px.png) | 390px class |
| [09_mobile_430px.png](09_mobile_430px.png) | 430px class |
| [10_before_after_appbar.png](10_before_after_appbar.png) | Reality-fix vs Visual Final |

---

## STOP

Mobile App Bar Visual Composition Final V1 is implemented and evidenced on Living Store.  

**Await visual approval** before freezing Decision Workspace.  

Do **not** start Products / Carts / Communication / Settings in this step.
