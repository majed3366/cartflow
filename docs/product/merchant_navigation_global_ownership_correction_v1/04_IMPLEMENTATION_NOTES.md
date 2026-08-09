# 04 — Implementation Notes

## Files changed

| File | Change |
|------|--------|
| `static/merchant_ui_v2_app.js` | `paintGlobalNavigation`; Global panel open/close; mounts paint from `NAV.global` |
| `templates/merchant_app_v2.html` | Empty Global mounts; `#cf2-global-btn` + `#cf2-global-panel`; marker `global-ownership-v1`; cache `globown1` |
| `static/merchant_ui_v2_frame.css` | Global panel styles; mobile Global control; comment clarifying `.cf2-nav` hide is presentation swap |
| `tests/test_merchant_ui_v2.py` | Marker + Global ownership contracts |

## Intentionally unchanged

- `merchant_ui_v2_home.js|.css` — Home composition
- `merchant_ui_v2_workspace.js|.css` — Workspace composition
- `#cf2-ctx` Contextual architecture (desktop column / mobile overlay)
- Product page stubs content

## Marker

`data-cf2-appbar="global-ownership-v1"`
