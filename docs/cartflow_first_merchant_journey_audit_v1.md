# CartFlow First Merchant Journey Audit v1

**Date (UTC):** 2026-05-19  
**Scope:** Read-only audit — signup through trust. **No** runtime changes to widget, WhatsApp, recovery, onboarding logic, auth, dashboard, or integrations.  
**Commit message:** `docs: add first merchant journey audit v1`  
**Related:** `docs/audit_merchant_onboarding_reality_v1.md`, `docs/cartflow_integration_foundation_audit_v1.md`, `services/merchant_onboarding_v1.py`, `routes/merchant_auth.py`

---

## Executive question

**Can a real merchant go from signup → working CartFlow without our help?**

| Verdict | Answer |
|---------|--------|
| **Can first real merchant onboard today?** | **PARTIAL** |
| **Self-serve from public homepage** | **NO** (CTA → dead-end `/register`) |
| **Self-serve if they reach `/signup`** | **YES** for account + dashboard + sandbox-style widget path |
| **Self-serve to real WhatsApp production** | **NO** (platform env, Twilio, templates, callbacks) |
| **Self-serve to “I recovered a cart” (revenue KPI)** | **NO** without guided test or days of real traffic |

**Reason:** Product plumbing exists (auth, guided onboarding, store connection UI, readiness cards, cart-event recovery). The **public entry funnel is broken**, **Zid OAuth and production WhatsApp are operator-gated**, and **“recovered” is a purchase outcome** merchants will not see on day one without orchestration.

---

## Part 1 — First merchant journey map

Legend: **Clarity** 1–5 (5 = merchant always knows what to do next).

### 1. Signup

| Dimension | Assessment |
|-----------|------------|
| **Current state** | Real signup at **`GET/POST /signup`** (`routes/merchant_auth.py`) creates `MerchantUser` + `Store` (slug, `recovery_delay=2` min, `recovery_attempts=1`). Public landing **`cartflow_landing.html`** links **`/register`**, which serves **`register_placeholder.html`** (“صفحة التسجيل قيد الإعداد”) — not signup. |
| **Blocker** | **HIGH** — Primary CTAs do not reach `/signup`. |
| **Confusion risk** | Merchant believes product is “not ready”; no link to real signup on placeholder page (only “العودة للرئيسية”). |
| **Missing setup** | Merchant must discover `/signup` or `/login` footer link. |
| **Fallback** | Support sends `/signup` URL; dev tests use `register_merchant_account()` directly. |
| **Clarity** | **2/5** from homepage; **4/5** on `/signup` form (Arabic validation messages). |

### 2. Login

| Dimension | Assessment |
|-----------|------------|
| **Current state** | **`/login`** with session cookie; post-signup redirect to login with `?registered=1`. Password reset via Resend when `RESEND_API_KEY` set, else dev log. |
| **Blocker** | None if account exists. |
| **Confusion risk** | Low; “next” param only allows `/dashboard` paths. |
| **Missing setup** | Email deliverability for reset in production. |
| **Fallback** | Forgot-password flow. |
| **Clarity** | **4/5** |

### 3. Merchant onboarding (dashboard)

| Dimension | Assessment |
|-----------|------------|
| **Current state** | **`build_merchant_onboarding_flow`** — 5 steps (account, store, WhatsApp, widget, test_ready); setup badge + lazy JS; store scoped via **`resolve_merchant_onboarding_store`** (no demo/latest fallback). **`merchant_setup_experience_v1`** adds progression card. |
| **Blocker** | Step **store** requires **`access_token`** (real Zid OAuth) **and** `recovery_enabled` — stricter than readiness `store_connected` (slug alone counts). |
| **Confusion risk** | Two parallel narratives: 5-step card vs production-readiness path (4+ steps including “اعتماد الرسائل”). Progress can disagree with `evaluate_onboarding_readiness`. |
| **Missing setup** | None for UI; completeness depends on backend milestones. |
| **Fallback** | `ma-onboarding-focus` hides KPIs until “ready”; merchant can still open all settings tabs. |
| **Clarity** | **4/5** for next action within dashboard; **3/5** vs ops-only production gates. |

### 4. Connect store (Zid)

| Dimension | Assessment |
|-----------|------------|
| **Current state** | **`/dashboard#settings`** + **`GET /api/merchant/store-connection`**; Zid OAuth when `ZID_CLIENT_ID` + `ZID_CLIENT_SECRET`; callback **`/auth/callback`** with signed `state` → tokens on merchant’s `Store`. Salla/Shopify: “قريباً”. |
| **Blocker** | **HIGH** if OAuth env missing → “ميزة الربط قيد الإعداد”. **HIGH** if `OAUTH_REDIRECT_URI` not registered at Zid (default `https://smartreplyai.net/auth/callback`). |
| **Confusion risk** | Signup already created a store slug; merchant may think they are “connected” before OAuth. UI correctly shows “غير مربوط” until `access_token`. |
| **Missing setup** | Zid merchant account; platform operator: OAuth client + redirect URI + `SECRET_KEY` for state signing. |
| **Fallback** | Widget-led recovery can use signup slug on any page embedding script **without** Zid OAuth; onboarding checklist still blocks “store” step. |
| **Clarity** | **4/5** on connection card when OAuth configured; **2/5** when pending. |

