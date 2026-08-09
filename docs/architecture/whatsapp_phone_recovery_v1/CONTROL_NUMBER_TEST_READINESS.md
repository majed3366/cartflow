# Control Number Test — Phase C1 Readiness

**Date (UTC):** 2026-08-09  
**Phase:** C1 — Readiness only  
**Status:** **STOP** — no live Meta action, no `/register`, no env overwrite  

---

## Purpose

Use a **new clean Saudi mobile** as a diagnostic control to determine whether Meta registration failure (`100` / `2388001`) is **specific to the existing CartFlow phone**, or systemic to the WABA / app / business setup.

| Role | E.164 | Phone Number ID | WABA |
|------|-------|-----------------|------|
| **Production / problem (immutable)** | `+966 57 970 6669` | `1260388737156321` | `1520530422625766` |
| **Control (new, never WA/WABA)** | `+966 53 313 2601` | *unknown until ES* | TBD by design |

---

## Hard constraints (non-negotiable)

| Must NOT | Why |
|----------|-----|
| Delete / deregister / replace production phone | Protect live asset |
| Call `/register` on `1260388737156321` | Already failed Phase 3; not this test |
| Overwrite `WHATSAPP_PHONE_NUMBER_ID` / `WHATSAPP_BUSINESS_ACCOUNT_ID` / prod tokens | Runtime must keep messaging on production IDs |
| Persist control token into DB / merchant state | Isolation |
| Switch CartFlow runtime to the control phone | Diagnostic only |
| Live Meta action in C1 | Readiness design only |

---

## 1) How current ES recovery is hard-asserted to the old phone

| Layer | Behavior |
|-------|----------|
| `services/admin_whatsapp_embedded_signup_recovery_v1.py` | Constants `TARGET_WABA_ID=1520530422625766`, `TARGET_PHONE_NUMBER_ID=1260388737156321` |
| `assert_existing_assets()` | **ABORT** on any WABA/phone mismatch |
| Shared-WABA fallback | Resolves **only** those exact IDs via `debug_token` + phone enumeration |
| `complete_embedded_signup_recovery` | Stops before `/register`; never persists tokens |
| Admin UI | `/admin/whatsapp/embedded-signup-recovery` — production recovery only |
| Register path | `ALLOWED_REGISTER_PHONE_IDS = {"1260388737156321"}` only |

**Implication:** Reusing the production recovery complete API as-is will **reject** a new Phone Number ID. Control test **must not** share that assert path without a separate mode.

---

## 2) Safest way to add the control number without touching production

### Recommended approach: **same Business + same WABA, separate admin control path**

1. Keep production env IDs and credentials untouched.  
2. Add a **new admin-only** surface (e.g. `/admin/whatsapp/control-number-es`) that:
   - Reuses Meta App ID + Configuration ID + App Secret (already on Railway) for OAuth only  
   - Runs FB.login Embedded Signup  
   - Expects operator to select **existing CartFlow business** and **add/verify** `+966533132601`  
   - Exchanges code ephemerally (same redirect_uri rules as Phase 2B)  
   - Records **only** sanitized IDs: new `phone_number_id`, `waba_id`, display number  
3. **Hard guards on complete:**
   - `new_phone_number_id ≠ 1260388737156321`  
   - Display E.164 normalizes to `+966533132601` (or Meta’s formatted equivalent)  
   - Optionally allow WABA `1520530422625766` (preferred) **or** abort if a *different* WABA was created unexpectedly  
4. **Never** write `WHATSAPP_PHONE_NUMBER_ID` / WABA env / DB.  
5. **STOP before `/register`** (Phase C2+ separately authorized).

### Why not WhatsApp Manager UI alone?

Manager can add a number, but CartFlow would not get a controlled OAuth/session capture, ID assertion, or isolation evidence. Admin ES path gives auditable, abortable diagnostics.

---

## 3) Same WABA vs separate test WABA

| Option | Verdict | Rationale |
|--------|---------|-----------|
| **A. Same WABA `1520530422625766`** | **Preferred for C1→C2** | Closest A/B: same business, app, WABA, payment/verification context. If control `/register` **succeeds** later → failure is likely **phone-specific**. If control also gets `2388001` → failure is likely **WABA/app/business-class**. |
| **B. Brand-new test WABA** | Optional follow-up only | Stronger isolation, but **changes the variable** (new WABA may have different certificate / onboarding state). Use only if same-WABA path is blocked by Meta UI or policy. |
| **C. Separate Meta App** | Out of scope | Would invalidate comparison to production ES config. |

