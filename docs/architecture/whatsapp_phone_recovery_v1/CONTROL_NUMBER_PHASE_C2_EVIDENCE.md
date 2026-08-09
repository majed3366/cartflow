# Control Number Test — Phase C2 Evidence

**Date (UTC):** 2026-08-09  
**Phase:** C2 — Isolated Embedded Signup surface  
**Status:** **Implementation / deploy readiness** — live ES **not** executed by agent  

---

## Purpose

Build a separate admin-only Embedded Signup path to add/authorize clean control phone  
`+966 53 313 2601` on existing WABA `1520530422625766`, capture the **new** Phone Number ID,  
and **STOP before `/register`**.

Production phone `1260388737156321` (`+966 57 970 6669`) must remain untouched.

---

## Delivered surface

| Item | Value |
|------|--------|
| Admin page | `GET /admin/whatsapp/control-number-es` |
| Config API | `GET /admin/api/whatsapp/control-number-es/config` |
| Complete API | `POST /admin/api/whatsapp/control-number-es/complete` |
| Service | `services/admin_whatsapp_control_number_es_v1.py` |
| UI | `templates/admin_whatsapp_control_number_es.html` |
| JS | `static/admin_whatsapp_control_number_es.js` |
| Marker | `control-number-es-v1` |
| Tests | `tests/test_admin_whatsapp_control_number_es_v1.py` |
| Link from | `/admin/whatsapp` → “Control Number ES (C2)” |

---

## Isolation (verified by design + tests)

| Must not change | Status |
|-----------------|--------|
| `WHATSAPP_PHONE_NUMBER_ID` | Never written by this path (`env_mutated: false`) |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | Never written |
| Production WhatsApp credentials | Ephemeral ES token only; never persisted |
| Merchant DB state | No DB writes (`db_mutated: false`) |
| Production recovery path | Unchanged (`/admin/whatsapp/embedded-signup-recovery`) |
| Register allowlist | Still `{"1260388737156321"}` only — control ID not added |

Reuses Meta App ID / Configuration ID / App Secret for OAuth only (same Railway secrets as Phase 2B).

---

## Hard assertions

| Rule | Behavior |
|------|----------|
| WABA == `1520530422625766` | Else **ABORT** (`waba_mismatch_or_new_waba`) |
| Normalized E.164 == `+966533132601` | Else **ABORT** (`phone_e164_mismatch`) |
| Phone Number ID ≠ `1260388737156321` | Else **ABORT** (`production_phone_id_appeared`) |
| New WABA created by Meta | **ABORT** (no owner-approval bypass in C2) |
| `/register` | Never called (`register_called: false`, `register_allowed: false`) |

Client pre-checks mirror WABA + production-phone-id aborts; server is authoritative.

---

## Success shape (sanitized)

```json
{
  "ok": true,
  "control_phone": "+966533132601",
  "waba_id": "1520530422625766",
  "new_phone_number_id": "<new id>",
  "production_phone_untouched": true,
  "register_called": false
}
```

Additional safe fields may include `resolution_source`, `display_phone_normalized`, `recovery_marker`, `phase`, isolation flags. Tokens/secrets never returned.

---

## Resolution paths

1. **Browser session** — `WA_EMBEDDED_SIGNUP` provides WABA + Phone Number ID → assert → ephemeral code exchange → Graph confirm display E.164 → STOP.  
2. **Fallback** — session IDs missing → exchange → list `/{waba}/phone_numbers` → match control E.164 → reject production ID → STOP.

---

## Operator flow (manual — not run in C2)

1. Open `https://smartreplyai.net/admin/whatsapp/control-number-es` (admin login).  
2. Confirm config Ready.  
3. Start Control Embedded Signup.  
4. Select existing CartFlow business + WABA `1520530422625766`.  
5. Add/verify `+966 53 313 2601`.  
6. Confirm sanitized success JSON with `new_phone_number_id` ≠ production.  
7. **STOP** — do not register, do not change env.

---

## Unit tests

```
pytest tests/test_admin_whatsapp_control_number_es_v1.py
```

Covers: E.164 normalize, assert abort (production ID / wrong WABA / wrong E.164), success sanitization, fallback lookup, admin auth, register allowlist unchanged.

---

## Live Meta status

| Action | C2 |
|--------|----|
| Live Embedded Signup click-through | **Not executed** |
| `/register` (any phone) | **Not called** |
| Production phone modify/delete/deregister | **Not done** |
| Env / runtime switch to control phone | **Not done** |

---

## STOP

Phase C2 implementation ready for deploy. Await explicit authorization before any live control Embedded Signup attempt.
