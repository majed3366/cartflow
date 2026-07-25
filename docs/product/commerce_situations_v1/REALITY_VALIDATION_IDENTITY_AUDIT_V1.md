# Reality Validation Identity Audit V1

> **Superseded by** [`REALITY_VALIDATION_IDENTITY_CERTIFICATION_V1.md`](./REALITY_VALIDATION_IDENTITY_CERTIFICATION_V1.md) — use `CEO_REVIEW_SAFE` certification before every CEO review.

## Purpose

CEO proves in &lt;30 seconds that Living Store simulation, merchant session, and every merchant surface read the **same** dataset.

## Probe

```http
GET /dev/reality-validation-context?store=demo
```

Production-allowlisted.

## Response (flat)

| Field | Meaning |
|-------|---------|
| `status` | `CONSISTENT` or `INCONSISTENT` |
| `store_slug` | Canonical store |
| `merchant_id` | Review / owning merchant |
| `simulation_run_id` | Living Store SRS run |
| `environment` / `database_environment` | App + DB dialect |
| `living_store_profile` | `living_store` |
| `last_simulation_timestamp` | Last run time |
| `facts` / `situations` / `observations` | Dataset counts |
| `home_projection` … `carts_projection` | Per-surface Situation counts |
| `divergence_begins_at` | First `surface.field` that differs |
| `surfaces.*` | Full identity block per surface |

## Surfaces audited

1. Living Store simulation  
2. Authenticated merchant session  
3. Home  
4. Decision Workspace  
5. Products  
6. Carts  
7. Communication  

## Law

No further UX or intelligence work until this audit reports **CONSISTENT**.