### 5. Connect WhatsApp

| Dimension | Assessment |
|-----------|------------|
| **Current state** | Dashboard **`#whatsapp`** — `store_whatsapp_number`, `whatsapp_recovery_enabled`, templates JSON; readiness via **`evaluate_onboarding_readiness`** + **`build_merchant_whatsapp_readiness_card`**. Real send: **`PRODUCTION_MODE`** + Twilio env (not merchant self-serve connect). |
| **Blocker** | **HIGH** for production — Twilio/Meta on server. **MEDIUM** in sandbox — mock path works without merchant provider signup. |
| **Confusion risk** | UI says “ربط واتساب”; merchant cannot connect Twilio in-app. Sandbox vs production not always obvious on first visit. |
| **Missing setup** | Merchant: business WhatsApp number, message templates content. Ops: `TWILIO_*`, `CARTFLOW_PUBLIC_BASE_URL` / status callback, sandbox join for test numbers. |
| **Fallback** | Sandbox/mock sends; `[MERCHANT READINESS]` / setup experience explain gaps in Arabic. |
| **Clarity** | **3/5** (honest about “needs follow-up” but not *how* to fix provider at Meta). |

### 6. Enable widget

| Dimension | Assessment |
|-----------|------------|
| **Current state** | **`cartflow_widget_enabled`** (default true); embed snippet in settings (`widget_loader.js` + `data-store={zid_store_id}`). Recovery truth is **widget / cart-event** driven (`POST /api/cart-event`), not Zid webhook alone. |
| **Blocker** | **HIGH** — Merchant must edit Zid theme or another site; no in-app theme installer. |
| **Confusion risk** | Copy-paste script vs Zid editor permissions; wrong `data-store` slug breaks attribution. |
| **Missing setup** | Access to storefront HTML/theme; optional domain/CSP allowlist for script origin. |
| **Fallback** | Self-hosted test page with snippet; **`/demo/store`** is dev/demo (not linked from merchant dashboard). |
| **Clarity** | **4/5** for snippet; **2/5** for Zid-specific install steps (not productized). |

### 7. Test recovery

| Dimension | Assessment |
|-----------|------------|
| **Current state** | Abandon flow: widget/tracking → `cart_abandoned` → schedule (`recovery_delay` default **2 minutes**) → send (mock if not production). Milestones: `first_cart_detected`, `first_recovery_scheduled`, `first_whatsapp_sent`. Onboarding step **test_ready** completes on any of those three. |
| **Blocker** | **MEDIUM** — Needs cart with **customer phone**; reason may be `waiting_for_reason` until widget reason captured. **MEDIUM** — Twilio sandbox: recipient must join sandbox. |
| **Confusion risk** | Merchant waits on dashboard without triggering abandon on live storefront. |
| **Missing setup** | Test phone; enabled templates (`reason_templates_json` often empty at signup — may block reason-specific sends). |
| **Fallback** | Ops/dev: `POST /dev/cartflow-delay-test`, window simulate (dev only); not exposed to merchants. |
| **Clarity** | **3/5** — carts list shows system path labels via clarity layer; no dedicated “send test recovery now” wizard. |

### 8. Understand result

| Dimension | Assessment |
|-----------|------------|
| **Current state** | **`/dashboard#carts`** — filters (recovered / sent / …), KPIs “تم استردادها”, `cartflow_merchant_clarity` log labels in Arabic. Milestone **`first_recovered_cart`** when `AbandonedCart.status == recovered` or `recovered_at` set (typically **purchase / conversion**, not “message sent”). |
| **Blocker** | **MEDIUM** — “Sent” (mock_sent) ≠ “recovered” in KPIs; merchant may expect revenue after first WhatsApp. |
| **Confusion risk** | High between operational logs (“تم إرسال رسالة”) and business outcome (“تم الاسترداد”). |
| **Missing setup** | Education that recovery attribution follows purchase truth. |
| **Fallback** | Messages tab + recovery log statuses; no merchant-facing `/dev/recovery-health`. |
| **Clarity** | **3/5** for ops detail; **2/5** for causal “why this cart is not recovered yet”. |

### 9. Trust system

