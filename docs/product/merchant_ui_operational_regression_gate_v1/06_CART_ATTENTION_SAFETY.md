# Gate 6 — Cart / Attention State Safety

## Code path

`merchant_ui_v2_{app,home,workspace}.js` contain **no** cart lifecycle writers, attention mutators, or state classifiers.

Home consumes `GET /api/dashboard/summary` (includes recovery/cart revision tokens and KPI fields). Workspace consumes projection only.

## Conclusion

UI presentation work did **not** relocate cart/attention classification into the client. Canonical lifecycle/attention truth remains server-side.

No mutation performed.
