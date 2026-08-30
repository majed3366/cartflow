# Messages checkout multiplicity + spanning-hold audit

**Status:** Classification complete. Optimization follows this document.  
**Live SHA (baseline):** `f613ec7145a5e29c56257187159bfe366c26b3c0`  
**Proven path:** `GET /api/dashboard/messages`  
**Date (UTC):** 2026-08-30

## Call graph (before)

```
GET /api/dashboard/messages
  maybe_reject_heavy_before_db          # admit 4/2, no DB
  admit_heavy_route (handler re-entry)
  _merchant_dashboard_db_ready          # REQUIRED (schema/warm)
  _dashboard_recovery_store_row         # REQUIRED (store identity)
  _api_json_dashboard_messages
    _merchant_recovery_message_history_rows
      sent_logs_for_store               # REQUIRED HISTORY_READ (1 query, cap 80)
      loop rows (≤40):
        context_from_log_row            # REQUIRED (column/JSON; not a checkout)
      _enrich_message_rows_with_communication_truth
        delivery truth IN               # REQUIRED (1 batch)
        customer reply IN               # REQUIRED (1 batch)
        _build_*_timeline               # application work while session held
      enrich_message_history_rows_with_lifecycle
        CartRecoveryLog IN              # REQUIRED (1 batch, cap 80/400)
        per recovery_key:
          attach_customer_lifecycle_state_v1
            _timeline_flags
              timeline_status_set
                get_recovery_truth_timeline
                  ensure_timeline_table_ready
                    ensure_recovery_truth_timeline_schema  # no-op after _schema_once
                    _table_exists → inspect(engine).has_table
                        # N_PLUS_ONE + engine checkout (bypasses scoped session)
                  SELECT timeline events                # REPEATED_LOOKUP
            _next_schedule_due_at                       # N_PLUS_ONE
            _scheduled_effective_delay_seconds          # N_PLUS_ONE (some states)
    _merchant_dashboard_refresh_state_payload
      3× CartRecoveryLog aggregates     # REQUIRED
      2× archive aggregates             # REQUIRED
      live_abandoned_cart_max_id        # REQUIRED
    last_send_ar / dict merge           # application work while session held
  j() → close_request_uow_if_clean      # late release
```

## Why ~60 checkouts?

Proven request `6b16a9dc5f0f4e84`: 61 checkout + 61 checkin, `request_ms=2145.3`.

SQLAlchemy scoped session reuses **one** connection for session queries. `inspect(db.engine).has_table` checks out a **second** engine connection per call. `ensure_timeline_table_ready` always called `_table_exists()` after schema-once. Lifecycle attach did that **per message row** (~40) plus per-row schedule lookups on the held session.

Classification of the ~60:

| Class | Count (order) | Verdict |
|-------|----------------|---------|
| N_PLUS_ONE (`inspect.has_table` via `_table_exists`) | ~40 | DUPLICATE after process-verified schema |
| REPEATED_LOOKUP (`timeline_status_set` / timeline SELECT) | ~40 session queries on the spanning checkout | Avoidable via `bulk_timeline_status_sets` |
| N_PLUS_ONE (schedule due/delay) | up to ~40 session queries | Avoidable via one schedule IN |
| REQUIRED store/logs/delivery/reply/refresh | ~8–12 session queries | Keep |
| LIFECYCLE_ENRICHMENT classify | 0 checkouts if prefetched | Keep in memory |
| HISTORY_READ row loop / Arabic labels | 0 | Move after release |
| LAZY_ACCESS | not proven | — |
| OTHER | db_ready / identity | Keep, bounded |

## Spanning hold (~2109 ms)

```
checkout (scoped session, pg:23403)
  → last SQL use (timeline/refresh; typical 5 ms)
  → application work: row loop, lifecycle classify, communication timeline,
    refresh token strings, JSON assemble, remaining request lifetime
  → next SQL use: none required
  → checkin at j() / request FINALLY
```

Postgres wait = `ClientRead`. `LOCK_WAIT=0`. The connection was retained while the application composed the merchant payload.

**Design:** release-before-application-work after the bounded DB phase (`compose_messages_after_db_phase`).
