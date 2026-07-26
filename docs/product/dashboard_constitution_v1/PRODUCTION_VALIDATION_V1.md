# Dashboard Constitution V1 — Production Validation

**Generated (UTC):** 2026-07-26T22:11:37.092527+00:00  
**Verdict:** `FAIL_CONSTITUTION_PROD`  

## Precondition (certified Living Store)

| Field | Value |
|-------|-------|
| status | `CONSISTENT` |
| CEO_REVIEW_SAFE | `True` |
| store_slug | `demo` |
| simulation_run_id | `srs_354a106febbd4e48bc45d1e6999fa393` |

## Acceptance flags

```json
{
  "parity_ok": true,
  "any_tech": false,
  "same_run": true,
  "carts_operational_only": true,
  "comms_facts": false,
  "empty_hash_home": false,
  "month_wall_hidden": true,
  "purposes_ok": false
}
```

## Deploy

```json
{
  "deployed": true,
  "attempt": 1,
  "last_attempts": [
    {
      "n": 1,
      "marker_app": true,
      "marker_comms": true
    }
  ]
}
```

## Screenshots

Desktop + Mobile: Home, Workspace, Products, Carts, Communication, Settings under `docs/product/dashboard_constitution_v1/prod_*.png`.
