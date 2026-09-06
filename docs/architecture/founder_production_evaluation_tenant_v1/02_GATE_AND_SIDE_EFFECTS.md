# Gate + side-effect policy — Founder Production Evaluation Tenant V1

## Server-side owner

```text
is_founder_production_evaluation_tenant(...)
```

Alias: `is_founder_evaluation_tenant` (same function object).

Ownership package: `services/founder_production_evaluation_tenant_v1/gate_v1.py`

## Production evaluation allowlist (count = 1)

| Identity | Eligible |
|----------|----------|
| `cf_founder_evaluation` | YES |
| `cf_fe_v1_*` | **NO** (test fixtures only) |
| demo / normal merchants | NO |
| query params / frontend flags | NO |
| environment-global merchandising release | **NO** (removed from production gate) |

## Authoritative input

- Authenticated `Store` row (`zid_store_id` / `integration_source`) wins over caller-supplied slug.
- COL attach accepts `authenticated_store_slug=` and overwrites `summary["store_slug"]`.
- Home / snapshot paths pass session-owned store slug into attach.

## Merchandising projection

| Path | Merchandising families |
|------|------------------------|
| Production founder tenant | Allowed |
| Production request with `cf_fe_v1_*` slug only | **Denied** |
| Test infra `CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE=1` | Allowed (tests/local only) |
| Normal / demo merchants | Denied (`merchandising_eval_tenant_gate`) |

Gate controls **projection/availability**, not truth validity.

## External side-effect policy

Default block for founder production tenant **and** `cf_fe_v1_*` fixtures (safety; does not grant feature eligibility):

- Twilio WhatsApp send
- Meta Cloud send
- Customer communications via send path

Internal COL / CDC / catalog / portfolio / merchandising missions: allowed.

Error: `founder_evaluation_tenant_side_effects_blocked`
