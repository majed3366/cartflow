# 07 — Controlled restoration design

Authoritative: current product semantics, V2 runtime, current shell, current data contracts. Visual System V1 defines identity. No wholesale file restore.

## Minimum change

1. **Selection:** ignore `cf_ui_v2=0`; persist only `=1`; heal leftover `=0` on canonical `/dashboard`.
2. **Identity:** expose `visual_system_version` + `X-CartFlow-Merchant-Visual-System`.
3. **Contract tests:** required emitters present; forbidden legacy markers absent on default `/dashboard`.
4. **Regression gate:** `MERCHANT_VISUAL_IDENTITY_REGRESSION_GATE`.

No Home / Workspace / Carts / Communication / Settings painter or CSS restyle. Those already match Visual System V1 when V2 is selected.
