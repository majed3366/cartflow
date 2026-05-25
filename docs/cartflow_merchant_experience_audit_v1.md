# CartFlow Merchant Experience Audit v1

**Date (UTC):** 2026-05-19  
**Method:** Read-only review — enter as a **first-time merchant** (Arabic RTL, mobile-capable). **No** runtime changes.  
**Commit message:** `docs: add merchant experience audit v1`

**Evidence:** `templates/cartflow_landing.html`, `templates/merchant_auth_signup.html`, `templates/merchant_app.html`, `static/merchant_dashboard_lazy.js`, `services/merchant_onboarding_v1.py`, `services/merchant_activation_v1.py`, `services/cartflow_merchant_clarity.py`, prior audits (`cartflow_first_merchant_journey_audit_v1.md`, `cartflow_founder_hours_reduction_v2.md`, `cartflow_first_merchant_launch_checklist_v1.md`).

---

## Executive verdict

| Surface | Verdict | One-line |
|---------|---------|----------|
| **Landing page** | **PARTIAL** | Strong visual brand; value proposition mostly in image + screen-reader text; trust signals thin. |
| **Signup** | **PASS** | Short form, clear Arabic errors; expectations after submit under-explained. |
| **Dashboard (<30 s comprehension)** | **PARTIAL** | Activation card gives “what to do”; lazy load + dual KPIs blur “what happened” and “value”. |
| **First test without founder** | **PARTIAL** | Test-widget path exists; recovery + explanation still need discipline (phone, reason, wait, templates). |
| **Daily / Setup / Advanced / Admin separation** | **PARTIAL** | Top nav groups help; **Setup** is fragmented across 3+ home surfaces; **Admin** correctly absent for merchants. |

**Overall merchant experience (first visit → first proof):** **PARTIAL** — viable **with** activation card + test-widget; **not** self-serve production-ready.

---

## Part 1 — Landing page

Reviewed as a cold visitor on mobile and desktop.

### 1.1 Is it clear?

| Criterion | Verdict | Notes |
|-----------|---------|-------|
| **What CartFlow is** | **PARTIAL** | Primary UI is a **682px reference image** with invisible hotspots (`cartflow_landing_reference.jpg`). Readable headline exists only in `.sr-only`: *«حوّل السلال المتروكة إلى مبيعات»*. Sighted users depend on image legibility. |
| **Who it is for** | **PARTIAL** | Implied (Zid-style dashboard mock in image); not stated in visible HTML text. |
| **Next step** | **PASS** | CTAs map to `/signup` (header, hero, footer). Fallback **«روابط سريعة»** if hotspots misalign on some screens. |

### 1.2 Trust?

| Signal | Verdict | Notes |
|--------|---------|-------|
| Social proof (logos, quotes) | **FAIL** | Not in template — image-only marketing. |
| Security / privacy | **FAIL** | No footer links to policies on landing. |
| Product substance | **PARTIAL** | Dashboard screenshot in artwork suggests real product. |
| Brand polish | **PASS** | Consistent Arabic typography (Tajawal), centered mobile shell. |

### 1.3 Outcome communicated?

| Outcome | Verdict | Notes |
|---------|---------|-------|
| Abandon → WhatsApp recovery | **PARTIAL** | Stated in `sr-only` paragraph; not guaranteed visible without reading alt/skip-nav. |
| Measurable result (recovered carts / revenue) | **PARTIAL** | Implied in hero artwork KPIs, not copy. |
| Time to value | **FAIL** | No “first result in X minutes” on landing. |

### 1.4 Confusing elements?

| Issue | Severity |
|-------|----------|
| **«احجز عرض توضيحي»** and **«ابدأ الآن مجاناً»** both go to **`/signup`** | Medium — demo vs signup intent blurred |
| Pixel-perfect hotspots can **miss** on unusual viewports | Medium — mitigated by skip-nav |
| **`/register`** still exists (`register_placeholder.html` — “قيد الإعداد”) if linked externally | Low — landing fixed; old links remain |
| No visible pricing / plan | Low — topbar shows «الباقة» disabled in dashboard, not on landing |

**Landing sub-score:** **PARTIAL**

---

## Part 2 — Signup

**Route:** `GET/POST /signup` — `merchant_auth_signup.html`

### Friction

| Step | Verdict | Friction |
|------|---------|----------|
| Fields | **PASS** | Store name, email, password, confirm — minimal. |
| Validation | **PASS** | Arabic field errors; password min 8. |
| Mobile | **PASS** | `inputmode=email`, UTF-8 form. |
| Post-submit | **PARTIAL** | Redirect to `/login?registered=1` — extra step before dashboard. |
| Email verification | **N/A** | Not required (faster, less trust signal). |

### Expectations set?

