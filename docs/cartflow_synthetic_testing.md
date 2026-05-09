# CartFlow synthetic operational testing

This document describes the **testing-only** layer used to catch regressions in real HTTP/browser flows without changing application behavior. All checks use **demo store data** and **synthetic sessions**.

## What is covered

### Playwright (browser)

- **Demo widget bootstrap** — `widget_loader.js` runs; `window.CARTFLOW_RUNTIME_STATUS.return_tracker_loaded` becomes true.
- **Add to cart** — demo catalog (`/demo/store` — product listing where the demo widget arm fallback applies) adds a line item to the UI cart.
- **Reason selection** — after the bubble appears, the flow confirms **نعم** on the first prompt, then selects **الضمان** so the browser performs a real `POST /api/cart-recovery/reason`.
- **Recovery event** — same tab posts `cart_abandoned` to `/api/cart-event` with `cf_test_phone` (test-only override), asserting HTTP 200 and `ok: true`.
- **Normal carts dashboard** — `/dashboard/normal-carts` renders and shows at least one operational surface (onboarding strip, merchant clarity banner, recovery alerts list, or empty-state copy).
- **Admin operations login** — `/admin/operations/login` returns the expected Arabic shell (`مركز التشغيل`).
- **Return tracker asset** — `GET /static/cartflow_return_tracker.js` succeeds (readiness for the return-tracker bundle).
- **No uncaught page errors from CartFlow** — collects `pageerror` events. Known benign third-party flakes (for example Tailwind CDN `tailwind is not defined` on some dashboard/admin loads) are filtered so the suite focuses on app regressions.

### k6 (HTTP smoke)

Very light checks (single VU, few iterations) against:

| Endpoint | Method |
|----------|--------|
| `/health` | GET |
| `/dashboard/normal-carts` | GET |
| `/api/recovery-settings` | GET |
| `/api/cart-event` | POST (minimal `cart_abandoned` body, `demo` store, synthetic `session_id`) |
| `/admin/operations/login` | GET |

This is **readiness / smoke**, not capacity testing.

## Prerequisites

- **Application** running locally or in a staging environment (same origin for cookie/API and static assets).
- **Node.js 18+** for Playwright.
- **k6** binary for the HTTP suite ([installation](https://k6.io/docs/getting-started/installation/)).

## How to run Playwright

From the repository root:

```bash
npm install
npx playwright install chromium
set CARTFLOW_BASE_URL=http://127.0.0.1:8000
npm run test:e2e
```

On macOS/Linux:

```bash
export CARTFLOW_BASE_URL=http://127.0.0.1:8000
npm run test:e2e
```

Optional UI mode:

```bash
npm run test:e2e:ui
```

Environment:

- **`CARTFLOW_BASE_URL`** — origin only (no trailing path), e.g. `http://127.0.0.1:8000`. Defaults to `http://127.0.0.1:8000` if unset.

The demo URL appends `cf_test_phone=9665444555666` (same pattern as Python tests) so customer routing stays in **test mode** where configured.

## How to run k6

From the repository root (adjust the base URL as needed):

```bash
k6 run -e CARTFLOW_BASE_URL=http://127.0.0.1:8000 synthetic/k6/smoke.js
```

`CARTFLOW_BASE_URL` defaults to `http://127.0.0.1:8000` inside the script if not set.

## Limitations

- **Environment-dependent** — requires a reachable server and database migration state consistent with your branch; failures may reflect **data or config** (e.g. missing `Store` row) rather than a pure frontend bug.
- **WhatsApp** — browser flows rely on demo/test phone hooks and server-side gating; these tests **do not** assert real message delivery and are not a substitute for provider monitoring.
- **Admin password** — the Playwright suite only loads the **login page**. It does not submit credentials (no secrets in the repo). k6 only performs **GET** on `/admin/operations/login`.
- **Timing** — the widget waits for **idle** behavior; Playwright uses long timeouts for the bubble/FAB to reduce flakes on slower machines.
- **cart-event POST in k6** — uses a disposable `session_id` and minimal cart lines; scheduling/skip outcomes vary with backend state. The smoke test only asserts **HTTP 200** and connectivity.

## Future CI plan

1. Add a workflow job that starts the app (or targets a fixed preview URL), runs `npm ci`, `npx playwright install --with-deps chromium`, then `npm run test:e2e`.
2. Install k6 in the runner image and execute `synthetic/k6/smoke.js` against the same base URL.
3. Upload Playwright HTML report and k6 summary as artifacts.
4. Gate merges on **smoke** first; add heavier scenarios (parallel VUs, multi-store) only after stable baselines.