| Dimension | Assessment |
|-----------|------------|
| **Current state** | Setup badge %, onboarding card, WhatsApp readiness card, setup experience API, blocker catalog (`BLOCKER_COPY` in `cartflow_onboarding_readiness.py`). Admin has `[MERCHANT READINESS]` and operational health — **not** merchant-visible. |
| **Blocker** | **MEDIUM** — `production_ready` and provider truth are not provable from merchant UI alone. |
| **Confusion risk** | 100% setup badge can still mean sandbox/mock only. |
| **Missing setup** | Delivery truth, template Meta approval, worker health — invisible to merchant. |
| **Fallback** | Contact support; ops logs. |
| **Clarity** | **3/5** for “what’s missing”; **2/5** for “is production safe right now”. |

---

## Part 2 — Time-to-value audit

**Question:** How long until the merchant sees **“I recovered a cart”** (dashboard KPI / `first_recovered_cart`)?

| Scenario | Estimate | Assumptions |
|----------|----------|-------------|
| **Best case** | **Not same session** for true “recovered”; **~30–45 min** to first *recovery signal* (cart + scheduled + mock/sent message) | Knows `/signup`; sandbox/mock; widget on test page; phone on abandon; default 2 min delay; no purchase required for “sent” |
| **Best case (recovered KPI)** | **Hours to days** (or **~1–2 h** with scripted test purchase / `POST /api/conversion`) | Requires conversion/purchase truth or manual status — not default onboarding path |
| **Realistic case** | **2–5+ hours** to first sent/mock; **days–weeks** to first organic recovered cart | Homepage → support link; Zid theme install; OAuth coordination; template fill; real customer traffic |
| **Realistic (production WhatsApp)** | **Days** | Ops enables `PRODUCTION_MODE`, Twilio, callbacks, template approval, sandbox join |

**Honest answer:** Merchants can see **“the system sent / scheduled recovery”** in under an hour only with guidance and a test page. They should **not** expect **“I recovered a cart”** (revenue outcome) on day one without a deliberate end-to-end test purchase.

---

## Part 3 — Setup dependency map

| Item | Required | Optional | Future |
|------|----------|----------|--------|
| Email + password (`/signup`) | ✓ | | |
| CartFlow server DB migrated (`ensure_merchant_auth_schema`) | ✓ (ops) | | |
| Zid merchant account | ✓ for platform-connected catalog/orders narrative | | |
| Zid OAuth app (`ZID_CLIENT_ID/SECRET`, redirect URI) | ✓ for “store connected” in product sense | | |
| Storefront theme access (widget embed) | ✓ for real traffic | Test HTML page | In-app Zid app install |
| `store_whatsapp_number` | ✓ for messaging identity | | |
| `reason_templates_json` / triggers | ✓ for reason-routed sends | Default/generic paths may partial-block | Template wizard |
| Twilio + `PRODUCTION_MODE` | ✓ for real WhatsApp | | Merchant self-serve provider connect |
| Meta template approval | ✓ for outside-24h production | | In-dashboard approval status |
| `CARTFLOW_PUBLIC_BASE_URL` / status callback | ✓ (ops) for delivery truth | | |
| Twilio sandbox join (test phones) | ✓ in sandbox testing | | |
| Customer phone on cart | ✓ | | |
| Domain / HTTPS storefront | ✓ for production widget | localhost dev | |
| Salla / Shopify | | | ✓ scaffolds only |
| VIP / smart offers | | ✓ | |
| `GET /dev/recovery-health` | | ✓ (ops/dev) | Merchant-safe health summary |

---

## Part 4 — Failure points (severity)

| Failure point | Severity | Notes |
|---------------|----------|-------|
| Landing **`/register`** vs real **`/signup`** | **HIGH** | Blocks unattended funnel at step 0 |
| Zid OAuth not configured on server | **HIGH** | “ميزة الربط قيد الإعداد”; store onboarding step never completes |
| OAuth redirect / state / `SECRET_KEY` mismatch | **HIGH** | Silent failed connect or wrong store row (legacy `save_or_update_store_from_token_response` if state missing) |
| Widget not installed on live storefront | **HIGH** | No `first_cart_detected`; recovery never starts |
| Missing customer phone on abandon | **HIGH** | `waiting_for_phone` / `no_customer_phone_source` |
| Production WhatsApp / Twilio not configured | **HIGH** | For real sends; sandbox hides this |
| Template approval unknown / missing local templates | **MEDIUM** | Outbound failures at provider |
| Onboarding “store” step vs widget-only path | **MEDIUM** | Checklist stuck while technical test works |
| Empty `reason_templates_json` at signup | **MEDIUM** | `skipped_reason_template_disabled` risk |
| Merchant expects “recovered” = message sent | **MEDIUM** | KPI/trust mismatch |
| `production_ready` vs runnable sandbox | **MEDIUM** | Over-trust in badge |
| Multi-worker recovery without single scheduler | **LOW** (merchant-visible rarely) | Ops incident |
| Salla/Shopify chosen | **LOW** | Not available — labeled “قريباً” |

