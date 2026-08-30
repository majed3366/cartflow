# Remediation report

Reusable module: `services/db_resource_safety_v1/`

| Piece | Role |
|---|---|
| hold_budget_v1 | Binding FAST/NORMAL/HEAVY/UNSAFE/CRITICAL |
| admission_v1 | Global 4 / per-route 2 heavy-read cap |
| release_before_wait_v1 | Law helper |
| health_survivability_v1 | Honest fast 503 when pool cannot be probed |
| query_bounds_v1 | Named caps |
| observability_v1 | Hold class counters |

Wired at choke points only: WhatsApp send, Zid HTTP, password-reset email, `/health?db=1`, messages, projection enrich_fallback, four hot-path query limits.

`main.py` remains wiring for messages admission and the existing batch-read functions (those queries already lived there). Business/resource policy lives in `services/db_resource_safety_v1/`.

Preserved: Settings QueuePool remediation, V2 lazy surface init, pool size 5+5, timeout 5s.
