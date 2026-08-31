# 02 — Legacy visual signature

Detectable markers of the older Merchant Dashboard. Canonical `/dashboard` V2 must contain **none** of the MUST_NOT / ROLLBACK_ONLY markers unless `?cf_ui=v1`.

| Marker | Class |
|--------|-------|
| `merchant_app.html` | MUST_NOT_RENDER_CANONICALLY |
| `merchant_ui_v1` / `X-CartFlow-Merchant-Renderer: merchant_ui_v1` | ROLLBACK_ONLY |
| `merchant_frame_v1.css` | ROLLBACK_ONLY |
| `home_executive_summary_v1.js` / `HomeExecutiveSummaryV1` | ROLLBACK_ONLY |
| `merchant_experience_home_v1.css` / `merchant_dashboard_home_v1.css` | ROLLBACK_ONLY |
| `data-cf-frame="v1"` / `.cf-rail` / `.cf-rail__brand` | ROLLBACK_ONLY |
| `.meif-card` / `.meif-facts` equal-card grid | LEGACY_ONLY |
| `merchant_ui_v2_language.css` | STILL_SHARED (V2 only) |
| `GET /api/dashboard/summary` | STILL_SHARED |
| `GET /api/cart-workspace/v1/projection` | STILL_SHARED |

Code: `services/merchant_visual_identity_v1.py` → `LEGACY_SIGNATURE`, `FORBIDDEN_CANONICAL_MARKERS`.
