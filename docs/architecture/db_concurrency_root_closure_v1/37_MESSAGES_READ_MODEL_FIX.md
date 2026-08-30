# Messages read-model correction — implementation

**Status:** Local candidate. Not deployed. First-100 not rerun.  
**Base SHA:** `f613ec7145a5e29c56257187159bfe366c26b3c0`  
**Date (UTC):** 2026-08-30

## What changed

1. `ensure_timeline_table_ready` returns after process-verified schema (`timeline_schema_is_verified`) and does not call `_table_exists()` / `inspect(engine)`.
2. `enrich_message_history_rows_with_lifecycle` batches timeline (`bulk_timeline_status_sets`) and schedule (`prefetch_recovery_schedule_facts`) and classifies with `timeline_statuses` + `schedule_prefetched=True`.
3. `_api_json_dashboard_messages` materializes history + refresh into plain dicts (`compose_messages_payload`). The HTTP route calls `release_messages_db_phase` before `j()`. Shared in-process helpers do not `remove()` the session so later carts/stats can still use the same Store.
4. FINALLY logs `checkout_count` and `last_hold_ms`.
5. Admission comments record that remaining demand is one scoped checkout; limits 4/2 unchanged.

## Files

- `schema_recovery_truth_timeline.py`
- `services/recovery_truth_timeline_v1.py`
- `services/lifecycle_authority_recovery_v1.py`
- `services/dashboard_messages_read_v1.py` (new)
- `main.py` (`_api_json_dashboard_messages` only)
- `services/db_lifecycle_v1/http_bind.py`
- `services/db_resource_safety_v1/admission_v1.py` (comment)
- `tests/test_connection_demand_messages_read_v1.py`

## Checkout target

Do not invent a numeric target. Requirement: material reduction from ~60 with no truth regression.

Expected remaining **session** queries on one checkout (order): db_ready, store, sent logs, delivery map, reply map, lifecycle logs IN, timeline IN, schedule IN, refresh aggregates (~6). Engine inspects for this path after warm: **0**.

## Production proof (Phase 12)

Not run until local acceptance **and** exact-SHA deploy authorization. Bracket only 50 → 60 → 80 → 100. STOP at first failure. Do not rerun full First-100 from this document.
