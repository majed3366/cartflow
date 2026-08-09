# 02 — Navigation Ownership Map

## GlobalNavigation

Canonical: `NAV.global` in `merchant_ui_v2_app.js`

| id | label |
|----|-------|
| home | الرئيسية |
| workspace | مساحة القرار |
| products | المنتجات |
| carts | السلال |
| comms | التواصل |
| settings | الإعدادات |

**Single mount:** `#cf2-nav` (visible desktop + mobile). Horizontal scroll confined to this region.

## ContextualNavigation

Canonical: `NAV.contextual`

| Section | Items |
|---------|-------|
| home | نظرة عامة · الملخص |
| workspace | ما يحتاج قرارك |
| others | null (handle/sidebar off) |

Desktop: in-flow `#cf2-ctx`. Mobile: same node off-canvas; closed = `#cf2-ctx-handle` on PageStage edge.

## Account / Utility

`#cf2-drawer` — الحساب / الملف والباقة / تسجيل الخروج only. Does **not** own platform destinations.
