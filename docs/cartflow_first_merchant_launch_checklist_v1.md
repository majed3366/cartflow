# CartFlow — First Merchant Launch Checklist v1

**Date (UTC):** 2026-05-19  
**Type:** Operational checklist only — **no** runtime, widget, WhatsApp, dashboard, or queue changes.  
**Commit message:** `docs: add first merchant launch checklist v1`

**Question this answers:** *Can we onboard and operate the first real merchant safely?*

**Overall pilot verdict:** **PARTIAL — ready for a founder-guided sandbox pilot; not ready for unattended production go-live.**

Related audits: `docs/cartflow_first_production_merchant_readiness_v1.md`, `docs/cartflow_first_merchant_journey_audit_v1.md`, `docs/cartflow_queue_worker_maturity_audit_v1.md`, `docs/cartflow_queue_worker_runtime_rules.md`, `docs/cartflow_purchase_truth_completion_v2.md`.

---

## When the first merchant is “ready”

| Scope | Ready? | Definition |
|-------|--------|------------|
| **Guided sandbox pilot (day 1)** | **YES, with founder on call** | Account, store slug, test widget path, abandon → schedule → **mock or sandbox** send, cart visible in dashboard, ops can read recovery-health + admin diagnostics. |
| **Limited production (week 1)** | **PARTIAL** | Real WhatsApp + approved templates + callbacks + single scheduler owner + purchase stop verified on a real order path. |
| **Unattended self-serve production** | **NO** | Provider env, template approval, theme embed, and KPI interpretation still need humans. |

**Stop and do not go live** if any **P0 blocker** below is unresolved for the chosen scope.

---

## Part 1 — Launch checklist (10 items)

| # | Item | What “good” looks like | How to verify (ops / founder) |
|---|------|------------------------|-------------------------------|
| 1 | **Signup works** | Merchant creates account at `/signup`; `MerchantUser` + `Store` row exist. | `POST /signup` succeeds; login works; `[MERCHANT SIGNUP]` in logs if debugging. |
| 2 | **Store connection works** | Zid OAuth completes when platform env is set; `Store.access_token` populated. | `/dashboard#settings` or `GET /api/merchant/store-connection` shows connected; not “ميزة الربط قيد الإعداد”. |
| 3 | **Widget test path works** | Merchant can exercise widget without editing live theme first. | `GET /dashboard/test-widget` → `/demo/store?store_slug={merchant_slug}`; abandon + reason on **their** slug. |
| 4 | **WhatsApp setup status clear** | Dashboard shows number, recovery toggle, gaps — merchant knows **intent** vs **platform** wiring. | `#whatsapp` + readiness card; ops knows real send = `PRODUCTION_MODE` + `TWILIO_*` (not in-app connect). |
| 5 | **Template / 24h readiness clear** | Local `reason_templates_json` filled; ops knows Meta/Twilio approval is **outside** CartFlow. | Templates non-empty (avoid `skipped_reason_template_disabled`); `docs/whatsapp_production_reality_v1.md` for 24h window. |
| 6 | **Recovery health healthy** | Scheduler owner correct; no stuck `running`; pending due explainable. | `GET /dev/recovery-health` — `scheduler_owner_mode`, `resume_on_startup_enabled`, `last_resume`, `pending_due`, `stuck_running`. |
| 7 | **Admin diagnostics available** | Support can answer What/Why/Action without reading raw logs only. | `GET /admin/support-diagnostics` or `/admin/support-diagnostics/ui` for session/store/recovery_key. |
| 8 | **First sandbox send works** | Abandon → wait `recovery_delay` (default 2 min) → `mock_sent` or sandbox send. | Cart row + milestone `first_whatsapp_sent`; log status not `whatsapp_failed` for happy path. |
| 9 | **First production send requirements known** | Written checklist for ops: Twilio, callbacks, templates, `PRODUCTION_MODE`, public URL. | Team can list env vars and approval lead time **before** promising real customer messages. |
| 10 | **Purchase stop / lifecycle closure verified** | After purchase truth ingest, recovery stops; durable closure record when applicable. | `[PURCHASE TRUTH INGESTED]` / `GET /dev/purchase-truth-status`; schedule cancelled; `lifecycle_closure_records` for terminal paths. |

---

## Part 2 — Readiness status (per item)

