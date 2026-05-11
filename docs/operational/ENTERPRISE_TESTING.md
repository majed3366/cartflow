# Enterprise operational testing (CartFlow)

This document describes how to produce the **load**, **AI-discipline**, **Sentry**, and **E2E** evidence retailers expect.  
**Important:** PDFs with *real* 5,000-user curves and production error rates must be generated **on your staging/production-sized stack** (PostgreSQL, app tier, CDN). The repo ships **scripts and thresholds**; numbers are not invented here.

---

## 1) Stress and load (k6)

### Scripts

| Script | Purpose |
|--------|---------|
| `synthetic/k6/smoke.js` | Single-VU readiness (health, cart-event, pages). |
| `synthetic/k6/widget-recovery-stress.js` | Reason capture + `POST /api/cart-event` with optional **full** ramp. |

### Smoke (default)

```bash
k6 run -e CARTFLOW_BASE_URL=https://your-staging.example synthetic/k6/widget-recovery-stress.js
```

### Full profile (tune `FULL_TARGET_VUS`; default ramp targets up to 5,000)

```bash
set LOAD_PROFILE=full
set FULL_TARGET_VUS=5000
k6 run -e CARTFLOW_BASE_URL=https://your-staging.example synthetic/k6/widget-recovery-stress.js --summary-export=synthetic/reports/k6-summary.json
```

### Thresholds (enforced in script)

- `http_req_duration: p(95) < 1000` ms  
- Low `http_req_failed` rate (stricter in `full` profile)

### DB integrity probe

`GET /health?db=1` runs `SELECT 1` on each iteration when enabled (use sparingly at extreme concurrency; pair with DB monitoring).

### HTML → PDF report

1. k6 `handleSummary` writes `synthetic/reports/k6-last-run.html` automatically.  
2. Optional JSON summary: `--summary-export=synthetic/reports/k6-summary.json`  
3. Convert JSON to HTML: `python scripts/reports/k6_summary_to_html.py synthetic/reports/k6-summary.json synthetic/reports/k6-report.html`  
4. Open the HTML in Chrome → **Print → Save as PDF** for the formal load-test PDF.

### Time-series “performance curve”

k6’s built-in HTML summary is a **snapshot**, not a time-series. For curves, export to **InfluxDB / Grafana**, or **k6 Cloud**, and attach those charts to the PDF appendix.

---

## 2) AI discipline and hallucination (Promptfoo + pytest)

### Ground truth in CartFlow

- **Default customer WhatsApp copy** is **rule-first** (`services/recovery_message_strategy.py`, `services/ai_message_builder.py`, templates) — no LLM required for the main recovery path.  
- **Optional Claude path** exists in `main.generate_recovery_message` when `ANTHROPIC_API_KEY` is set — that is the surface to red-team with a **live** model provider in Promptfoo.

### Promptfoo (50 scenarios, stub provider — no API keys)

```bash
cd promptfoo
npm install
python ../scripts/generate_promptfoo_scenarios.py   # refreshes tests.generated.yaml
npx promptfoo eval -c promptfooconfig.yaml --no-cache
npx promptfoo view   # optional UI for pass/fail matrix
```

- **Provider:** `promptfoo/cartflowStubProvider.js` (deterministic Arabic stub).  
- **Assertions:** no `%` / `٪` / `discount` / `خصم` in output (aligns with “no rogue discounts”).  
- **Matrix file:** `promptfoo/tests.generated.yaml` (50 rows).

To test **real** Claude outputs, swap the provider in `promptfoo/promptfooconfig.yaml` for an Anthropic/OpenAI provider and keep the same `tests` + stricter asserts (product names must be substring of `vars.product_name`, etc.).

### Pytest matrix (same 50 logical combinations, Python `build_abandoned_cart_message`)

```bash
python -m pytest tests/operational/test_enterprise_message_discipline_matrix.py -v
```

JUnit / CI matrix export:

```bash
python -m pytest tests/operational/test_enterprise_message_discipline_matrix.py --junitxml=synthetic/reports/discipline-matrix.xml
```

### VIP vs automated customer WhatsApp

**Authoritative integration proof:** `tests/test_vip_manual_handling.py` — VIP abandon → `recovery_scheduled` is **false**, `send_whatsapp` **not** called for the scheduled recovery sequence, merchant alert path mocked.  
The `decision_engine` VIP branch returns a **neutral** template string; scheduling and send gating are validated in those tests, not duplicated inside Promptfoo.

### Recovery-settings discounts

Merchant offer lines are gated by `services/cartflow_product_intelligence.py` + store JSON; extend Promptfoo/pytest with fixtures that load real `cf_merchant_offer_settings_json` samples when you add LLM providers.

---

## 3) Sentry (“mission control”)

### SDK (backend)

- **Dependency:** `sentry-sdk` in `requirements.txt`.  
- **Init:** `services/cartflow_sentry.init_cartflow_sentry(app)` runs at import when `SENTRY_DSN` is set.  
- **Env:**  
  - `SENTRY_DSN` — required to enable.  
  - `SENTRY_ENVIRONMENT` (e.g. `staging`, `production`).  
  - `SENTRY_TRACES_SAMPLE_RATE` (default `0.15`) — performance traces for API routes.  
  - `SENTRY_PROFILES_SAMPLE_RATE` (default `0`) — optional CPU profiles.  
  - `CARTFLOW_RELEASE` — optional release tag.

### WhatsApp failure breadcrumbs

`services/whatsapp_send.py` calls `capture_whatsapp_failure` on Twilio send exceptions (tagged `subsystem=whatsapp`).

### Custom alert rules (configure in Sentry UI)

Recommended issue alerts (examples):

1. **WhatsApp:** filter `subsystem:whatsapp` or message `whatsapp_failure` — notify Ops on spike.  
2. **HTTP 5xx:** alert when `/api/cart-event` or `/webhook/*` error rate exceeds baseline.  
3. **Latency:** use Performance → Transactions for `POST /api/cart-event` p95 regression vs baseline.

### **Widget** storefront performance (browser)

Sentry **browser** SDK is **not** embedded in `static/widget_loader.js` by default (would require DSN in storefront and CSP updates). To track widget load per tenant:

1. Create a **Browser** project in Sentry.  
2. Inject the loader snippet **after** CSP allow-lists `https://browser.sentry-cdn.com` and your ingest host.  
3. Use `tracesSampleRate` low (e.g. `0.05`) on production storefronts.

---

## 4) End-to-end (Playwright)

```bash
# Terminal 1
uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2
set CARTFLOW_BASE_URL=http://127.0.0.1:8000
npx playwright test e2e/cartflow-lifecycle.spec.ts
```

- `e2e/cartflow-synthetic.spec.ts` — broader dashboard smoke.  
- `e2e/cartflow-lifecycle.spec.ts` — **reason POST → cart-event** and JSON contract (`recovery_scheduled`, VIP branch guard).

---

## Honest “final report” checklist for retailers

| Deliverable | How you produce it |
|-------------|-------------------|
| Load PDF with curve + error rate | k6 Cloud/Grafana screenshots + `k6-last-run.html` / `k6-report.html` printed to PDF |
| Promptfoo matrix | `npx promptfoo eval` + **View** export or CI log |
| Sentry dashboards | Sentry UI + saved queries + alert rules |
| E2E proof | Playwright HTML report (`npx playwright show-report`) |

Nothing replaces running these steps against **your** PostgreSQL-backed environment at target scale.
