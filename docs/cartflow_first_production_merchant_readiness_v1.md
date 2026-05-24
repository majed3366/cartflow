# First Production Merchant Readiness Audit v1

**Date (UTC):** 2026-05-19  
**Scope:** Read-only audit — *“If a real merchant arrives tomorrow, can CartFlow go live within one day?”*  
**Commit message:** `docs: add first production merchant readiness audit v1`

**No runtime, recovery, dashboard, queue, widget, or WhatsApp code changes.**

Related: `docs/cartflow_first_merchant_journey_audit_v1.md`, `docs/audit_merchant_onboarding_reality_v1.md`, `docs/whatsapp_production_reality_v1.md`, `docs/cartflow_merchant_activation_path_v1.md`, `docs/merchant_production_readiness_path_v1.md`.

---

## Executive answer

| Question | Honest answer |
|----------|----------------|
| **Can a real merchant go live in &lt;1 calendar day?** | **Only with heavy founder/ops support and a narrowed definition of “go live.”** |
| **Sandbox proof** (account, widget, abandon, mock or sandbox send, cart visible) | **Possible in one working day** (~6–10 h merchant + ~2–4 h support). |
| **Production WhatsApp** (real customer messages, compliant templates, delivery callbacks) | **Not in one day** for a typical merchant without pre-provisioned platform ops and Meta/Twilio lead time. |
| **Unattended** (no human help) | **No** — public funnel, OAuth, and provider gates block it. |

### Verdict: **PARTIAL** (needs support)

Maps to: **“Needs support”** — not **YES** (&lt;1 day self-serve production), not **NO** (architecture is present for guided rollout).

---

## 1. Exact go-live path (as implemented)

Legend: **Merchant time** = skilled merchant with Arabic UI literacy. **Ops time** = CartFlow operator on server/env/provider consoles. **Wall-clock** includes mandatory waits (e.g. 2 min recovery delay).

| Step | What happens (code / product) | Merchant time | Ops / founder time | Wall-clock notes |
|------|------------------------------|---------------|--------------------|------------------|
| **1. Signup** | `GET/POST /signup` → `MerchantUser` + `Store` (`recovery_delay=2`, `recovery_attempts=1`, widget flags on). **Not** `/register` (placeholder). | 5–10 min | 0–5 min (send `/signup` link) | Instant account; email verify not required in flow |
| **2. Login** | Session cookie; post-signup → `/login?registered=1` | 2–3 min | 0 | — |
| **3. Store connection** | `/dashboard#settings` → Zid OAuth when `ZID_CLIENT_ID` + `ZID_CLIENT_SECRET`; callback `/auth/callback` → `Store.access_token`. Signup slug ≠ connected. Onboarding step **store** needs token + `recovery_enabled`. | 10–20 min (OAuth clicks) | **30–90 min** if OAuth app/redirect misconfigured; **0** if pre-provisioned | **P0** if “ميزة الربط قيد الإعداد” |
| **4. WhatsApp (dashboard config)** | `#whatsapp`: `store_whatsapp_number`, `whatsapp_recovery_enabled`, `reason_templates_json` via `/api/recovery-settings`. **Does not** connect Twilio/WABA in UI. | 15–30 min | **1–3 h** env: `PRODUCTION_MODE`, `TWILIO_*`, callbacks | Merchant configures **intent** only |
| **5. Templates** | Local JSON templates + reason tags; **no** Meta template ID sync. Production readiness expects provider-approved templates (manual/offline). | 20–45 min (copy edit) | **0 min** local; **24 h–7 d** Meta/Twilio approval | Outside 24h window = template policy |
| **6. Widget** | Copy embed from settings; `data-store={zid_store_id}`; V2 runtime via `widget_loader.js`. DB `widget_installed` / enable flags. | **30–90 min** (theme/editor) | 15–30 min (verify snippet, staging URL) | Biggest merchant skill variance |
| **7. Test recovery** | Abandon → `POST /api/cart-event` → schedule → wake → send. Default **2 min** delay. Milestones: `first_cart_*`, `first_whatsapp_sent`. | 10–15 min test flow | 10 min (watch logs / carts row) | **+2 min** mandatory wait |
| **8. First real send** | `recovery_uses_real_whatsapp()` = `PRODUCTION_MODE` + Twilio env. Else **`mock_sent`**. Sandbox: recipient must **join** Twilio sandbox. | 0 (automatic after delay) | **30–60 min** first Twilio setup; sandbox join instructions to merchant | Mock = minutes; real = ops-dependent |
| **9. Proof** | **Operational:** cart row, logs, `first_whatsapp_sent`. **Business “recovered”:** purchase / `POST /api/conversion` / `purchase_truth_records` — not same day without real order. | 5 min refresh | 5 min verify `[PURCHASE DETECTED]` / carts | KPI “recovered” may stay **0** after send |

