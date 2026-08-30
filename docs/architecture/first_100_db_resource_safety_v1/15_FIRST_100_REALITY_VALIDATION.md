# First-100 reality validation

Local critical-route burst (`_validate_local.py`, TestClient, SQLite NullPool):

| Scenario | n | ok | fail | max_ms | admission after | result |
|---|---|---|---|---|---|---|
| A 1 merchant | 3 | 3 | 0 | 65 | idle | PASS |
| B multiple tabs | 4 | 4 | 0 | 36 | idle | PASS |
| C 10 | 10 | 10 | 0 | 105 | idle | PASS |
| D 25 | 25 | 25 | 0 | 228 | idle | PASS |
| E 50 | 50 | 50 | 0 | 374 | idle | PASS |
| F 100 | 100 | 100 | 0 | 528 | idle | PASS |

Paths: `/ping`, `/health`, `/login`.

Contract tests: 29 passed (safety + fan-out + Settings QueuePool).

Limits of this validation:

- Local engine is NullPool — QueuePool checkout wait/timeout cannot be reproduced here.
- This is not 100 distinct production merchants on mixed surfaces against Postgres.
- Production mixed-surface First-100 against live Railway is **not run** (this SHA is not deployed).
