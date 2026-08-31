# 04 — Version selection audit

Mechanisms that can choose V1 vs V2.

| Mechanism | Classification | Effect |
|-----------|----------------|--------|
| Default (`DEFAULT_MERCHANT_UI_V2=True`) | **CANONICAL** | `/dashboard` → V2 |
| `?cf_ui=v2` | **CANONICAL** | Force V2; persists cookie 14d |
| `?cf_ui=v1` | **ROLLBACK_ONLY** | Force V1; persists `cf_ui_v2=0` 14d |
| Cookie `cf_ui_v2=1` | **CANONICAL** | Persisted explicit V2 |
| Cookie `cf_ui_v2=0` | **ROLLBACK_ONLY** | Persisted explicit V1 — **was hidden** until identity markers |
| `CARTFLOW_MERCHANT_UI_V2=1` | **CANONICAL** | Env force V2 |
| `CARTFLOW_MERCHANT_UI_V2=0` | **ROLLBACK_ONLY** | Env force V1 |
| `/dev/merchant-ui-v2` | **DEV_ONLY** | Sets V2 cookie |
| `/dev/merchant-ui-v1` | **ROLLBACK_ONLY** | Sets V1 cookie |
| `/dev/living-store-home-review` | **CANONICAL** | Bind + force V2 cookie |
| localStorage / sessionStorage | **none** | Not used for UI version |
| Landing `/` | **not a selector** | Not Merchant UI |

Priority (highest first): query → cookie → env → default.

## Governance

- Normal merchant verification uses **default V2** or `?cf_ui=v2`.  
- V1 is rollback / compare only.  
- Identity `selection_source` must be `query` | `cookie` | `env` | `default` | `review_bind`.  
- A visual PASS that did not record `selection_source` is invalid.

**UNSAFE_AMBIGUITY remaining in this repo after closure: 0.**  
The V1 cookie still exists as an explicit rollback control; it is no longer hidden.
