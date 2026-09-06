# Tenant identity — Founder Production Evaluation Tenant V1

## Canonical identity

| Field | Value |
|-------|-------|
| `store_slug` / `Store.zid_store_id` | `cf_founder_evaluation` |
| Merchant email | `founder.evaluation@cartflow.local` |
| Display name | `CartFlow Founder Evaluation` |
| `integration_source` | `founder_production_evaluation_v1` |
| WhatsApp recovery | `False` (forced on ensure) |

Constants live in `services/founder_production_evaluation_tenant_v1/contract_v1.py`.

## Isolation properties

- Isolated from demo / sandbox merchants
- Isolated from any real customer merchant
- Normal tenant isolation applies (all reads/writes scoped by authenticated `store_slug`)
- Authenticated merchant login required (`/dashboard` session)
- No special global admin bypass
- Internally identifiable as evaluation-only via `integration_source`
- Slug reserved — must not be issued as a customer `store_slug`

## Not this tenant

| Identity | Role |
|----------|------|
| `cf_fe_v1_*` | Local/test founder **fixtures** (`founder_evaluation_v1`) — logic only |
| `demo` / commerce sandbox | Demo — not evaluation gate |
| Real Zid merchant slugs | Production customers — evaluation features OFF |

## Bootstrap

Ops-only, explicit call (not on every request, not Scheduler):

```python
from services.founder_production_evaluation_tenant_v1 import (
    ensure_founder_production_evaluation_tenant_v1,
)

ensure_founder_production_evaluation_tenant_v1()
```

Rotate `FOUNDER_EVAL_BOOTSTRAP_PASSWORD` in production ops before first founder login.

## Access path

Normal merchant path only:

1. Login with evaluation merchant email
2. `GET /dashboard` (Merchant UI V2)
3. Store context from session ownership — never from client-supplied `store_slug` body/query for gate decisions

No `/dev` route. No hidden lab route for founder product pass.
