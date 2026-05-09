# CartFlow runtime health visibility

## Philosophy

Runtime health answers “**can this deployment do its job safely right now?**” using **read-only** checks and **symbolic** anomalies — without altering WhatsApp delivery, scheduling, merge rules, or dashboard UX.

- **No mutations** in health helpers (no fixes, no retries).
- **No secrets** in snapshots or admin summaries (Twilio tokens are never emitted).
- **Logs are opt-in** via `CARTFLOW_STRUCTURED_HEALTH_LOG=1` to avoid noise in default production.
- **Foundation only** — no workers, queues, websockets, or admin UI in this layer.

## Module: `services/cartflow_runtime_health.py`

### Health snapshot

`build_runtime_health_snapshot()` returns nested sections:

- **recovery_runtime** — DB/session viability, duplicate-prevention flag from the flat observability helper.
- **whatsapp_runtime** — high-level WhatsApp/Twilio readiness (env-level visibility only).
- **identity_runtime** — store row resolvable for dashboard scope; `identity_conflict_detected` reflects buffered `identity_merge_blocked`-class anomalies (in-process buffer).
- **dashboard_runtime** — template/runtime process assumed active; payload OK placeholder for future checks.
- **duplicate_protection_runtime** — logical duplicate gate (aligned with observability flag).
- **behavioral_runtime** — merge pipeline “ok” placeholder; DB connectivity mirrors recovery.
- **provider_runtime** — Twilio env presence, recent `whatsapp_failed` row count (24h, read-only query).

The snapshot **reuses** `runtime_health_snapshot_readonly()` from the existing observability package (import-only; that package is not modified by this task).

### Anomaly aggregation

- **Symbols**: `duplicate_send_attempt`, `send_after_return`, `send_after_conversion`, `identity_merge_blocked`, `missing_customer_phone`, `provider_send_failure`, `impossible_state_transition`, `dashboard_payload_conflict`.
- **Pure helpers**: `aggregate_anomaly_symbols`, `map_conflict_codes_to_anomalies` (maps internal dashboard conflict codes to symbols).
- **In-process buffer**: `record_runtime_anomaly` / `drain_recent_anomalies` / `recent_anomaly_type_counts` — bounded deque for **future** admin endpoints; nothing in core recovery paths is required to call it.

### Structured logging

When `CARTFLOW_STRUCTURED_HEALTH_LOG` is truthy (`1`, `true`, `yes`, `on`):

- `[CARTFLOW HEALTH]`
- `[CARTFLOW ANOMALY]`
- `[CARTFLOW PROVIDER]`

`record_runtime_anomaly` may emit `[CARTFLOW ANOMALY]` in that mode only.

### Admin-readiness payload

`build_admin_runtime_summary()` returns a dict suitable for a future internal route, e.g.:

- `recovery_runtime_ok`, `identity_runtime_ok`, `provider_runtime_ok`, `dashboard_runtime_ok`
- `recent_anomaly_count`, `recent_anomaly_types_preview`
- `trust`: `runtime_stable`, `runtime_degraded`, `runtime_warning`, `runtime_trust_label_ar` (merchant-safe Arabic)

### Trust signals

`derive_runtime_trust_signals()` derives tri-state flags from snapshot + buffered anomaly count. Copy avoids alarmist wording (see Arabic label in code).

### Provider stability (visibility)

- Env: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` — **presence only**.
- Counter: `CartRecoveryLog.status == whatsapp_failed` since last 24h (or `-1` if query fails).

## Future: Sentry / Admin

- **Sentry**: tag events with anomaly `type=` and health section booleans; avoid PII in extras.
- **Admin dashboard**: mount `build_admin_runtime_summary()` behind auth; optionally expose `build_runtime_health_snapshot()` for drill-down.

## Limitations

- Buffered anomalies are **per process** and capped (~200); restart clears them.
- Health is **best-effort**; false negatives/positives are possible under partial outages.
- No automatic alerting — operators opt into logs or future admin routes.
