# CartFlow WhatsApp provider readiness (diagnostics only)

This layer surfaces **Twilio env state**, **production vs mock mode**, and **merchant-safe failure classes** without changing send paths, queues, or recovery scheduling. It complements—but does not replace—the existing observability package (`cartflow_observability_runtime`).

## Philosophy

- **Read-only**: no test sends, no credential exposure, no auto-retry.
- **Separate concerns**: distinguish missing configuration, Twilio policy/sandbox limits, auth/rate issues, and internal recovery skips.
- **Merchant-safe**: Arabic copy maps from stable failure classes, not raw provider payloads.

## Twilio vs Meta

- **Twilio** is the active integration (`services/whatsapp_send.py`). Readiness reads `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` and `PRODUCTION_MODE` + `recovery_uses_real_whatsapp()`.
- **Meta / WhatsApp Cloud API** is a **placeholder** in `get_meta_readiness()` (`META_WHATSAPP_TOKEN` / `WHATSAPP_CLOUD_API_TOKEN`). No Graph send path ships in this repo yet; values exist for future wiring.

## Sandbox and templates

- Sandbox/join issues are classified heuristically from common Twilio error text and codes (e.g. `63016`, “not a participant”, “join”).
- Template / approval style failures map to **`template_not_approved`** when keywords or codes suggest content approval problems—tune mappings as your provider messages evolve.

## Failure classes

| Class | Typical meaning |
|-------|------------------|
| `provider_not_configured` | Missing Twilio env or unknown primary provider |
| `sandbox_recipient_not_joined` | Sandbox / participant issues |
| `template_not_approved` | Template / content gating |
| `provider_auth_failed` | Credentials / permission / invalid sender |
| `provider_rate_limited` | Throttling |
| `provider_unavailable` | Transport / 5xx / timeouts |
| `provider_rejected_message` | Number or message rejected |
| `internal_recovery_skip` | Reserved for non-provider skips (internal copy) |
| `unknown_provider_failure` | No deterministic match |

`classify_provider_failure(error, status)` accepts exception strings or status snippets **already available to callers**—never log secrets.

## Merchant-safe wording

Defined in `services/cartflow_provider_readiness.py` (`merchant_copy_for_failure_class`). For `whatsapp_failed`, the dashboard keeps the core label from `recovery_blocker_display` and may add **`normal_recovery_provider_issue_hint_ar`** with extra provider guidance (e.g. when Twilio env is missing) so recovery-logic wording stays stable.

## Runtime health

`build_runtime_health_snapshot()` adds shallow **`provider_readiness_*`** fields and a **`provider_readiness_summary`** map under `provider_runtime`. Admin summary includes coarse provider readiness flags.

## Structured logs (`[CARTFLOW PROVIDER]`)

Throttled snapshots print when **`CARTFLOW_PROVIDER_READINESS_LOG=1`** or **`CARTFLOW_STRUCTURED_HEALTH_LOG=1`**, with fields:

`provider=`, `ready=`, `failure_type=`, optional `store_slug` / `session_id` / `cart_id` when passed through `log_provider_readiness_snapshot`.

## Future multi-provider abstraction

- Keep **`get_whatsapp_provider_readiness()`** as the facade.
- Add real Meta send behind the same classify + readiness surface when a second provider is implemented.
- Consider persisting last failure class per store in DB if cross-process dashboards need it (not required for this visibility-only layer).
