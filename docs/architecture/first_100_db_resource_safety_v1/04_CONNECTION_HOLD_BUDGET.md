# Connection hold budget V1

Binding thresholds (`services/db_resource_safety_v1/hold_budget_v1.py`):

| Class | Hold | Verdict |
|---|---|---|
| FAST | < 250ms | WITHIN_BUDGET |
| NORMAL | < 1s | WITHIN_BUDGET |
| HEAVY | 1–3s | JUSTIFIED_HEAVY only on listed routes |
| UNSAFE | > 3s | VIOLATION |
| CRITICAL | any hold across external/network wait | VIOLATION |

Justified heavy routes: projection, normal-carts, messages, cart-event.

Measured locally on NullPool: checkout listeners are not installed (no QueuePool). Hold classification is armed for production-like Postgres.
