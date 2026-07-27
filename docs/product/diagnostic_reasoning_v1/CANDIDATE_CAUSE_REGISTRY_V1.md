# Candidate Cause Registry V1

Governed in `services/diagnostic_reasoning_v1/cause_registry_v1.py`.

## Families

- `checkout_abandonment_after_shipping`
- `interest_without_purchase`
- `payment_friction_at_checkout`
- `contact_followup_blocked`

## Rule

Generic stage signals (e.g. `shipping`) never alone select `shipping_cost`.  
Missing subtype capture → `insufficient_evidence`.
