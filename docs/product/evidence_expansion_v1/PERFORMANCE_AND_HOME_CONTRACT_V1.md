# Performance & Home Contract — Evidence Expansion V1

## Home contract

Home never changes for Evidence Expansion.

- Home only consumes **published diagnoses** (Diagnostic Reasoning publication / HES).
- Evidence Expansion runs **completely outside** the Home request path.
- Evidence Gaps are **never** attached to dashboard summary, HES, or merchant publication.

## Performance contract

| Concern | Rule |
|---------|------|
| Merchant HTTP | Snapshot read only; no gap compose |
| Collection | Background (future collectors) |
| Processing / comparison | Background |
| Gap register | After diagnostic materialize in snapshot builder / CLI |
| Publishing diagnoses | Existing snapshot path |

## Wiring

1. `dashboard_snapshot_builder_v1` materializes diagnostics (background).
2. Diagnostic orchestrator calls `register_evidence_gaps_from_diagnostics_v1`.
3. Gaps upsert into `evidence_gaps`.
4. Home finalize / summary read path: **no reference** to Evidence Expansion payloads.

## Future consumers (not this phase)

Evidence Expansion becomes the permanent source for prioritizing:

- better diagnoses
- better recommendations
- Product Intelligence
- Knowledge Layer
- Decision Workspace
- Merchant Reports

Future intelligence must come from **richer evidence**, not more speculation.
