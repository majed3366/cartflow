# CartFlow session consistency

## Philosophy

CartFlow ties together the merchant dashboard, recovery worker/runtime, behavioral flags on abandoned carts, and provider outcomes. Each layer updates state asynchronously. Session consistency work is **diagnostic and additive**: it detects drift between those views, logs structured signals, and surfaces **merchant-safe** hints on the normal-recovery dashboard when a conflict is detected. It does **not** auto-repair persisted state, change recovery timing, alter WhatsApp sending, or replace existing lifecycle, duplicate, or provider-readiness guards.

## Canonical runtime ownership

The **database-backed abandoned cart** (including `cf_behavioral` inside `raw_payload`), recovery logs, and lifecycle reconciliation on the server remain the sources of truth for whether a cart is still recoverable. The dashboard payload is **derived** from those sources plus reconcilers; the session consistency layer checks that the **assembled** normal-recovery payload is **internally coherent** (phase, latest log status, behavioral snapshot) and that behavioral merges did not **attempt** to weaken stronger terminal engagement before lifecycle pruning.

## Stale state handling

- **Behavioral merges**: Before `prune_behavioral_merge_fields` runs, raw incoming fields are compared to the prior behavioral dict. Attempts to flip strong engagement flags from true to false or to downgrade `lifecycle_hint` from a strong state are recorded as `stale_behavioral_merge` under `[CARTFLOW CONSISTENCY]` (throttled). Counters and recent-event marks feed runtime health only.
- **Dashboard payload**: After the normal-recovery payload is built, additive fields such as `normal_recovery_session_runtime_consistent` and optional `normal_recovery_session_consistency_codes` reflect heuristic checks. If issues exist, a short Arabic **operational** hint is added via `normal_recovery_session_trust_hint_ar` (no internal jargon).
- **Client/widget**: `note_frontend_stale_state_intent` is available for future or internal callers to log `frontend_state_stale` under `[CARTFLOW SESSION]` without changing widget UX in this layer.

## Behavioral precedence

Existing lifecycle pruning continues to enforce precedence on persisted merges. The consistency module only **observes** raw merge intent so operators can correlate “stale client/browser payload” with protected server state.

## Dashboard truth guarantees

The dashboard continues to use the same phase and blocker logic as before. Session consistency **adds**:

- `normal_recovery_session_runtime_consistent` (boolean)
- `normal_recovery_session_consistency_codes` (when inconsistent)
- `normal_recovery_session_trust_hint_ar` (only when inconsistent)

It does **not** change blocker keys, identity trust strings, or provider readiness overlays.

## Async timing considerations

Delayed recovery, webhooks, and browser events can arrive out of order. Diagnostics use **heuristics** (for example, converted log vs phase) and **recent windows** (default 600s monotonic) so runtime health trust reflects **recent** drift without rewriting history. Cumulative counters remain for longer-term inspection.

## Runtime health and admin summary

`build_runtime_health_snapshot()` includes `session_consistency_runtime` and augments `behavioral_runtime` with `behavioral_state_consistent` and session counters. `derive_runtime_trust_signals()` treats recent session drift and stale signals as **warning** contributors. `build_admin_runtime_summary()` exposes a `session_consistency` block and extended `trust` fields.

## Logging

Structured lines use:

- `[CARTFLOW SESSION]` — client/session-oriented events (e.g. `frontend_state_stale`)
- `[CARTFLOW CONSISTENCY]` — merge and cross-runtime checks (e.g. `stale_behavioral_merge`, `dashboard_runtime_mismatch`, `provider_callback_stale`)

Enable with `CARTFLOW_SESSION_CONSISTENCY_LOG=1` and/or `CARTFLOW_STRUCTURED_HEALTH_LOG=1`. Emission is throttled per `(type, session, cart)` fingerprint to limit noise.

## Known limitations

- Heuristics may false-positive on rare legitimate race timings; signals are for investigation and trust blending, not automatic rollback.
- Recent-window trust is **process-local**; multi-worker deployments see per-process marks only.
- The module does not introduce queues or workers; ordering is still governed by existing runtime behavior.

## Future queue/worker implications

If recovery execution is moved to dedicated workers, the same diagnostics should run at **payload assembly** and **merge** boundaries in that process, or centralized counters would need shared storage. Until then, in-process counters and logs remain deterministic and cheap.

## Merchant-safe wording examples

Strings used for dashboard hints when drift is detected are non-technical, for example:

- Ignoring stale display state in favor of the cart
- Preventing a conflicting cart state from surfacing
- Noting a minor display mismatch while showing the latest trusted context

Exact copy lives in `services/cartflow_session_consistency.py`.
