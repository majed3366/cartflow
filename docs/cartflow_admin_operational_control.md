# CartFlow admin operational control

## Philosophy

The admin layer is an **operational control surface**, not a second product UI. It must stay **read-only**, **deterministic**, and **cheap**: it reuses `build_runtime_health_snapshot()`, `build_admin_runtime_summary()`, `derive_runtime_trust_signals`, onboarding evaluation, duplicate-guard diagnostics, lifecycle/session snippets, and the in-process anomaly ring buffer.

## Trust model

**Per-store** buckets (`operationally_ready`, `partially_ready`, `degraded`, `unstable`) combine:

- Onboarding completion / blocking (`evaluate_onboarding_readiness`)
- Global provider readiness when real WhatsApp is required
- Global lifecycle, duplicate-guard, and session-consistency OK flags from the health snapshot

Scores are capped with transparent rules — no ML or hidden weights.

## Platform category

`platform_admin_category` maps trust signals plus **aggregated** onboarding ratios (scanned stores) into coarse admin enums: healthy, onboarding_blocked, provider_attention_needed, runtime_warning, operational_attention_needed, degraded, sandbox_only.

## Degradation model

`degradation_flags` are boolean pressure signals from:

- Buffered anomaly histograms (duplicate send attempts, provider failures, dashboard conflicts, impossible transitions)
- Lifecycle conflict counters
- Session consistency drift from the snapshot
- Duplicate-guard “blocked recently”
- Share of stores with onboarding blockers

**No auto-remediation** — visibility only.

## Anomaly interpretation

`anomaly_visibility` exposes **symbolic** counts and counters suitable for support. It deliberately avoids stack traces and raw PII. Detail fields in the underlying buffer may exist server-side; this summary focuses on type histograms and guard counters.

## Simplicity constraints

- No realtime streaming, queues, notifications, or remediation bots.
- Store scan is **capped** (`_MAX_STORES_TO_SCORE`) to avoid heavy analytics.
- Phone-coverage gap uses a straightforward SQL existence pattern.

## HTTP surface

`GET /dev/admin-operational-summary` returns JSON when `ENV=development` only — consistent with other internal tooling; **not** linked from the merchant dashboard.

## Future Sentry integration

The summary is shaped as JSON suitable for forwarding to external APM or error tracking later: stable keys, symbolic anomaly types, no secrets. Wire Sentry (or similar) as an additional **consumer** of the same payload without changing recovery code paths.