| Expectation | Set at signup? | Verdict |
|-------------|----------------|---------|
| You get a dashboard immediately after login | Implicit | **PARTIAL** |
| Zid OAuth will be needed for “connected store” | **No** | **FAIL** for informed consent |
| WhatsApp is configured in dashboard, not connected here | **No** | **PARTIAL** |
| First proof uses **test store** + ~2 min delay | **No** | **FAIL** |
| Messages may be **mock/sandbox** until production | **No** | **FAIL** |

**Signup sub-score:** **PASS** (flow) / **PARTIAL** (expectations)

---

## Part 3 — Dashboard: the 30-second test

**Assumption:** Merchant just logged in; `merchant_dashboard_lazy_shell` loads summary via `GET /api/dashboard/summary`.

### Can they answer in <30 seconds?

| Question | Verdict | What merchant actually sees |
|----------|---------|------------------------------|
| **What happened?** | **PARTIAL** | Top KPIs (سلال متروكة / تم استردادها / رسائل واتساب) often **0** or skeleton `…` until JSON returns. Activation timeline shows state *after* fetch. **No** single “last event” sentence in first paint. |
| **What to do?** | **PASS** (when loaded) | **Activation card** (`ma-activation-root`): title *«تفعيل سريع — أول نجاح»*, `next_step_ar`, primary CTA **«فتح متجر الاختبار»** → `/dashboard/test-widget`. Onboarding card (*5 steps*) on home **إعداد المتجر**. |
| **What value?** | **PARTIAL** | Month summary + recovery % communicate value **only after data**. Zeros read as “product empty” not “awaiting first test”. **«تم استردادها»** sounds like revenue before any send. |

### Cognitive load on home (first screen)

| Element | Role | 30s clarity |
|---------|------|-------------|
| Global topbar (الرئيسية / السلال / التواصل / الإعدادات) | Navigation | **PASS** |
| Activation band | Setup / first success | **PASS** when visible |
| Setup experience card (`ma-setup-experience-root`) | Setup % | **PARTIAL** — second checklist |
| Month summary + KPI grid | Daily value | **PARTIAL** — competes with setup |
| Context sidebar (changes per section) | Wayfinding | **PASS** |

**Dashboard sub-score:** **PARTIAL** (improves after ~2–5 s JSON load; weak on instant “what happened”)

---

## Part 4 — First test without founder

Can a literate merchant reach **first widget**, **first recovery**, **first explanation** unaided?

| Milestone | Without founder? | Verdict | Path & gaps |
|-----------|------------------|---------|-------------|
| **First widget** | **Sometimes** | **PARTIAL** | **«فتح متجر الاختبار»** → scoped `/demo/store?store_slug={merchant}` (`merchant_activation_v1`). Must complete phone + exit-intent in widget. No step-by-step wizard. |
| **First recovery** | **Sometimes** | **PARTIAL** | Abandon → `POST /api/cart-event` → schedule; default **2 min** delay. `delay_hint_ar` on activation card helps **if** merchant returns to dashboard. Empty `reason_templates_json` can block reason-specific send. |
| **First explanation** | **Rarely** | **PARTIAL** | Cart list uses `cartflow_merchant_clarity` Arabic labels (`mock_sent` → *«تم إرسال رسالة الاسترجاع»*). Milestone hint: *«قد تكون رسالة تجريبية»*. **No** plain “why no WhatsApp on my phone” for mock. **No** merchant-facing failure decoder. |

### Unaided success conditions (all required)

1. Finds `/signup` (not old `/register` link).  
2. Completes login after signup.  
3. Clicks **test store** from home (does not paste snippet on Zid first).  
4. Enters **valid test phone** + captures **reason** in widget.  
5. Waits **full recovery delay** and revisits **السلال**.  
6. Has **non-empty** templates or accepts generic send path.

**Estimated unaided completion rate (first merchant, no docs):** **low** — **PARTIAL** product path, **FAIL** as self-serve onboarding.

**First test sub-score:** **PARTIAL**

---

## Part 5 — Experience classification (Daily / Setup / Advanced / Admin)

### Intended separation

| Class | Purpose | Merchant-facing home |
|-------|---------|----------------------|
| **Daily use** | Monitor carts, outcomes, messages | **الرئيسية** KPIs, **السلال** tabs, **التواصل** messages |
| **Setup** | Connect store, WhatsApp, widget, first test | **إعداد المتجر**, activation, `#settings` `#whatsapp` `#widget` |
| **Advanced** | Power tuning, VIP, multi-message templates | Recovery delay/attempts, VIP tab, trigger templates, exit intent |
| **Admin** | Platform ops, cross-merchant diagnostics | **Not exposed** to merchants (`/admin/*`, `/dev/*`) |

### Does the UI separate them?