| # | Item | Status | Reason | Action |
|---|------|--------|--------|--------|
| 1 | Signup works | **READY** | `/signup` creates user + store; landing CTAs point to `/signup` (`cartflow_landing.html`). Mobile signup hardening shipped. | Send merchant **`https://{host}/signup`**; confirm `RESEND_*` if password reset needed in prod. |
| 2 | Store connection works | **PARTIAL** | Zid OAuth path exists (`merchant_store_connection_v1`, `/auth/callback`) but requires **`ZID_CLIENT_ID`**, **`ZID_CLIENT_SECRET`**, registered **`OAUTH_REDIRECT_URI`**. Widget-only abandon works with signup slug **without** OAuth. | Pre-flight OAuth app per environment; founder walks OAuth once; treat onboarding “store” step as **OAuth complete**, not slug-only. |
| 3 | Widget test path works | **PARTIAL** | Merchant-scoped test URL exists (`/dashboard/test-widget` → demo store with `store_slug`). Live Zid theme embed still merchant-owned (30–90 min skill variance). | Day 1: use **test-widget** path only; defer production theme until sandbox proof done. |
| 4 | WhatsApp setup status clear | **PARTIAL** | Dashboard captures number + flags; **does not** connect Twilio/WABA in UI. Readiness cards explain gaps in Arabic. | Founder script: “dashboard = your settings; CartFlow ops = provider wires”; show mock vs real in logs. |
| 5 | Template / 24h readiness clear | **PARTIAL** | Local JSON templates + reason tags work; **no** in-app Meta template ID sync; production needs **approved** provider templates (24h–7d). | Before prod: fill templates in dashboard; ops submits templates to Meta/Twilio; document approval status offline. |
| 6 | Recovery health healthy | **READY** | `GET /dev/recovery-health` (production-allowed) with scheduler ownership, stuck running, pending due, failed explanation. P0 guardrails: one scheduler owner, API replicas `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0`. | On deploy: one process with resume enabled; check health after restart; fix stuck `running` before onboarding merchant traffic. |
| 7 | Admin diagnostics available | **READY** | `admin_support_diagnostics_v1` — read-only What/Why/Action for support. | Bookmark admin UI; use `recovery_key` / `session_id` from merchant report. |
| 8 | First sandbox send works | **PARTIAL** | Mock path reliable when `PRODUCTION_MODE` off; real sandbox needs Twilio sandbox **join** on test handset; 2 min delay confuses merchants. | Pilot day 1: **mock only** unless sandbox pre-joined; coach wait + phone + reason capture. |
| 9 | First production send requirements known | **PARTIAL** | Requirements documented across readiness audits; not a single in-app merchant wizard. | Ops prints short env checklist (Twilio, callback URL, `PRODUCTION_MODE`, templates approved); founder does not promise prod send day 1. |
| 10 | Purchase stop / lifecycle closure verified | **PARTIAL** | Purchase truth v2 + lifecycle closure records v1 + Zid webhook ingest path exist; **“recovered” KPI** still needs real order/conversion. | Verify one test: `POST /api/conversion` or dev purchase-truth test + confirm schedule stop; educate merchant: **sent ≠ recovered**. |

### Consolidated blockers (P0 for pilot)

| ID | Blocker | Affects items |
|----|---------|---------------|
| B1 | Zid OAuth env missing or redirect mismatch | 2 |
| B2 | Merchant uses `/demo/store` without `store_slug` (wrong store) | 3, 8 |
| B3 | Empty `reason_templates_json` at signup | 5, 8 |
| B4 | `PRODUCTION_MODE` + Twilio expected on day 1 without ops prep | 4, 8, 9 |
| B5 | Multi-worker deploy without scheduler ownership discipline | 6, 8 |
| B6 | Widget not on merchant test path and no abandon event | 3, 8 |
| B7 | Interpreting “recovered” KPI before purchase truth | 10 |

---

## Part 3 — Founder-assisted playbook (day one)

**Audience:** First guided merchant + one CartFlow founder/ops on call.  
**Target outcome:** Sandbox proof (definition **A** in `cartflow_first_production_merchant_readiness_v1.md`) — not full production WhatsApp.

### Exact order (do not reorder for day 1)