---

## Part 5 — Trust audit (post-setup)

| Question | Verdict |
|----------|---------|
| **System status** | **Partial** — Merchant sees setup %, Arabic blockers, cart statuses; does not see worker/scheduler health or delivery truth depth. |
| **Readiness** | **Partial** — `merchant_setup_experience` and WhatsApp card explain gaps; sandbox vs production distinction easy to miss. |
| **Failures** | **Partial** — Per-cart log labels (clarity layer) help; failed sends lack merchant-facing “why + fix” panel (ops have `/dev/recovery-health`). |
| **Next action** | **Good** within dashboard — deep links to `#settings`, `#whatsapp`, `#carts`; weak for off-platform actions (Meta, Twilio, Zid theme). |

**Honest verdict:** After setup, a diligent merchant can trust that **CartFlow is attempting recovery** when carts appear and messages show in logs. They **cannot** fully trust **production readiness** or **revenue recovery** without operator confirmation — by design today (`audit_merchant_onboarding_reality_v1.md`: self-serve to `production_ready` = NO).

---

## Part 6 — Recommended priorities

| Priority | Action | Impact |
|----------|--------|--------|
| **P0** | Point all landing CTAs to **`/signup`** (or redirect `/register` → `/signup`) | Unblocks unattended signup |
| **P0** | Document merchant-visible **“first recovery test”** checklist (widget page + phone + wait 2 min) | Cuts time-to-first signal |
| **P1** | Align onboarding **store** step with widget-only path OR explain OAuth is required for Zid sync | Removes checklist/truth split |
| **P1** | Default or wizard for **`reason_templates_json`** on signup | Fewer silent send skips |
| **P1** | Merchant-safe **recovery status** summary (subset of recovery-health) | Trust on failures |
| **P2** | In-dashboard Zid theme install guide / video | Widget friction |
| **P2** | Clear **sandbox vs production** banner on WhatsApp tab | Trust |
| **P3** | Salla/Shopify when adapters ship | Market expansion |

---

## Journey diagram (as implemented today)

```mermaid
flowchart TD
  A[Homepage /] -->|CTA /register| B[Placeholder - dead end]
  A -->|if knows URL| C[/signup]
  C --> D[/login session]
  D --> E[/dashboard onboarding card]
  E --> F{Zid OAuth?}
  F -->|token| G[Store step complete]
  F -->|skip| H[Widget embed only - step incomplete]
  E --> I[WhatsApp number + templates]
  E --> J[Widget snippet in storefront]
  J --> K[POST /api/cart-event abandon]
  K --> L[Schedule + send mock or real]
  L --> M{Purchase / conversion?}
  M -->|yes| N[KPI recovered / first_recovered_cart]
  M -->|no| O[Sent / waiting - not recovered KPI]
```

---

## Practical conclusion

| Question | Answer |
|----------|--------|
| **Can first real merchant onboard today?** | **PARTIAL** |

**Reason:**

- **YES** for: creating an account (`/signup`), logging in, using the Arabic dashboard, copying the widget, and (with server sandbox) seeing carts and mock/sent recovery activity.
- **NO** for: discovering signup from the marketing site, completing Zid OAuth without ops env, turning on production WhatsApp without ops, and seeing **“I recovered a cart”** as a business result without real purchase traffic or a guided test.

**Working system ≠ working product ≠ merchant success.** Core recovery logic can run; the **first-merchant product path** still requires human ops for OAuth, provider, and funnel fixes before most real merchants succeed alone.

---

## Code references (audit evidence)

| Area | Location |
|------|----------|
| Signup | `routes/merchant_auth.py`, `services/merchant_auth_v1.py` `register_merchant_account` |
| Landing dead-end | `templates/cartflow_landing.html` → `templates/register_placeholder.html` |
| Onboarding steps | `services/merchant_onboarding_v1.py` |
| Readiness / blockers | `services/cartflow_onboarding_readiness.py` |
| Store OAuth | `services/merchant_store_connection_v1.py`, `main.py` `/auth/callback` |
| Recovery ingress | `main.py` `POST /api/cart-event` |
| Production gate | `services/whatsapp_send.py` `recovery_uses_real_whatsapp` |
| Prior onboarding audit | `docs/audit_merchant_onboarding_reality_v1.md` |

---

## Document control

| Item | Value |
|------|--------|
| Runtime changes | **None** |
| Widget / WhatsApp / recovery / auth / dashboard code | **Untouched** |
