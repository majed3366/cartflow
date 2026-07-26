# Mobile / Desktop Semantic Parity Report V1

**Rule:** Different layout is allowed. Different understanding is forbidden.

## Canonical payload

Both viewports consume the same:

- `merchant_publication_v1` (after slim transport)
- `home_executive_summary_v1.sections` (Home)
- Workspace `zone_b` after `apply_publication_priority_to_decisions_v1`

## Fingerprint fields

`semantic_parity_fingerprint_v1()` compares:

- store condition status + summary
- primary action / subject / situation id
- communication summary
- cart summary
- secondary titles
- truth_version + simulation_run_id
- opportunity_count

## Automated proof

`tests/test_executive_control_parity_v1.py::SemanticParityTests`

Desktop and Mobile screenshots in the CEO pack must show identical:

1. Store condition wording  
2. Primary decision / action  
3. Priority order  
4. Affected product  
5. Cart + communication meaning  
6. Secondary situation set (when shown)
