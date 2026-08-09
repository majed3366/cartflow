# Embedded Signup Recovery — Phase 2B Evidence

**Date (UTC):** 2026-08-09  
**Deploy target:** Living Store `https://smartreplyai.net`  
**Phase:** 2B — Minimal Embedded Signup Recovery  
**STOP:** Do **not** call `POST /{phone-number-id}/register`

---

## Targets (hard assert)

| Asset | Required ID |
|-------|-------------|
| WABA | `1520530422625766` |
| Phone Number ID | `1260388737156321` |

Mismatch → **ABORT** (HTTP 409). No exchange continuation, no register, no asset create/delete.

---

## What shipped

| Surface | Path |
|---------|------|
| Admin page | `GET /admin/whatsapp/embedded-signup-recovery` |
| Config API | `GET /admin/api/whatsapp/embedded-signup-recovery/config` |
| Complete API | `POST /admin/api/whatsapp/embedded-signup-recovery/complete` |
| Service | `services/admin_whatsapp_embedded_signup_recovery_v1.py` |
| Client | `static/admin_whatsapp_es_recovery.js` |
| Tests | `tests/test_admin_whatsapp_embedded_signup_recovery_v1.py` |

### Behavior

1. Admin-only (CartFlow admin session cookie).  
2. Loads Facebook JS SDK; `FB.init({ appId })` from env.  
3. `FB.login` with `config_id` + `response_type=code`.  
4. Captures `WA_EMBEDDED_SIGNUP` (`waba_id`, `phone_number_id`) + auth `code`.  
5. Server **HARD ASSERT** IDs → exchange code via Graph `oauth/access_token`.  
6. Ephemeral token used only for optional phone confirm; **not persisted**, **not logged**, **not returned**.  
7. `register_called: false` always.

### Env (Railway — names only)

- `META_WHATSAPP_APP_ID`  
- `META_WHATSAPP_CONFIGURATION_ID`  
- `META_WHATSAPP_APP_SECRET`  

App Secret must **never** appear in git, logs, UI, or evidence JSON.

---

## Automated test evidence

```
9 passed — tests/test_admin_whatsapp_embedded_signup_recovery_v1.py
```

Covers: assert OK / WABA mismatch abort / phone mismatch abort / public config redaction / success path without token leak / route auth.

---

## Runtime evidence checklist

Fill after Living Store deploy + owner Meta click-through:

| Gate | Evidence | Status |
|------|----------|--------|
| Recovery page reachable (admin) | screenshot / HTTP 200 | pending deploy probe |
| Config API returns App ID + Configuration ID (no secret) | `production_probe.json` | pending |
| Facebook SDK initializes | UI “Facebook SDK: ready” | pending |
| Embedded Signup opens | Meta dialog/popup | **requires owner Facebook session** |
| Meta authorization completes | `WA_EMBEDDED_SIGNUP` FINISH + code | **requires owner** |
| Existing WABA confirmed | `1520530422625766` | **requires owner** |
| Existing phone confirmed | `1260388737156321` | **requires owner** |
| Fresh authorization obtained | `fresh_authorization_obtained: true` | **requires owner** |
| No duplicate WABA/phone | response flags false | asserted in code |
| No delete/deregister | response flags false | asserted in code |
| `/register` not called | `register_called: false` | asserted in code |

---

## Owner action to close live success gate

1. Open `https://smartreplyai.net/admin/whatsapp/embedded-signup-recovery` (admin login).  
2. Confirm Ready = yes.  
3. Click **Start Embedded Signup**.  
4. Complete Meta UI selecting the **existing** CartFlow WABA + phone (do not create new assets).  
5. Confirm Result JSON shows `ok: true`, matching IDs, `register_called: false`.  
6. **STOP** — do not proceed to Phase 3 `/register` until separately authorized.

---

## Security note

If `META_WHATSAPP_APP_SECRET` was pasted into chat or tickets, **rotate it** in Meta App Dashboard → Settings → Basic, then update Railway. This evidence pack does not store the secret.
