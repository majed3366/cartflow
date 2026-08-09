# Phase 2B — Server-Side Shared WABA Fallback

**Date (UTC):** 2026-08-09  
**Status:** Implemented (unit-validated). Live Meta retry not required for this task.  
**`/register`:** not called  

---

## Objective

When Facebook Login + OAuth code exchange succeed but the browser `WA_EMBEDDED_SIGNUP` session event is missing, resolve the **existing** CartFlow WABA/phone via Meta’s shared-WABA / token-debug path — without creating assets or calling `/register`.

---

## What changed

| Layer | Change |
|-------|--------|
| Service | `resolve_shared_waba_fallback()` — `debug_token` → exact WABA assert → `/{waba}/phone_numbers` → exact phone assert; optional `/{business}/client_whatsapp_business_accounts` |
| Complete API | Accepts `allow_shared_waba_fallback` when session IDs are empty |
| Client | After session wait timeout, calls complete with fallback flag (listener kept; mismatch still aborts) |
| Browser path | Unchanged hard-assert when session IDs are present |

Success shape:

```json
{
  "ok": true,
  "resolution_source": "server_shared_waba_fallback",
  "waba_id": "1520530422625766",
  "phone_number_id": "1260388737156321",
  "register_called": false
}
```

Stop errors:

- `target_waba_not_shared`
- `target_phone_not_confirmed`

Wrong browser IDs still abort with `asset_assertion_failed` — fallback is **not** used to override a mismatch.

---

## Resolution algorithm

1. Exchange authorization code → ephemeral token (never logged/returned).  
2. `GET /debug_token?input_token=<es_token>` authenticated with app token `APP_ID|APP_SECRET`.  
3. Inspect `granular_scopes` for `whatsapp_business_*` `target_ids`.  
4. Require exact WABA `1520530422625766`.  
5. If not in granular scopes and partner Business Portfolio ID is known (`META_BUSINESS_PORTFOLIO_ID` / aliases, or session `business_id` hint):  
   `GET /{BUSINESS_ID}/client_whatsapp_business_accounts` (platform system token preferred, else ES token).  
6. If target WABA still absent → `target_waba_not_shared`.  
7. `GET /1520530422625766/phone_numbers` with ES token.  
8. Require exact phone `1260388737156321` else `target_phone_not_confirmed`.  
9. Return success with `resolution_source: server_shared_waba_fallback`.  

Tokens are discarded after the request path. No persistence.

---

## Is `business_management` required for this fallback?

### Current Login for Business configuration (owner-reported)

Selected:

- `whatsapp_business_management`
- `whatsapp_business_messaging`

Not selected:

- `business_management`

### Meta documentation (relevant)

| Capability | Primary permission cited by Meta |
|------------|----------------------------------|
| Embedded Signup Cloud API messaging/management | `whatsapp_business_management`, `whatsapp_business_messaging` |
| Get shared WABA ID via `debug_token` granular scopes | Works off scopes granted on the ES token — typically `whatsapp_business_management` target_ids |
| `/{business-id}/client_whatsapp_business_accounts` | Documented under manage-accounts as using **`whatsapp_business_management`** (Advanced access); called with partner system user token |
| Solution Partner credit-line sharing | **`business_management`** (+ Admin/Financial Editor on partner portfolio) |

### CartFlow-specific conclusion

**Do not change Meta configuration yet solely for this fallback.**

For our recovery path, the primary resolver is **`debug_token` → granular `whatsapp_business_management` target_ids → WABA phone list**. That path does **not** require `business_management` according to Meta’s shared-WABA-via-token guidance.

`business_management` becomes relevant if:

1. `client_whatsapp_business_accounts` is needed because granular scopes omit the WABA, **and**  
2. Graph returns a permission error that explicitly requires `business_management` to read the Business node / shared clients edge.

Optional env to enable the secondary list path: `META_BUSINESS_PORTFOLIO_ID` (CartFlow partner Business Manager ID).

**Recommendation:** Keep current permissions for the next authorized attempt. Only add Advanced Access to `business_management` if runtime evidence shows `client_whatsapp_business_accounts` (or Business edge resolution) failing with a `business_management` permission error after `debug_token` also fails to surface the target WABA.

---

## Tests

```
pytest tests/test_admin_whatsapp_embedded_signup_recovery_v1.py
```

Covers:

- Browser path success + no token leak  
- Mismatch aborts before exchange  
- Fallback success → exact IDs + `server_shared_waba_fallback`  
- `target_waba_not_shared`  
- `target_phone_not_confirmed`  
- Missing IDs without fallback flag → `missing_session_asset_ids`  
- Route auth / config redaction  

---

## Safety

| Rule | Status |
|------|--------|
| No `/register` | Enforced (`register_called: false`) |
| No asset create/delete/deregister | Enforced |
| Exact WABA/phone only | Enforced |
| Browser listener retained | Yes |
| Browser mismatch not weakened | Yes |
| Tokens never logged/returned | Yes |

---

## STOP

Implementation + read-only/unit validation complete.  

Do **not** call `/register`.  
Await review / authorized live attempt with the new fallback.
