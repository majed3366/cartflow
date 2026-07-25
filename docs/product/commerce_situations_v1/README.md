# Commerce Situation Engine V1

Canonical merchant-understandable **commercial situation** layer.

## Pipeline

```text
Operational Truth → Observations → Correlations → Business Facts
        ↓
Commerce Situation Engine   ← canonical business object
        ↓
Home · Decision Workspace · Products · Carts · Communication
```

## Law

- One Situation = one merchant commercial situation (entity-bound).
- Many Facts may feed one Situation.
- Facts never publish directly when Situations are enabled.
- Home introduces; Workspace explains; Products/Carts/Communication consume the same `situation_id` without reinterpretation.
- Not Theme-style type buckets (failed Production Reality Validation).
- No Product Intelligence. No invented recommendations. Gates 3–7 LOCKED.

## Ownership fields

`title` · `business_question` · `why_it_matters` · `affected_products/customers/carts` · `supporting_facts` · `evidence` · `confidence` · `merchant_action` · `expected_business_impact`

## Flag

`CARTFLOW_COMMERCE_SITUATIONS_V1` default **ON**.

## Probe

`GET /dev/commerce-situations?store=demo`

## Module

`services/commerce_situations_v1/`