### End-to-end time budgets

| Definition of “go live” | Merchant-active time | Founder/ops time | Calendar time |
|-------------------------|----------------------|------------------|---------------|
| **A — Sandbox proof** (mock/sandbox send, cart proof) | **~2–3 h** | **~2–4 h** | **1 working day** (fits &lt;1 day **with support**) |
| **B — Production WhatsApp live** (real sends to customers) | **~3–4 h** config | **~4–8 h** + provider consoles | **1–3+ days** (templates, sandbox→prod, callbacks) |
| **C — Production + revenue proof** | Same as B | Same + traffic wait | **Days–weeks** |

**Recommended “day one” scope for a first real merchant:** Definition **A** only, with founder on call and `PRODUCTION_MODE` off or Twilio sandbox pre-joined.

---

## 2. Dependency inventory

### 2.1 Required (cannot complete intended go-live without)

| Dependency | Owner | Evidence |
|------------|-------|----------|
| **CartFlow app reachable** | Ops | HTTPS deploy, `SECRET_KEY`, DB |
| **Merchant account** | Merchant | `/signup` (not `/register`) |
| **Store row + `zid_store_id`** | System | Created at signup |
| **Widget on storefront** | Merchant + dev | Embed snippet; correct `data-store` |
| **`POST /api/cart-event`** | Storefront scripts | Abandon path |
| **Recovery settings** | Merchant | Delays, attempts, recovery enabled |
| **Reason templates (local)** | Merchant | `reason_templates_json` — empty → send may skip |
| **For production real send:** `PRODUCTION_MODE` + `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` + `TWILIO_WHATSAPP_FROM` | **Ops** | `services/whatsapp_send.py` |
| **For production real send:** Meta/Twilio **approved templates** | Merchant + Meta | No approval API in CartFlow |
| **For production:** public URL + `TWILIO_STATUS_CALLBACK_URL` / `CARTFLOW_PUBLIC_BASE_URL` | Ops | Delivery truth v2 |
| **For Zid “connected” checklist:** `ZID_CLIENT_ID`, `ZID_CLIENT_SECRET`, `OAUTH_REDIRECT_URI` registered | Ops | `merchant_store_connection_v1` |
| **For Zid OAuth:** merchant Zid merchant account | Merchant | OAuth consent |
| **For password reset (production):** `RESEND_API_KEY`, `RESEND_FROM_EMAIL` | Ops | `merchant_password_reset_email` |
| **Customer phone** in abandon flow | End customer | Widget phone capture |

### 2.2 Optional (improves experience, not blocking sandbox proof)

| Dependency | Notes |
|------------|-------|
| Zid OAuth / `access_token` | Widget-only abandon works with signup slug; onboarding **store** step still wants OAuth |
| Salla / Shopify connection | Scaffold only — “قريباً” |
| Meta Cloud API send path | Not active; Twilio only |
| `GET /dev/purchase-truth-status` | Ops debug |
| VIP flows | Parallel product surface |
| Platform gateway `order_paid` | Code exists; **not** on live Zid webhook |
| Email verification at signup | Not required in current auth |
| Multi-store per merchant | Single store per user model today |

### 2.3 Hidden operational work (not shown as a merchant checklist step)

| Work | Who | Why hidden |
|------|-----|------------|
| Provision Twilio account + WhatsApp sender | Ops | No in-app “connect provider” |
| Register OAuth redirect at Zid developer portal | Ops | One-time per environment |
| Set `PRODUCTION_MODE`, rotate secrets, `CARTFLOW_PUBLIC_BASE_URL` | Ops | Deploy config |
| Join Twilio sandbox with test handset | Merchant | WhatsApp console — not in CartFlow UI |
| Submit WhatsApp templates to Meta for approval | Merchant/agency | External policy |
| Configure Twilio status callback URL | Ops | `whatsapp_delivery_webhook` |
| Pre-build test HTML page or staging theme for widget | Founder | No merchant-scoped in-app test URL (use `/dashboard/test-widget` → `/demo/store?store_slug=…` when deployed) |
| Monitor `[MERCHANT READINESS]`, recovery-health, Sentry | Ops | Admin routes |
| Explain mock vs `sent_real` vs “recovered” KPI | Founder | Copy/training |
| DB migrations / `purchase_truth_records` schema | Ops | First deploy |
| Worker/scheduler ownership (single vs multi Uvicorn) | Ops | `cartflow_queue_worker_maturity_audit_v1` |
| Legal: WhatsApp opt-in, privacy, store policies | Merchant + legal | Product does not auto-generate |

