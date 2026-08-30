# Long query findings

Do not confuse request latency with DB hold duration. At `58a82f3` the hold usually equals “first checkout → response end”.

| Path | Slowness source | Class |
|---|---|---|
| `/api/cart-workspace/v1/projection` enrich_fallback | APPLICATION COMPUTE + snapshot miss, not a single bad SQL | HEAVY / UNSAFE under pressure |
| `/api/dashboard/messages` | LIVE path, over-fetch, unbounded reply map | NORMAL after bounds |
| `/api/dashboard/normal-carts` live | SNAPSHOT BUILD / bulk reads; RecoverySchedule and MessageLog were unbounded | HEAVY |
| Recovery execute + WhatsApp | EXTERNAL WAIT while session held | CRITICAL (now released before send) |
| `/health?db=1` under saturation | POOL CHECKOUT WAIT (5s timeout) | architectural violation, not DB slowness |

Projection and messages remain JUSTIFIED_HEAVY when they stay inside 3s and do not wait on network.
