# 03 — Removed Superseded Behavior

Verified absent from active production runtime (`templates/merchant_app_v2.html`, `static/merchant_ui_v2_app.js`, `static/merchant_ui_v2_frame.css`):

| Candidate | Status |
|-----------|--------|
| `#cf2-global-btn` / grid Global control | Removed |
| `#cf2-global-panel` / Global modal | Removed |
| `is-global-nav-open` / `openGlobalNav` | Removed |
| `#cf2-drawer-global` platform list in account drawer | Removed |
| `#cf2-ctx-btn` in Utility/App Bar | Removed (replaced by PageStage `#cf2-ctx-handle`) |
| `.cf2-nav { display: none }` under ≤1023 | Removed (GlobalUpbar stays visible) |
| `data-cf2-appbar="global-ownership-v1"` | Superseded by `shell-integration-v1` |
| page-chrome / section pills / تنقل القسم | Still absent |

Docs packs for prior experiments remain on disk for history; they are not loaded by the merchant template.