---

## 3. Human support burden

### Can the merchant do it alone?

| Phase | Alone? | Why |
|-------|--------|-----|
| Discover product + signup | **No** | Landing → `/register` dead-end |
| Dashboard onboarding (5 steps) | **Partial** | Arabic UI helps; OAuth + widget embed hard |
| Sandbox test (mock send) | **Partial** | Possible if told `/signup`, given test page, waits explained |
| Production WhatsApp | **No** | Provider is platform env, not self-serve |
| Interpret failures | **No** | Recovery-health / readiness logs ops-oriented |

### Founder / support involvement

| Scenario | Estimated support hours (first merchant) | Notes |
|----------|----------------------------------------|-------|
| **Guided sandbox go-live (day 1)** | **2–4 h** | URL, OAuth fix, test page, 2 min delay, read carts together |
| **Production cutover (first time)** | **8–16 h** spread over days | Twilio, templates, callbacks, first real send debug |
| **Per additional merchant (production)** | **4–8 h** week 1, then **1–2 h/mo** | Assumes env stable, playbooks exist |
| **If OAuth/Twilio broken in env** | **+4–12 h** | Dominates calendar |

**Rule of thumb:** Plan **one founder half-day per first production merchant**, not zero touch.

---

## 4. Failure points (where onboarding stops)

### P0 — Stops or nullifies “go live” without intervention

| # | Failure point | Symptom | Evidence |
|---|---------------|---------|----------|
| P0-1 | Marketing **`/register`** placeholder | Merchant never signs up | `cartflow_landing.html`, `register_placeholder.html` |
| P0-2 | **Zid OAuth not configured** | “ميزة الربط قيد الإعداد”; store step stuck | `merchant_store_connection_v1`, onboarding `store` step |
| P0-3 | **Production WhatsApp expected day 1** | Sends fail or mock-only confusion | `PRODUCTION_MODE`, Twilio env |
| P0-4 | **Unapproved WhatsApp templates** (production) | Mass `whatsapp_failed` / template errors | `whatsapp_production_reality_v1` |
| P0-5 | **Widget not embedded** | No carts; “doesn’t work” | No abandon events |
| P0-6 | **Wrong test store** (`/demo/store` only) | Dashboard empty while demo has events | `demo_store.html` `data-store="demo"` vs `/dashboard/test-widget` |
| P0-7 | **Empty `reason_templates_json`** | `skipped_reason_template_disabled` | Signup store defaults |
| P0-8 | **Platform order webhook → no purchase truth** | Recovery continues after real platform order | `POST /webhook/zid` no purchase ingest |

### P1 — Slows, confuses, increases support load

| # | Failure point | Symptom |
|---|---------------|---------|
| P1-1 | **2 min `recovery_delay`** without UI countdown | “Nothing happened” |
| P1-2 | Onboarding **store** requires OAuth while widget path does not | Checklist vs reality split |
| P1-3 | **Dual setup UIs** (5-step card + setup experience + readiness path) | Conflicting % complete |
| P1-4 | **Mock vs real send** not on cart row | Trust gap in sandbox |
| P1-5 | **“Recovered” KPI** vs **sent** | Merchant thinks product failed |
| P1-6 | Twilio **sandbox join** not guided in-product | Test send never arrives |
| P1-7 | **`templates_approved=unknown`** in readiness | False confidence at 100% score |
| P1-8 | Merchant thinks **`whatsapp_provider_mode`** controls provider | Field not wired to send (`Store` display only) |

### P2 — Polish / scale

| # | Failure point |
|---|---------------|
| P2-1 | No Salla/Shopify live connect |
| P2-2 | No Meta send path |
| P2-3 | No delivery `read` metrics in merchant UI |
| P2-4 | Single admin “latest store” operational card |
| P2-5 | Multi-worker scheduler ambiguity |

---

## 5. Go-live path diagram

```mermaid
flowchart TD
  subgraph day1 [Day 1 realistic scope]
    S[Signup /signup 5-10m]
    L[Login 2m]
    O[Onboarding dashboard 20-40m]
    Z{Zid OAuth}
    W[WhatsApp tab config 15-30m]
    T[Templates edit 20-45m]
    G[Widget embed 30-90m]
    X[Test abandon + reason 10m]
    D[Wait recovery_delay 2m]
    P[Proof: cart + sent/mock 5m]
    S --> L --> O --> Z
    O --> W --> T --> G --> X --> D --> P
  end

  subgraph ops [Ops not in one day]
    TW[Twilio + PRODUCTION_MODE 1-3h]
    CB[Status callback URL]
    META[Meta template approval 1-7d]
    TW --> CB
    META --> TW
  end

  subgraph blocked [Blocks unattended go-live]
    R[/register dead-end]
    DEMO[/demo/store wrong slug]
  end
```

