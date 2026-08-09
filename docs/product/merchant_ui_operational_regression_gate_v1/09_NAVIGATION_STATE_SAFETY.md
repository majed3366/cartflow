# Gate 9 — Navigation State Safety

Artifact: `navigation_state_probe.json`

| Check | Result |
|-------|--------|
| Home → Workspace → Home | Hash/nav correct; ends `#home` |
| Active page count | Always **1** |
| Page roots | 6 section roots; one `is-active` |
| Ctx open/close | Works on mobile; does not change API truth |
| Account utility drawer | Opens/closes; does not steal Global ownership |
| Bound Global nav flags | 6 stable (no duplicate binders) |
| Shell marker | `shell-integration-v1` throughout |
| Legacy DOM | All false |

Contextual navigation does not mutate business payloads.
