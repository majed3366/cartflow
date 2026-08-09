# 02 — Canonical Global Nav Model

**Source of truth:** `static/merchant_ui_v2_app.js` → `NAV.global`

| id | label |
|----|-------|
| `home` | الرئيسية |
| `workspace` | مساحة القرار |
| `products` | المنتجات |
| `carts` | السلال |
| `comms` | التواصل |
| `settings` | الإعدادات |

## Paint function

`paintGlobalNavigation(activeSection)` writes the same list into:

1. `#cf2-nav` — desktop Upbar (`data-cf2-global-mount="upbar"`)
2. `#cf2-global-panel-list` — mobile Global panel (`data-cf2-global-mount="mobile"`)
3. `#cf2-drawer-global` — utility drawer optional shortcuts (`data-cf2-global-mount="drawer"`)

No hardcoded destination buttons remain in the template for Global destinations (hosts are empty mounts).

## Public API

```js
window.CartFlowUiV2.nav.global
window.CartFlowUiV2.paintGlobalNavigation
window.CartFlowUiV2.openGlobalNav / closeGlobalNav
```
