# CartFlow production readiness

This document describes how to validate configuration and runtime safety before serving production traffic. It complements the machine-readable report from `build_cartflow_production_readiness_report()` in `services/cartflow_production_readiness.py` and the development-only HTTP endpoint `GET /dev/production-readiness` (requires `ENV=development`).

## Production checklist

1. Set a strong **`SECRET_KEY`** (never use the repository default string).
2. Set **`DATABASE_URL`** to a durable Postgres (or equivalent) URL; do not rely on the SQLite fallback on Railway.
3. If you intend real WhatsApp sends, set **`PRODUCTION_MODE`** to a truthy value (`1`, `true`, `yes`, `on`) and configure **Twilio** (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`). Confirm Twilio sandbox, sender, and templates per your account.
4. Decide **`ENV`**: use `ENV=development` **only** for local tooling. Leaving `ENV` unset means **non-development** middleware rules apply (`/dev/*` mostly blocked).
5. Review **unsafe states** below (`GET /debug/db`, allowlisted `/dev/*` routes, `/admin/init-db`).
6. After deploy, use runtime health and onboarding diagnostics (existing dashboards and admin operational summary) to confirm provider and store readiness.

## Required environment variables

| Variable | Role |
|----------|------|
| `SECRET_KEY` | Signing / session secret for the app; must not be left at the code default in production. |
| `DATABASE_URL` | Primary SQL database; if unset, the app falls back to a temporary SQLite path (unsafe for multi-instance production). |
| `TWILIO_ACCOUNT_SID` | Twilio account identifier for WhatsApp. |
| `TWILIO_AUTH_TOKEN` | Twilio auth secret (**never log**). |
| `TWILIO_WHATSAPP_FROM` | Approved WhatsApp sender (e.g. `whatsapp:+...`). |
| `ENV` | If set to `development`, full `/dev/*` tooling is enabled; otherwise most `/dev` routes return 404 at the edge. |
| `PRODUCTION_MODE` | When truthy, recovery may use real WhatsApp when Twilio is fully configured (see `recovery_uses_real_whatsapp()`). |

### Optional URLs / OAuth (presence-only in reports)

These are used elsewhere in the codebase for links and Zid integration:

- `CARTFLOW_PUBLIC_BASE_URL`, `PUBLIC_BASE_URL`, `OAUTH_REDIRECT_URI`
- `ZID_CLIENT_ID`, `ZID_CLIENT_SECRET`, `ZID_WEBHOOK_SECRET`

There is no separate CORS “allowed origins” env in this repo; embed and dashboard flows rely on existing CSP / frame usage.

## Unsafe states

- **`SECRET_KEY`** missing or equal to `dev-only-change-in-production` while **`PRODUCTION_MODE`** is on → treat as **blocking** until rotated.
- **`DATABASE_URL`** unset in production → SQLite fallback may lose data or diverge across instances.
- **`GET /debug/db`** is outside the `/dev` prefix → it is **not** hidden by `no_dev_in_production` and returns a short DB URL prefix (information leak).
- **`GET /admin/init-db?key=...`** uses a **fixed default key** (`dev-init`) in source → anyone who knows the key can hit it; protect with network rules or change the key in `routes/ops.py`.
- **Allowlisted `/dev/*` paths** when `ENV` is not `development` remain reachable (no session auth): see `main._DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT` (includes read-only `GET /dev/widget-runtime-config-verify` for storefront widget config checks). **`/dev/widget-test`** intentionally stays **blocked** unless `ENV=development` — it loads **legacy **`cartflow_widget.js`** directly** as a QA harness only (not `/demo/store` / not V2).
- **`WA_RECOVERY_SEND_TRACE`**: if enabled in production, ensure logs do not print message bodies, Twilio tokens, or customer PII.

## Railway deployment notes

- Config is defined in `railway.toml`: Docker build, start command `python -m uvicorn main:app --host 0.0.0.0 --port 8000`.
- Set **`PORT`** if your platform injects it; the sample command uses `8000` explicitly in Railway’s `startCommand`.
- Provide **`DATABASE_URL`** from Railway Postgres (or external). Railway may supply `postgres://`; the app normalizes to `postgresql://`.
- Set **`SECRET_KEY`**, **`PRODUCTION_MODE`**, and Twilio variables in the service environment. Do not commit `.env`.

## Dev route policy

- Middleware `no_dev_in_production` returns **404** for `/dev` and `/dev/*` when **`ENV` is not `development`**, **except** for the allowlisted paths copied in `services/cartflow_production_readiness.py` (keep in sync with `main.py`). **`GET /dev/widget-test`** / **`GET /dev/widget-test/cart`** load **legacy **`cartflow_widget.js`** inline** — they are **not** allowlisted so they disappear in deployed non-dev environments (`404`). Use **`/demo/store`** for layered **V2** behaviour.
- Some `/dev/...` handlers also return 404 if `ENV` is not `development` (defense in depth); allowlisted paths may still run without that check — treat them as **operator-only** surface.

## Admin password / init-db warning

- There is no classic “admin user password” in this service; the closest operational risk is **`/admin/init-db`** gated only by query param `key` matching the built-in default. See **Unsafe states**.

## WhatsApp provider readiness

- Readiness is summarized via `get_whatsapp_provider_readiness()` (Twilio-first). Production real-send expectations come from **`PRODUCTION_MODE`** plus full Twilio env vars (`whatsapp_send.recovery_uses_real_whatsapp()`).
- A **ready** provider means credentials are present and the real-send gate is satisfied; template approval and sandbox participation are operational concerns surfaced in provider failure classes — resolve in Twilio / WhatsApp Business accounts.

## Known limitations before launch

- No background worker/queue hardening is part of this readiness layer (in-process queue behavior unchanged).
- Readiness checks are **read-only** and **best-effort**; they do not replace monitoring, backups, or penetration testing.
- **`production_ready` in JSON** is conservative: for example, `/debug/db` exposure is treated as a **blocking** issue whenever `PRODUCTION_MODE` is on, until you remove or protect that route at the edge.

## Readiness output rules

Reports and tests guarantee:

- Only **`configured: true/false`** style fields and **missing key names** — **never** secret values.
- A self-check fails the report if a long secret from the environment appears verbatim in the serialized payload (should not happen in normal operation).
