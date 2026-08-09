# Merchant Navigation — Global Ownership Correction V1

**Status:** Living Store deployed · automated gates true · **STOP for visual approval**  
**Marker:** `data-cf2-appbar="global-ownership-v1"`  
**Deploy SHA:** `ea236e5a079196d9a1b59d788dd23f2264c6f91b`  
**Forensic basis:** `docs/product/merchant_navigation_forensic_audit_v1/`

**PASS:** not declared  
**Freeze:** not declared

---

## Answers

### 1. What exact root-cause rule was removed/replaced?

The architectural effect of hiding `.cf2-nav` under `@media (max-width: 1023px)` which left Global destinations **drawer-only**.

**Replaced by:** desktop list presentation of `#cf2-nav` still hides on mobile (to avoid six-link overflow), while Global ownership is presented via `#cf2-global-btn` + `#cf2-global-panel` painted from the same `NAV.global`. Utility drawer is no longer the exclusive Global owner.

### 2. Where is the canonical GlobalNavigation model?

`static/merchant_ui_v2_app.js` → `NAV.global`, painted by `paintGlobalNavigation()`.

### 3. What consumes it on desktop?

`#cf2-nav` (`data-cf2-global-mount="upbar"`).

### 4. What consumes it on mobile?

`#cf2-global-panel-list` (`data-cf2-global-mount="mobile"`), opened by `#cf2-global-btn`.

### 5. What role remains for the hamburger/global drawer?

Account / utility (`#cf2-drawer`): الملف والباقة، تسجيل الخروج، plus optional Global shortcuts in `#cf2-drawer-global` from the **same** model.

### 6. How is Contextual Navigation kept separate?

Unchanged `#cf2-ctx` + `#cf2-ctx-btn` / `NAV.contextual`. Body class `is-ctx-open`. Mutual exclusion with Global panel and utility drawer.

### 7. Was any Home/Workspace composition changed?

**No.**

---

## Automated gates

All acceptance gates in `05_ACCEPTANCE_RESULTS.md` → **true** (see `production_probe.json`).

---

## Hard gates

| Gate | Status |
|------|--------|
| No Home visual changes | Met |
| No Workspace visual changes | Met |
| No Products/Carts/Comms/Settings implementation | Met |
| No nav V4/V5/V6 experiment | Met |
| Do not declare PASS / freeze | Met |
