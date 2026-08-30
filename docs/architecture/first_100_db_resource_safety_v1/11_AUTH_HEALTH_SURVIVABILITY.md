# Auth and health survivability

| Route | Under ordinary pressure | Under pool saturation (before) | After |
|---|---|---|---|
| `/ping` | no DB | stays up | unchanged |
| `/health` | no DB | stays up | unchanged |
| `/health?db=1` | SELECT 1 | 503 after 5s checkout timeout | if pool HIGH/CRITICAL, 503 immediately with `database=pool_pressure` (honest; no lie, no 5s wait) |
| `/login` | FAST/NORMAL | can stall if pool exhausted | still uses DB; protected by admission leaving reserved slots |
| Dashboard auth resolve | FAST cookie queries | timeout/redirect | still FAST; early checkout remains (L) |

`/health?db=1` 503 under saturation is **unavoidable if we refuse to lie** when the pool cannot serve a probe. Waiting 5s then 503 was the architectural violation.
