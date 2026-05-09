# CartFlow admin operational dashboard (UI)

## Philosophy

The admin operational surface is a **control center for running the product**, not a full observability platform. It answers, in one calm pass:

- Is the platform healthy enough to trust right now?
- Where are merchants stuck in onboarding or provider readiness?
- Are runtime safeguards flashing warnings we should act on?
- Which stores sit in which **trust bucket**?

It intentionally avoids large charts, infrastructure metrics, and terminal-style noise.

## Operational control principles

1. **Read-only truth** — The UI renders data produced by `build_admin_operational_summary_readonly()` only. No parallel scoring, no new diagnostic pipelines in the UI layer.
2. **Compact signals over volume** — Cards, chips, and short Arabic hint lines; small tables instead of heavy drilldowns.
3. **Business-first language** — Operators care about readiness, risk, and merchant outcomes; not low-level IDs or payloads.
4. **No secrets** — No tokens, env dumps, stack traces, or raw provider responses.

## Simplicity constraints (v1)

- No WebSockets, push notifications, or live polling.
- No AI-generated diagnoses.
- No queue or infra orchestration.
- No redesign of the **merchant** dashboard; this route is **`/admin/*`** only.

## Trust visibility model

- **Platform category** (`platform_admin_category`): coarse state such as healthy, onboarding_blocked, provider_attention_needed, runtime_warning, operational_attention, degraded, sandbox_only — mapped to short Arabic labels in the template.
- **Trust buckets** (`operationally_ready`, `partially_ready`, `degraded`, `unstable`): per-store scores from existing logic; shown as counts and per-row chips.
- **Degradation flags** and **anomaly visibility** mirror existing buffers and counters — summarized as pills and compact lists, not time-series graphs.

## Authentication

- **`CARTFLOW_ADMIN_PASSWORD`** must be set for the dashboard and login form to function (otherwise HTTP 503 on `/admin/operations`).
- After login, a signed **`cartflow_admin_session`** cookie (HMAC with `SECRET_KEY`) gates the page.
- For HTTPS deployments behind TLS, you may set **`CARTFLOW_ADMIN_COOKIE_SECURE=1`** to mark the cookie `Secure`.

## Future extensibility

- Optional drilldown routes per store (still read-only).
- Export of the same JSON as CSV for support.
- Optional gentle auto-refresh (manual or long-interval) without WebSockets.

## Related code

- `routes/admin_operations.py` — HTTP routes and template wiring.
- `services/cartflow_admin_http_auth.py` — password check and cookie signing.
- `services/cartflow_admin_operational_summary.py` — single source of operational aggregates and `store_operational_rows`.
- `templates/admin_operations.html`, `templates/admin_operations_login.html`.
