# Merchant UI Production Config Parity Regression Gate V1 — REPORT

**Date (UTC):** 2026-09-01  
**Base SHA:** `5606530c736416c0141b2f4a7f2cfef0e92290bc`  
**Invariant:** `MERCHANT-UI-INV-CONFIG-01`  
**Gate:** `MERCHANT_UI_PRODUCTION_CONFIG_PARITY_REGRESSION_GATE`

## Material Merchant UI flags (3)

| Flag | Default | Normalization | Production effective |
|------|---------|---------------|----------------------|
| `CARTFLOW_CART_WORKSPACE_V1` | false | explicit bool; else Railway SHA → ON; else OFF | **true** |
| `CARTFLOW_MERCHANT_UI_V2` | true | env truthy/falsey; unset → default ON | **true** |
| `CARTFLOW_CARTS_V2_UI` | true | unset/empty → ON; explicit falsey → OFF; unrecognized → **unresolved** | **true** |

Affect axes covered: renderer family, page availability, composition path, data projection path, visual state path, mobile behavior, canonical route behavior.

## Production / review identity

Inspectable via `production_merchant_ui_config_identity()` / `review_merchant_ui_config_identity()` and `/dev/merchant-runtime-identity` fields:

- `merchant_ui_config_version`
- `merchant_ui_material_flags`
- `merchant_ui_production_material_flags`
- `merchant_ui_config_parity`

No secrets.

## Automated cases

| Case | Result |
|------|--------|
| A review == production | PASS |
| B one material flag differs | FAIL (fail-closed) |
| C raw differs, effective equal | PASS |
| D unresolved effective | FAIL (fail-closed) |
| E unrelated non-Merchant-UI env | does not fail gate |

## Visual deploy authorization

`evaluate_merchant_visual_deploy_authorization` requires:

1. VISUAL CONTRACTS = PASS  
2. SEMANTIC REGRESSION = PASS  
3. REAL-DEVICE REVIEW = PASS  
4. PRODUCTION CONFIG PARITY = PASS  

Else `safe_for_exact_sha_deploy = false`.

## Visual re-verify (governance-only change)

Painters/CSS untouched. Prior real-device PASS on `5606530c` under production-equivalent config remains the visual evidence. Organism markers still present in candidate static (`gravity-well`, `formation`, `weighted-queue`, `lifecycle-continuum`, `config-ledger`).
