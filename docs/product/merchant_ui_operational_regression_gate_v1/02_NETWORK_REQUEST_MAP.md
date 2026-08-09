# Gate 2 — Network / Request Behavior

Artifact: `request_summary.json`

## Bounded counts (tracked xhr/fetch/document)

| Class | Count |
|-------|------:|
| dashboard_html | 1 |
| dashboard_summary | 2 |
| workspace_projection | 5 |
| api during Home/Workspace scroll | **0** |

## Phase map

| Phase | APIs |
|-------|------|
| home_initial | summary ×1 |
| home_scroll | none |
| nav_workspace | projection ×1 |
| workspace_scroll | **none** (CIM scroll does not fetch) |
| nav_home | summary ×1 |
| responsive_* | projection ×1 each (expected re-paint) |

## Validation

| Check | Result |
|-------|--------|
| Request storms | **No** |
| Infinite reload | **No** |
| Full dashboard HTML reload on hash nav | **No** (hash `go()` only) |
| CIM scroll fetches | **No** |
| Duplicate calls from visual-only components | **No** |

Workspace projection ×5 = 1 navigation + 4 responsive breakpoints in the probe — not a storm.
