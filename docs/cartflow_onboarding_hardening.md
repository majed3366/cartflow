# CartFlow onboarding hardening

## Philosophy

Onboarding hardening makes activation **measurable and honest**: merchants see what is configured, what still blocks real traffic, and how sandbox differs from production — without changing recovery logic, widget behavior, or messaging pipelines. Everything is **read-only evaluation** plus **light dashboard copy**; there are no auto-fixes, tutorials, or notifications.

## Readiness model

`services/cartflow_onboarding_readiness.py` evaluates the latest dashboard `Store` row (same selection order as the recovery settings API) and returns:

- **`ready`**: true only when the store can operate in the **current** environment. In sandbox (mock messaging path), Twilio is not required. In production (`recovery_uses_real_whatsapp()` true), both credential configuration and **provider readiness** must pass before the system is considered operationally ready to send.
- **`completion_percent`**: weighted score from dashboard presence, connection, recovery enabled, widget enabled, messaging path (sandbox **or** real provider path), and first-send milestones — not gamification; a coarse progress hint only.
- **`blocking_steps`**: symbolic codes (e.g. `widget_not_installed`, `whatsapp_not_connected`) mapped to **merchant-safe** Arabic titles and actions.
- **`milestones`**: first cart, first recovery log, first sent message, first reply signal, first recovered cart — derived from existing tables only.

## Operational activation requirements

- **Store row** must exist (`dashboard_not_initialized` otherwise).
- **Connection**: access token or Zid store id present (lenient signal that setup progressed).
- **Recovery**: `is_active` and `recovery_attempts >= 1`.
- **Widget**: `cartflow_widget_enabled` true (treated as “widget path enabled” for onboarding).
- **Production messaging**: Twilio env completeness and `get_whatsapp_provider_readiness()["ready"]` — consumed read-only; the provider module is not modified here.
- **Customer phone** (production only): if carts exist but none carry a usable phone and the merchant number is unset, `no_customer_phone_source` blocks readiness to avoid a false “ready to send” state.

## Sandbox limitations

When `recovery_uses_real_whatsapp()` is false, the stack uses the mock/sandbox messaging path. The evaluation adds a **sandbox notice** (Arabic) so merchants do not assume production delivery. Sandbox can still be `ready` for configuration and flow verification without Twilio.

## Onboarding blockers

Human-readable metadata lives in `BLOCKER_COPY` (titles, explanations, actions). Internal codes stay in JSON/snapshots; surfaced strings avoid vendor jargon where possible.

## Milestone model

Milestones are **diagnostics only** (no badges or scoring games). They help merchants and support see whether first cart, first log, first send, reply, or recovery events have occurred for the store slug / `store_id`.

## Merchant trust principles

- **No false “ready”** in production without provider readiness and messaging configuration.
- **Configured ≠ ready**: explicit separation in the readiness flags and health snapshot.
- **Dashboard strip** on `/dashboard/normal-carts`: one compact section (`cf-onboarding-strip`) with status, next step, optional sandbox note, and approximate completion — no full UI redesign.

## Runtime health and admin summary

- `build_runtime_health_snapshot()` includes `onboarding_runtime` and mirrors `onboarding_completion_percent` / `onboarding_ready_flag` beside `provider_readiness_summary` for quick correlation (read-only fields only).
- `derive_runtime_trust_signals()` treats incomplete onboarding as a **warning** contributor.
- `build_admin_runtime_summary()` exposes `onboarding` and extended `trust` onboarding fields.

## Tests

See `tests/test_cartflow_onboarding_readiness.py` and `tests/test_cartflow_runtime_health.py` for regression coverage.
