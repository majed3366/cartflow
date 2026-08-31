# 06 — Visual invariants

| ID | Law |
|----|-----|
| INV-VIS-01 | Canonical `/dashboard` V2 must never render the legacy V1 dashboard composition. |
| INV-VIS-02 | Home and Decision Workspace must retain approved signature primitives (P12–P16 as specified). |
| INV-VIS-03 | Carts / Communication / Settings stay assimilated (same product language, page-specific responsibility). |
| INV-VIS-04 | Mobile preserves canonical structure; no legacy composition fallback. |
| INV-VIS-05 | Incomplete truth may reduce density; it must not remove CartFlow identity. |
| INV-VIS-06 | Visual state changes must not switch renderer families. |
| INV-VIS-07 | Rollback-only V1 must never be selected silently by leftover cookie or other normal Merchant UI state. Only `?cf_ui=v1` or ops `CARTFLOW_MERCHANT_UI_V2=0`. |
| INV-VIS-08 | Future visual change must pass `MERCHANT_VISUAL_IDENTITY_REGRESSION_GATE` before production deploy. |
