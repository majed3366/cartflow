# Economic Input Contract V1

Design only. This task defines the required inputs. It does not implement
acquisition of any of them.

## 1. Manifest

Each field declares **authority** (who is allowed to assert it), **freshness**
(how old a value may be before it stops counting), **scope** (the grain it is
valid at), and **missing-state behavior**.

Observed status is grounded in the current schema, not assumed.

| Field | Authority | Freshness | Scope | Status today |
| --- | --- | --- | --- | --- |
| `shipping_cost` | Merchant declaration or platform shipping settings | ≤ 30 days | store, optionally per shipping zone | **MISSING** — no column, no integration |
| `shipping_subsidy` | Merchant declaration | ≤ 30 days | store | **MISSING** |
| `product_cost` / COGS | Merchant declaration or platform cost field | ≤ 90 days | product identity (`stable_identity_key`) | **MISSING** |
| `gross_margin` | Derived: `price − product_cost − fees` | Inherits worst input | product identity | **MISSING** — blocked by `product_cost` |
| `margin_floor` | Merchant policy declaration only | ≤ 180 days, explicit merchant re-confirm | store | **MISSING** — never inferable |
| `payment_fees` | Platform / payment provider settings | ≤ 90 days | store | **MISSING** |
| `platform_commission` | Platform settings | ≤ 90 days | store | **MISSING** |
| `inventory_quantity` | Platform inventory feed | ≤ 24 hours | product identity | **MISSING** — no inventory column anywhere in schema |
| `AOV` | Derived from cart/purchase truth | ≤ 30 days rolling | store | **PARTIAL** — see §2 |
| `product_pair_counts` | Derived from `cart_line_snapshots` co-occurrence | ≤ 90 days rolling | store, product pair | **DERIVABLE** — but evidence, not economics |

Ten fields, of which eight are fully missing, one is partial, and one is
derivable. No Level 3 intervention is computable today, and this is a structural
fact about the schema rather than a tuning decision.

## 2. What economic truth actually exists

CartFlow knows what a customer **pays**. It does not know what the merchant
**keeps**.

Present and authoritative:

- `product_catalog_entries.price` + `currency` + `last_synced_at` — current selling price
- `cart_line_snapshots.unit_price` + `quantity` — immutable historical cart lines
- `abandoned_carts.cart_value` — cart value at abandonment

`AOV` is marked PARTIAL for a specific reason: `purchase_truth_records` records
that a purchase happened (`purchase_detected`, `order_id`, `purchase_time`) but
carries **no monetary amount**. Order value is therefore not authoritative. Any
AOV derived today is cart-scoped at abandonment, not order-scoped at purchase,
and must be labelled as such. It cannot be used as a revenue metric.

This is also why the measurement contract refuses revenue as a primary metric:
revenue is not merely insufficient, it is currently not measurable.

## 3. Economic safety contract

A Level 3 intervention may be emitted only if all four of these are computable
from authoritative inputs:

| Quantity | Definition |
| --- | --- |
| `intervention_direct_cost` | Per-order cost the intervention transfers to the merchant |
| `margin_after_intervention` | `gross_margin − intervention_direct_cost` |
| `margin_floor` | Merchant-declared minimum acceptable margin |
| `stop_loss_condition` | Explicit condition that halts the intervention before the window ends |

Rule: `margin_after_intervention ≥ margin_floor` must be provable **before** the
intervention is shown, not after it is measured.

If any required input is missing:

```
eligibility_state = ECONOMIC_INPUTS_REQUIRED
```

### No-fallback rule

There is no default, no industry benchmark, no assumed margin, no inferred
shipping cost, and no "typical" threshold. A guessed default produces a
recommendation that looks identical to a governed one, which is the exact failure
this contract exists to prevent. A missing input blocks the level; it never
degrades into an estimate.

Merchant-declared values are authoritative for their own store but must be
recorded as declarations with a timestamp, and must expire per the freshness
column above. A stale declaration is treated as missing, not as approximate.

## 4. Level 4 additional inputs

Beyond the full Level 3 set:

- `product_pair_counts` with a sufficiency threshold (co-occurrence alone is correlation)
- `inventory_quantity` per candidate product, fresh within 24 hours
- product-level economics for **both** products in the pair
- shipping impact of adding the second product (weight, zone, packaging)
- compatibility evidence — the pair must make sense, not merely co-occur

Recommending a specific out-of-stock or margin-negative complementary product is
worse than recommending nothing, which is why Level 4 requires inventory
freshness an order of magnitude tighter than every other field.

## 5. Acquisition is out of scope

This task does not add columns, integrations, merchant input forms, or sync jobs
for any field above. The manifest exists so that eligibility can honestly report
`missing_inputs` and so that a future acquisition task has a fixed target.
