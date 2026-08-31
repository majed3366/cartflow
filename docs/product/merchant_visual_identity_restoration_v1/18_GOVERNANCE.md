# 18 — Governance (amends Merchant Visual System V1)

Future material Merchant UI change requires:

1. Canonical runtime proof (`/dashboard`, not `/`)
2. Visual-system compliance (P1–P16 as specified per surface)
3. Figma traceability if a primitive is added or moved
4. Mobile proof (1023px law)
5. Logo-hidden coherence
6. `MERCHANT_VISUAL_IDENTITY_REGRESSION_GATE` PASS
7. Exact production proof: SHA = identity headers = delivered assets = rendered DOM = founder-visible V2

No visual change may be approved from a non-canonical route, a leftover V1 cookie session, or landing `/`.

V1 remains rollback-only via `?cf_ui=v1` or ops env. Cookie `cf_ui_v2=0` is not a legal selector.
