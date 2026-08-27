# Test Evidence

**Date (UTC):** 2026-08-27  
**Infrastructure:** local pytest + SQLite only. No production host, no Railway API, no production Postgres.

## Suites run

```
tests/test_cost_recurrence_prevention_v1.py
tests/test_recovery_scheduler_guardrails_v1.py
tests/test_recovery_process_role_v1.py
tests/test_scheduler_ownership_diagnosis_v1.py
tests/test_reliability_foundation_phase0_v1.py
tests/test_recovery_health_v1.py
tests/test_dashboard_snapshot_loop_continuous_v1.py
tests/test_recovery_db_due_scanner_loop.py
tests/test_db_session_lifecycle_scheduler_v1.py
tests/test_scheduler_deployment_verify_v1.py
tests/test_recovery_db_due_scanner.py
tests/test_scheduler_meta_runtime_startup_v1.py
tests/test_scheduler_meta_preflight_v1.py
```

## Coverage map

| Requirement | Tests |
|-------------|--------|
| Process separation / fail-closed role | `ProcessEntryTests`, `test_api_startup_does_not_start_scheduler_loops`, `test_scheduler_entry_does_not_import_fastapi_app` |
| Private host accepted | `DatabaseNetworkGuardTests.test_private_railway_accepted` |
| Public proxy rejected | `test_public_proxy_rejected` |
| Missing / malformed URL | `test_missing_rejected`, `test_malformed_rejected` |
| Emergency override | `test_emergency_override` |
| Secrets absent from errors | `test_secrets_never_in_error` |
| Interval / backoff / no zero-sleep | `SchedulerIntervalTests` |
| Non-overlap | `test_no_overlapping_ticks` |
| Single-instance lock | `test_postgres_lock_not_acquired_fails_closed`, `test_skip_instance_lock_flag` |
| Snapshot byte budget | `test_byte_budget_aborts`, `test_many_records_remain_bounded` |
| Empty DB not busy | `test_empty_cycle_not_busy` |
| Healthcheck no DB query | `HealthNoDbTests.test_health_snapshot_does_not_query_db` |
| Pool bounds | `PoolBoundsTests`, `PoolConfigTests` |
| Jobs default OFF | `SnapshotBuilderDefaultOffTests`, `test_default_unset_enables_resume_scan_in_development` (now asserts False), scanner loop `test_disabled_by_default` |
| Recurring `create_all` removed | `test_scanner_source_has_no_create_all` |

## Result

**129 passed**, 3 warnings, 35.01s (2026-08-27 UTC). All listed tests use SQLite or mocks. None connect to Railway or production Postgres.

Pool-engine inspection uses a localhost DSN only to read SQLAlchemy pool attributes; the previous engine is restored. No live Postgres is required.