---

## 6. Durable evidence & “proof” at go-live

| Proof type | Available day 1? | Durable? |
|------------|------------------|----------|
| Cart appears in `#carts` | Yes (if widget OK) | DB `AbandonedCart` |
| `first_whatsapp_sent` milestone | Yes (after delay) | API + logs |
| `mock_sent` / `sent_real` in logs | Yes | `CartRecoveryLog` |
| `[MERCHANT READINESS]` level | Yes | Logs |
| Purchase / `purchase_truth_records` | Only with test conversion POST | DB when ingested |
| Dashboard “recovered” KPI | Unlikely day 1 | Needs real conversion |
| `production_ready` onboarding state | Rare day 1 without ops | Evaluator flags |

---

## 7. Source-of-truth for “ready to go live”

| Layer | What it proves |
|-------|----------------|
| `evaluate_onboarding_readiness` / `merchant_onboarding_reality_v1` | **Config** readiness (not first send) |
| `build_merchant_onboarding_flow` | **Checklist** steps (stricter store rule) |
| `merchant_production_readiness_path_v1` | **Next action** Arabic for ops |
| `recovery_uses_real_whatsapp()` | **Real vs mock** send |
| First cart / send milestones | **Behavioral** proof |
| `purchase_truth_records` | **Purchase** proof (separate track) |

**There is no single `go_live_ready` boolean** — ops must pick definition A vs B (§1).

---

## 8. Verdict detail

### Why not **YES** (&lt;1 day, unattended)

- Public signup funnel broken (`/register`).
- Production WhatsApp is **ops-provisioned**, not merchant self-serve.
- Meta template approval is **calendar days**, not hours.
- Widget embed is **merchant IT work**, not a 10-minute toggle.
- “Go live” confused with **“recovered revenue”** — not achievable in one day without orchestration.

### Why not **NO**

- Auth, store model, dashboard, widget runtime, cart-event recovery, mock/sandbox sends, readiness cards, scoped activation test URL (`/dashboard/test-widget`), and purchase truth **exist**.
- A disciplined **founder-led day-one sandbox** onboarding is **feasible** and matches current code paths.

### **PARTIAL** — recommended operating model

| Role | Day 1 |
|------|-------|
| **Merchant** | Signup, configure WhatsApp number + templates, embed widget, run one guided abandon test, accept 2 min wait |
| **Founder/ops** | Send `/signup`, fix OAuth/Twilio env, provide test page, join sandbox, interpret carts/logs, set expectations on KPIs |
| **Calendar** | **One working day** for sandbox proof; **multi-day** for production WhatsApp |

---

## 9. Day-one playbook (documentation only — for support)

1. Send merchant **`https://{host}/signup`** (not `/register`).  
2. Confirm **`[MERCHANT READINESS]`** — target `sandbox_only` or `partial`, not necessarily `production_ready`.  
3. Complete **WhatsApp number + recovery on + templates** before embed test.  
4. Use **`/dashboard/test-widget`** or custom HTML with merchant `data-store`.  
5. Run abandon + reason + phone; **wait 2 minutes**; refresh `#carts`.  
6. Explain **mock** if `PRODUCTION_MODE` off; plan production cutover as **day 2+** with Twilio/Meta checklist.

---

## 10. Code references

| Area | Location |
|------|----------|
| Signup | `routes/merchant_auth.py`, `services/merchant_auth_v1.py` |
| Onboarding | `services/merchant_onboarding_v1.py`, `services/merchant_setup_experience_v1.py` |
| Readiness | `services/merchant_onboarding_reality_v1.py`, `services/cartflow_onboarding_readiness.py` |
| Store OAuth | `services/merchant_store_connection_v1.py`, `main.py` `/auth/callback` |
| WhatsApp send gate | `services/whatsapp_send.py` |
| Activation test URL | `merchant_activation_test_store_url`, `/dashboard/test-widget` |
| Recovery | `main.py` `POST /api/cart-event`, `_run_recovery_sequence_after_cart_abandoned_impl` |
| Purchase proof | `POST /api/conversion`, `services/cartflow_purchase_truth.py` |

---

## 11. Reviewer checklist

- [ ] Confirm production env vars for target host before promising real sends  
- [ ] Confirm Zid OAuth app + redirect URI for merchant’s market  
- [ ] Pre-create Twilio sandbox + test handset joined  
- [ ] Use sandbox definition for “day one”; schedule production for day 2+  
- [ ] Accept **PARTIAL** verdict unless funnel + provider self-serve ship
