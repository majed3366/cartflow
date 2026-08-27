# Database Network Guard

Module: `services/database_network_guard_v1.py`  
Hook: `extensions.init_database()` calls `assert_database_url_allowed` **before** `create_engine`.

## Classification (no credentials)

| Class | Host pattern | Production default |
|-------|----------------|--------------------|
| `railway_private` | `*.railway.internal` | Allowed |
| `railway_public_proxy` | `*.proxy.rlwy.net`, `*.rlwy.net`, `*.up.railway.app`, `*.railway.app` | Rejected |
| `external_public` | any other remote host | Rejected |
| `localhost` | `localhost`, `127.0.0.1`, `::1` | Allowed (tests / local) |
| `sqlite` | `sqlite:` | Allowed (tests / local) |
| `missing` | empty `DATABASE_URL` | Rejected in production |
| `malformed` | unparseable / no host | Rejected |

Production-like `ENV`: `production`, `prod`, `staging`, `preview`.

## Emergency override

`CARTFLOW_ALLOW_PUBLIC_DATABASE` (default **OFF**). Only `1` / `true` / `yes` / `on` enables public/external hosts. Override is for emergency break-glass only.

## Fail before pool

`init_database()`:

1. In production, missing env `DATABASE_URL` fails immediately (no silent sqlite fallback).
2. `assert_database_url_allowed(url)` runs.
3. Only then is `create_engine` / pool created.

API and Scheduler both go through `init_database()`, so both fail closed.

## Secrets

Raised messages are only:

- `database url rejected: missing`
- `database url rejected: malformed`
- `database url rejected: public_proxy`
- `database url rejected: external`

They never include the URL, hostname, port, username, password, or database name. `redact_url_for_logs()` always returns `[redacted]`.

## Tests

`tests/test_cost_recurrence_prevention_v1.py` — `DatabaseNetworkGuardTests`:

- private Railway hostname accepted
- public proxy rejected
- missing URL rejected
- malformed URL rejected
- emergency override allows public proxy
- secrets never present in the error