| Step | Founder / merchant action | Success signal | Typical time |
|------|---------------------------|----------------|--------------|
| **1. Create account** | Send `/signup` link; merchant completes form; login. | Dashboard loads; store slug visible in settings. | 10–15 min |
| **2. Connect store** | If Zid pilot: complete OAuth from `#settings`. If widget-only day 1: confirm slug only, note OAuth deferred. | `access_token` present **or** explicit “widget-only day 1” note in runbook. | 15–45 min |
| **3. Open test widget** | Merchant opens **`/dashboard/test-widget`** (logged in); abandon cart with **test phone**. | `first_cart_detected` or cart row in `#carts`. | 15–20 min |
| **4. Run recovery test** | Capture reason in widget; wait **full** `recovery_delay` (default 2 min); refresh carts. | `first_whatsapp_sent` or log `mock_sent` / sandbox sent; schedule not stuck in `running`. | 15 min + wait |
| **5. Check admin diagnostics** | Ops: `recovery_key` / support diagnostics + `GET /dev/recovery-health`. | Health not `warning` for stuck running; scheduler owner as expected. | 10 min |
| **6. Prepare WhatsApp production** | **Offline:** Twilio account, template submission, callback URL, env doc — **not** during live merchant call unless pre-staged. | Written prod checklist signed off by ops. | 0 min on call; hours–days async |
| **7. Go live limited** | Embed widget on **one** low-traffic page or staging theme; keep `PRODUCTION_MODE` off until step 6 done. | Real abandon on live snippet with founder monitoring first 24h. | After sandbox proof |

**Estimated founder time on call:** **2–4 hours** for steps 1–5.  
**Estimated calendar time to limited production:** **1–3+ days** after step 6.

---

## Part 4 — Operational rules

### What not to do (first merchant)

| Do not | Why |
|--------|-----|
| Promise **production WhatsApp** on day 1 | Templates, Twilio, callbacks, and `PRODUCTION_MODE` are ops-gated (items 4, 9). |
| Skip **`/dashboard/test-widget`** and only use `/demo/store` | Default demo store uses `data-store="demo"` — merchant dashboard stays empty (blocker B2). |
| Scale API replicas with **all** workers running resume scan | Duplicate startup resume risk — set `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0` on replicas (`cartflow_queue_worker_runtime_rules.md`). |
| Treat **“تم إرسال رسالة”** as **“تم الاستردادها”** | KPI recovered follows purchase truth, not send (item 10). |
| Go live with **empty** reason templates | Sends may skip with `skipped_reason_template_disabled`. |
| Debug only from merchant dashboard | Use **`/dev/recovery-health`** and **admin support diagnostics** (items 6–7). |
| Change recovery delay/send/WhatsApp code during pilot | Pilot validates **existing** behavior; fixes are separate releases. |

### When to stop (do not proceed to step 7)

Stop the pilot session and fix before “go live limited” if:

1. **Signup or login fails** — no store row.
2. **`/dev/recovery-health`** shows `stuck_running_detected=true` or scheduler owner mismatch in multi-worker deploy.
3. **No cart row** after test-widget abandon (widget path, phone, or `POST /api/cart-event` broken).
4. **Repeated `whatsapp_failed`** in sandbox without ops understanding (templates, sandbox join, or env).
5. **Zid OAuth required** by merchant mentally but env shows “قيد الإعداد” — fix B1 first.
6. Merchant expects **revenue recovered** same day as first message — reset expectations (item 10).

### When the first merchant is ready (checklist pass)

Mark **pilot ready** when **all** are true:

- [ ] Items **1, 3, 6, 7, 8** at **READY** or accepted **PARTIAL** with documented workaround (test-widget + mock send).
- [ ] Item **2** at **READY** *or* signed **widget-only day 1** waiver.
- [ ] Item **5** — templates non-empty for test reasons used.
- [ ] Item **9** — ops written prod checklist acknowledged **before** any prod send promise.
- [ ] Item **10** — founder demonstrated **sent vs recovered**; one purchase-stop test path verified in staging.
- [ ] No open **P0 blockers** B1–B7 for chosen scope.
- [ ] Founder runbook stored: signup URL, test-widget link, recovery-health URL, admin diagnostics URL, support contact.

Mark **production-ready** only after step 6 (WhatsApp production prep) complete and item **9** executed — typically **not** the same calendar day as first signup.

---

## Quick reference URLs (replace `{host}`)

| Purpose | Path |
|---------|------|
| Merchant signup | `/signup` |
| Merchant login | `/login` |
| Test widget (merchant) | `/dashboard/test-widget` |
| Recovery health (ops) | `/dev/recovery-health` |
| Admin support diagnostics | `/admin/support-diagnostics` or `/admin/support-diagnostics/ui` |
| Purchase truth debug (ops) | `/dev/purchase-truth-status` |

---

## Changelog

| Version | Date | Notes |
|---------|------|-------|
| v1 | 2026-05-19 | Initial checklist + readiness matrix + founder day-one playbook |
