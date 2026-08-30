# Observability

Already present: `request_timing_audit_v1` checkout wait/hold; `db_request_audit` query counts; `db_pool_diagnostics` / `db_pool_pressure_v1` (checked_out, overflow, timeout_count, pressure level, scanner circuit breaker).

Added: `observability_v1.record_hold` classifies each checkin into FAST/NORMAL/HEAVY/UNSAFE/CRITICAL and logs violations. Wired from the existing pool checkin listener (Postgres QueuePool only; NullPool skips the listener).

No external APM.
