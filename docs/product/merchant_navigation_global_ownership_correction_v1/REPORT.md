# Merchant Navigation — Global Ownership Correction V1

**Status:** Implemented + deployed evidence pending / **STOP for visual approval**  
**Marker:** `data-cf2-appbar="global-ownership-v1"`  
**Forensic basis:** `docs/product/merchant_navigation_forensic_audit_v1/`

---

## Answers

### 1. What exact root-cause rule was removed/replaced?

The architectural effect of:

```css
@media (max-width: 1023px) {
  .cf2-nav { display: none !important; }
}
```

which left Global destinations **drawer-only** on mobile.

**Replaced by:** hide desktop *list presentation* of `#cf2-nav` on mobile, and present the **same** `NAV.global` through `#cf2-global-btn` + `#cf2-global-panel`. Utility drawer is no longer the exclusive Global owner.

### 2. Where is the canonical GlobalNavigation model?

`static/merchant_ui_v2_app.js` → `NAV.global` (painted by `paintGlobalNavigation`).

### 3. What consumes it on desktop?

`#cf2-nav` (`data-cf2-global-mount="upbar"`).

### 4. What consumes it on mobile?

`#cf2-global-panel-list` (`data-cf2-global-mount="mobile"`), opened by `#cf2-global-btn`.

### 5. What role remains for the hamburger/global drawer?

Account / utility surface (`#cf2-drawer`): profile/package, logout, and optional Global shortcuts painted into `#cf2-drawer-global` from the **same** model.

### 6. How is Contextual Navigation kept separate?

Unchanged `#cf2-ctx` + `#cf2-ctx-btn` / `NAV.contextual`. Distinct body class `is-ctx-open`. Mutual exclusion with Global panel and utility drawer.

### 7. Was any Home/Workspace composition changed?

**No.** Home and Workspace CSS/JS were not modified.

---

## Hard gates

| Gate | Status |
|------|--------|
| No Home visual changes | Met (files untouched) |
| No Workspace visual changes | Met |
| No Products/Carts/Comms/Settings implementation | Met |
| No nav V4/V5/V6 experiment | Met — ownership correction only |
| Do not declare PASS / freeze | Met — visual review required |

See `05_ACCEPTANCE_RESULTS.md` and `06_VISUAL_REVIEW.md` after Living Store capture.
