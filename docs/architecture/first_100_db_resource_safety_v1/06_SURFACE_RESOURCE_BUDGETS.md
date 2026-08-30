# Active surface budgets

| Surface | Concurrent DB-bound GETs (lazy V2) | Hold class | Notes |
|---|---|---|---|
| Home | 1 (summary) | FAST/HEAVY live | Snapshot mode preferred |
| Workspace | 1 (projection) | FAST cache / HEAVY fallback | Fallback now admission-gated (global 4, per-route 2) |
| Carts | 1 (normal-carts) | NORMAL/HEAVY | Bulk schedules/logs now limited |
| Communication | 3 (messages, followups, summary) | NORMAL | messages admission-gated; Promise.all kept (SAFE when Communication is the only active surface) |
| Settings | 3 sequential | FAST/NORMAL | QueuePool remediation preserved |

One active surface must not depend on an idle system. Communication remains the widest single-surface concurrency (3). Admission prevents messages from stacking with other heavy fallbacks beyond 4 global.
