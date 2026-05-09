# CartFlow runtime observability

## Philosophy

Operational observability explains **what the runtime did or skipped** in a way that is:

- **Traceable** — grep-friendly structured lines with stable prefixes.
- **Explainable** — lifecycle tokens map to merchant-safe dashboard hints, not raw enums.
- **Merchant-safe** — no stack traces, secrets, or internal IDs in dashboard payloads.
- **Admin-debuggable** — engineers correlate `session_id` / `cart_id` / `store_slug` in logs without changing recovery outcomes.

This layer is **diagnostics only**: it does not change WhatsApp sending, scheduling, VIP flows, identity merge rules, or blocker key mapping.

## Structured log prefixes (new)

New observability uses consistent banners:

| Prefix | Typical use |
|--------|----------------|
| `[CARTFLOW RECOVERY]` | Recovery lifecycle traces (`trace_recovery_lifecycle`). |
| `[CARTFLOW DIAGNOSTIC]` | Heuristic conflict detection, structured field dumps. |
| `[CARTFLOW STATE]` | Reserved for future state-transition breadcrumbs. |
| `[CARTFLOW WHATSAPP]` | Reserved (existing `[WA SEND PATH]` traces remain). |
| `[CARTFLOW IDENTITY]` | Category constant for routing; production drift still uses existing `[CARTFLOW IDENTITY WARNING]`. |

Legacy `print` / `log` lines are **not removed**; this is additive.

## Diagnostic categories

Module constants (for metrics / log routers): `identity`, `recovery`, `whatsapp`, `scheduling`, `duplicate_protection`, `behavioral_merge`, `dashboard_runtime`, `provider`, `frontend_runtime`, `state_transition`.

## Recovery lifecycle (tracing)

`trace_recovery_lifecycle` and `trace_recovery_lifecycle_from_log_status` emit **`[CARTFLOW RECOVERY]`** lines with tokens such as:

`recovery_created`, `waiting_delay`, `skipped_duplicate`, `skipped_missing_phone`, `skipped_returned`, `skipped_converted`, `queued`, `send_started` (reserved), `send_success`, `send_failed`, `reply_received`, `returned_to_site`, `merge_blocked`, `trust_warning` (reserved), `automation_gated`.

Lifecycle hooks are wired where persistence is already happening (e.g. after `CartRecoveryLog` commit; behavioral return-to-site merge success/failure). **No scheduling math is altered.**

## Runtime health snapshot

`runtime_health_snapshot_readonly()` returns read-only booleans, e.g. `whatsapp_provider_ready`, `recovery_runtime_active`, `identity_resolution_ok`, `duplicate_prevention_active`, `dashboard_runtime_active`.

Exposed on **`GET /dashboard/normal-carts`** as template context key `cartflow_runtime_health` (templates may ignore it). No new public API route.

## Merchant-safe visibility

Blocker payloads from `recovery_blocker_display` gain an additive field **`operational_hint_ar`**: short operational truth (e.g. «تم منع محاولة مكررة», «بانتظار رقم العميل») without replacing stable `label_ar` / keys.

Normal recovery dashboard JSON includes **`normal_recovery_operational_hint_ar`** when a blocker is present.

## Operational truth principles

1. Prefer **plain Arabic operational explanations** over English status codes in merchant-facing hints.
2. **Never** surface provider tokens, Twilio SIDs, or stack traces in dashboard payloads.
3. Conflict heuristics log **symbolic codes** only (`recovered_cart_with_send_success_log`, etc.).
4. Observability must **not** introduce duplicate sends or bypass existing guards.

## Runtime conflict diagnostics

`detect_recovery_runtime_conflicts` + `log_runtime_conflicts` run during normal-recovery dashboard payload build. They **log only**; there is no auto-repair. Examples:

- Latest log shows successful send while identity trust failed.
- Anti-spam skip without behavioral return flag (possible drift).

Heuristics may false-positive on ordering edge cases; treat logs as signals, not ground truth.

## Known limitations

- Lifecycle coverage is **incremental**; not every branch emits a trace yet.
- `send_started` is reserved — actual send entrypoints already have dev-gated WA traces.
- **Sentry / OpenTelemetry**: structured single-line logs are suitable for future ingestion; no SDK is bundled here.

## Future: Sentry readiness

- Use `emit_structured_runtime_line` or grep on `[CARTFLOW RECOVERY]` / `[CARTFLOW DIAGNOSTIC]`.
- Tag events with `category=` and conflict `code=` for faceted search.
- Avoid shipping full message bodies or phone numbers in breadcrumb metadata.
