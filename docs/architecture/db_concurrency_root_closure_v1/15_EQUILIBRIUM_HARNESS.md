# Phase 13 — Equilibrium harness

Permanent helper: `services/db_lifecycle_v1/equilibrium.py` → `run_four_phase`.

```
BASELINE → ACTIVITY → QUIESCENCE → EQUILIBRIUM
```

Metrics: baseline/peak/post `checked_out`, timeout delta, pass iff post ≤ baseline and timeouts == 0.

Local proof uses SQLAlchemy **QueuePool** (size 5, overflow 5, timeout 5) on SQLite. That validates checkout/checkin accounting, not Postgres `idle_in_transaction`.

Postgres + `pg_stat_activity` is the production stage (not run).