| Class | Separation verdict | Where it lives today | Problem |
|-------|-------------------|----------------------|---------|
| **Daily use** | **PASS** | Top nav **السلال** + home KPIs/month | Clear once merchant has data |
| **Setup** | **FAIL** | Split across: (1) activation card, (2) `merchant_setup_experience` %, (3) `merchant_onboarding_v1` 5-step spec, (4) production readiness path in API, (5) settings sub-nav | **No single “Setup mode”** — three progress narratives |
| **Advanced** | **PARTIAL** | Mixed into **التواصل** (templates, reasons) and **الإعدادات**; VIP under **السلال** | Power features not labeled “متقدم” |
| **Admin** | **PASS** | Merchants stay in `/dashboard*`; ops use separate routes | Correct boundary |

### Recommended mental model (for docs/training, not implemented)

```text
Setup     → Home «إعداد المتجر» + activation CTA only until first_whatsapp_sent
Daily     → السلال + الرئيسية KPIs (hide setup cards after activation_working)
Advanced  → تواصل (templates) + إعدادات (delays, VIP threshold)
Admin     → CartFlow team only
```

**Classification sub-score:** **PARTIAL**

---

## Part 6 — Top 5 confusion points

| Rank | Confusion | Who hits it | Verdict driver | Fix class (docs roadmap) |
|------|-----------|-------------|----------------|--------------------------|
| **1** | **«تم استردادها»** KPI vs **«تم إرسال رسالة»** on cart row | Every new merchant | **FAIL** semantics for day 1 | Product copy + KPI tooltip (P0) |
| **2** | **«ربط واتساب»** sounds like connecting Twilio/Meta; dashboard only stores number + flags | Setup phase | **PARTIAL** honesty, **FAIL** self-serve prod | Sandbox/production banner (P0) |
| **3** | **Three setup progress UIs** (activation milestones, setup experience %, 5-step onboarding) | Home visitors | **FAIL** single story | Consolidate setup surface (P0) |
| **4** | **Store “connected”** = Zid OAuth in onboarding, but **test-widget works without OAuth** | Zid merchants | **PARTIAL** path split | “Widget-only today” branch (P0) |
| **5** | **2-minute wait** with no in-product countdown; merchant refreshes empty KPIs | First test | **PARTIAL** | Delay timer on activation + cart row (P1) |

**Honorable mentions:** `/register` placeholder (external links); **«احجز عرض»** → signup; lazy skeleton `…` feels broken; VIP manual path vs automated recovery.

---

## Part 7 — PASS / PARTIAL / FAIL matrix (detailed)

| Area | Clear | Trust | Outcome | Self-serve first test |
|------|-------|-------|---------|------------------------|
| Landing | PARTIAL | PARTIAL | PARTIAL | — |
| Signup | PASS | PARTIAL | PARTIAL | — |
| Dashboard @30s | PARTIAL | PARTIAL | PARTIAL | — |
| First widget | — | — | — | PARTIAL |
| First recovery | — | — | — | PARTIAL |
| First explanation | — | — | — | PARTIAL |
| Daily vs Setup split | PASS / — | — | — | FAIL (setup) |
| Admin boundary | PASS | — | — | — |

---

## Part 8 — Summary for product positioning

| Persona | Experience |
|---------|------------|
| **Cold visitor** | Attractive but **image-dependent** landing; trust/outcome copy thin. |
| **New merchant (guided)** | **PASS** signup → **PARTIAL** dashboard → **PARTIAL** test path with founder link to test-widget. |
| **New merchant (alone)** | Likely stuck on OAuth order, empty KPIs, or delay — **FAIL** as self-serve. |
| **Daily merchant (activated)** | **PASS** carts + comms nav — **PARTIAL** until KPI semantics learned. |

### Alignment with founder-hours audit v2

Merchant experience gaps **explain** why sandbox still needs **~90–150 min** founder time: the product **shows** activation CTAs but does not **close** interpretation, provider, and setup-story gaps without a human.

---

## Part 9 — Improvement priorities (documentation only)

| Priority | Merchant experience fix | Expected shift |
|----------|-------------------------|----------------|
| **P0** | Single setup home; KPI tooltips (sent ≠ recovered); WhatsApp mode banner | Setup **FAIL** → **PARTIAL** |
| **P0** | First-test wizard (test-widget → phone → wait → view cart) | First test **PARTIAL** → **PASS** (unaided) |
| **P1** | Landing visible value prop (not only image); demo CTA distinct from signup | Landing **PARTIAL** → **PASS** |
| **P1** | Label **Advanced** section in sidebar | Classification **PARTIAL** → **PASS** |
| **P2** | Trust footer (privacy, contact); testimonials | Landing trust **FAIL** → **PARTIAL** |

---

## Document control

| Item | Value |
|------|--------|
| Runtime changes | **None** |
| Related | `cartflow_founder_hours_reduction_v2.md`, `cartflow_first_merchant_launch_checklist_v1.md` |
