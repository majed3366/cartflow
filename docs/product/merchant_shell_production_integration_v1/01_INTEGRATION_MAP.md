# 01 — Integration Map

| Approved layer | Production host | Source |
|----------------|-----------------|--------|
| UtilityRow | `.cf2-utility` inside `.cf2-chrome` | Template + CSS |
| GlobalUpbar | `.cf2-global` → `#cf2-nav` | `NAV.global` via `paintGlobalNavigation` |
| ContextualSidebar | `#cf2-ctx` + `#cf2-ctx-handle` (mobile) | `NAV.contextual` via `setContext` |
| PageStage | `#cf2-stage` | Existing Home/Workspace roots unchanged |

**Marker:** `data-cf2-appbar="shell-integration-v1"`

**Files changed (shell only):**
- `templates/merchant_app_v2.html`
- `static/merchant_ui_v2_app.js`
- `static/merchant_ui_v2_frame.css`
- `static/merchant_ui_v2_ds.css` (chrome height tokens)
- `tests/test_merchant_ui_v2.py`

**Files not changed:** `merchant_ui_v2_home.js|.css`, `merchant_ui_v2_workspace.js|.css`
