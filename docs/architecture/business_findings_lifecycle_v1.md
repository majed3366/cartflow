# Business Findings Lifecycle V1 (BFL)

**Status:** Lifecycle foundation  
**Flag:** `CARTFLOW_BUSINESS_FINDINGS_LIFECYCLE_V1` (default on)  
**Probe:** `GET /dev/business-findings-lifecycle?store=demo`  
**Table:** `business_findings` (Alembic `i8j9k0l1m2n3`)

## Purpose

Establish Business Findings as **first-class durable platform objects**, not temporary Home calculations.

Required path:

```
Evidence → Business Finding → Persisted → Knowledge → Guidance →
Operational Truth (route decision) → Surface Eligible → Merchant Surfaces
```

## Non-goals (this chapter)

- No UI polishing, Home redesign, or new cards
- No Decision Workspace / Knowledge / Guidance generators of findings
- Surfaces **consume only**

## Canonical object fields

Every finding record includes: `finding_id`, `finding_type`, `merchant_id`, `product_id` (nullable), `category_id` (nullable), `evidence`, `confidence`, `severity`, `generated_at`, `expires_at` (nullable), `lifecycle_state`, `visibility_state`, `reasoning`, `recommended_action`.

## Lifecycle states (no skips)

`detected` → `validated` → `persisted` → `knowledge_routed` → `operational_truth_routed` → `surface_eligible` → `displayed` → `resolved` / `archived`

Illegal transitions are rejected by `lifecycle_v1.can_advance`.

## Generation vs consumption

| Layer | Role |
|-------|------|
| `materialize_business_findings_lifecycle_v1` | **Only** production generation entry (engine + sanitize + persist + routes) |
| Home / HCI | `load_current_findings_package_v1` — consume persisted; mark `displayed` |
| Decision / Knowledge / Guidance | Must not call `run_business_findings_engine_v1` for merchant surfaces |
| Labs / demos | May still call the engine for review fixtures |

## Routing

- **Knowledge:** parallel `KnowledgeStatement` with `source_type=business_finding`, `knowledge_type=business_finding_observation` (ECF generator untouched)
- **Guidance:** explicit route record — does not generate guidance; consumable via knowledge lineage
- **Operational Truth:** commercial findings are **not** OT packages; route decision recorded; lifecycle advances
- **Surface:** `visibility_state=eligible` when `home_eligible`; destinations include `merchant_home` / `decision_workspace`

## Observability

Per finding diagnostics:

- `generated` / `persisted` / `routed` / `surface_eligible` / `displayed`
- `stopped_at` = last lifecycle stage reached

Probe returns materialize counters + per-finding diagnostics so a disappeared finding identifies the exact stop stage.

## Package layout

`services/business_findings_lifecycle_v1/` — types, flag, lifecycle, normalize, persistence, route, materialize, consume_home, prod_probe.
