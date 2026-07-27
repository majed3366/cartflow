# Evidence Gap Registry V1

**Internal only.** Never expose to merchants, Home, Workspace, or reports UI.

## When a gap opens

A gap is composed when a diagnostic contract has:

- `diagnosis_status = insufficient_evidence`, or
- `diagnosis_status = conflicting_evidence`

## Persisted fields

| Field | Purpose |
|-------|---------|
| `gap_id` | Stable id (`store` + `family` + `diagnostic_id` + version) |
| `diagnostic_family` | Family that failed to resolve |
| `competing_causes` | Causes under consideration |
| `evidence_available` | What we already observed / scored |
| `evidence_missing` | Observables that would separate causes |
| `possible_future_observables` | Keys from the governed catalog |
| `priority` | `high` / `medium` / `low` |
| `gap_status` | `open` → `partially_filled` → `resolved` / `superseded` / `suppressed` |
| `reopen_reason` | Required to move terminal → `open`; empty reason preserves terminal |
| `internal_only` | Always `true` |
| `merchant_safe` | Always `false` |

### Lifecycle rule

`resolved` / `superseded` / `suppressed` must **not** silently reopen on rematerialization. Upsert calls `resolve_gap_status_transition_v1`; terminal → `open` requires a non-empty `reopen_reason`.

## Storage

- Table: `evidence_gaps` (`models.EvidenceGap`)
- Schema ensure: `schema_evidence_expansion_v1.ensure_evidence_expansion_schema`
- Upsert: `services/evidence_expansion_v1/gap_store_v1.py`
- List (internal tooling): `list_open_evidence_gaps_v1` — **do not** wire into `/api/dashboard/summary`

## Example (shipping stage)

**Observation:** Customers leave after Shipping.

**Competing causes:** Shipping Cost, Delivery Time, Shipping Options, Payment, Unknown.

**Available:** Left after shipping (stage observation).

**Missing (registry):**

- `shipping_option_selected`
- `shipping_cost_first_shown`
- `delivery_estimate_shown`
- `payment_attempt_after_shipping`
- `return_after_shipping_step`
- …

**Result:** Merchant sees insufficient evidence. Engineering registry stores the gap.