**C1 recommendation:** Design control flow for **Option A (same WABA)**. Document Option B as contingency if Meta refuses a second number on the production WABA.

---

## 4) Exact isolation guards required

### Code / API (future Phase C1.5 implementation — not built in C1)

| Guard | Requirement |
|-------|-------------|
| Separate route + marker | e.g. `control-number-es-v1` — not production recovery marker |
| Assert **reject** production phone ID | Abort if session returns `1260388737156321` |
| Assert **accept** only control E.164 | Normalize and match `+966533132601` |
| Optional WABA assert | Prefer exact `1520530422625766`; abort on unexpected new WABA unless contingency B authorized |
| No env mutation | Never set `WHATSAPP_PHONE_NUMBER_ID` / `WHATSAPP_BUSINESS_ACCOUNT_ID` |
| No DB writes | No store / merchant / WhatsApp credential rows |
| Ephemeral token | Exchange in-memory; never log/return/persist |
| Register deny-by-default | Control phone ID **not** added to `ALLOWED_REGISTER_PHONE_IDS` until a later phase explicitly allowlists it |
| Production recovery unchanged | Existing `/admin/whatsapp/embedded-signup-recovery` keeps hard targets |

### Operational

| Guard | Requirement |
|-------|-------------|
| Admin-only | Same CartFlow admin auth as other Meta ops |
| Single purpose | “Control number diagnostic” labeled in UI |
| No send / no template / no scheduler use of new ID | Runtime messaging stays on env phone |
| Evidence folder | Sanitize JSON only (IDs, statuses, error codes — no tokens/PIN/secret) |

---

## 5) What Meta assets would be created (later live phases)

When operator completes ES for the control number (post-C1):

| Asset | Expected |
|-------|----------|
| Phone number on WABA | New Cloud API phone entry for `+966 53 313 2601` |
| Phone Number ID | **New** Graph ID ≠ `1260388737156321` |
| WABA | Prefer **no new WABA** (reuse `1520530422625766`) |
| Business Portfolio | Prefer existing CartFlow business (no new BM) |
| App linkage | Same Meta WhatsApp app / ES `config_id` |
| Certificate / registration | Created only when `/register` is later called (not in C1) |

**C1 creates nothing** — design only.

---

## 6) Rollback / cleanup implications

| If live ES later adds the control phone | Cleanup options |
|----------------------------------------|-----------------|
| Phone unused, never registered | Prefer leave as inactive diagnostic asset **or** Meta-side remove only after written authorization |
| Phone registered in a later phase then abandoned | Deregister/delete is **destructive** — require explicit owner approval; never automate |
| Wrong WABA created by mistake | Do **not** delete production WABA; isolate/document; Meta support if needed |
| Env never changed | Rollback of CartFlow runtime = **none** (no codepath switched) |
| Admin control path | Feature-flag or remove routes after experiment; production recovery stays |

**Rule:** Production phone `1260388737156321` is never the cleanup target of this experiment.

---

## 7) Intended later flow (not executed in C1)

```
Fresh Embedded Signup (control admin path)
  → select existing CartFlow business
  → add/verify NEW phone +966533132601
  → obtain new Phone Number ID
  → validate ≠ 1260388737156321
  → validate E.164 match
  → STOP before /register
```

Interpretation matrix (after a future register phase):

| Control `/register` outcome | Likely conclusion |
|----------------------------|-------------------|
| Success | Production failure is **phone-specific** (or aged ES asset class on old ID) |
| Same `100`/`2388001` | Failure likely **WABA / business / app / payment** class |
| Different Meta error | New failure mode — stop and re-diagnose |

---

## 8) Phase gate

| Item | C1 |
|------|----|
| Readiness doc | **This file** |
| Code for control path | **Not started** |
| Live ES | **No** |
| `/register` (any phone) | **No** |
| Env / DB changes | **No** |

---

## STOP

Phase C1 complete. Await authorization before any control Embedded Signup implementation or live Meta click-through.
