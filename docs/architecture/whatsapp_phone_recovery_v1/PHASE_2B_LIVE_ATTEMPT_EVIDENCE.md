# Phase 2B — Single Live Attempt Evidence

**Date (UTC):** 2026-08-09  
**Deploy SHA:** `5e1cea2` (Living Store confirmed)  
**Authorized:** ONE live Embedded Signup recovery attempt  
**Outcome:** **STOPPED — blocked before launch**

---

## Result

| Field | Value |
|-------|--------|
| Attempt started | No |
| FB.login opened | No |
| OAuth code obtained | No |
| Browser `WA_EMBEDDED_SIGNUP` | N/A (not reached) |
| Shared-WABA fallback | N/A (not reached) |
| `/register` called | **false** |
| Assets deleted/created | **No** |

### Error category

`admin_session_unavailable`

### Details

| Item | Evidence |
|------|----------|
| Target URL | `https://smartreplyai.net/admin/whatsapp/embedded-signup-recovery` |
| Observed redirect | `https://smartreplyai.net/admin/operations/login?next=/admin/whatsapp/embedded-signup-recovery` |
| Graph endpoint involved | None |
| HTTP status (admin page) | Login gate (HTML), not Graph |
| Meta error code/subcode | None |
| Browser event emitted | No |
| `debug_token` succeeded | Not reached |
| Target WABA in granular scopes | Not reached |
| Phone enumeration succeeded | Not reached |
| `CARTFLOW_ADMIN_PASSWORD` in agent env | **Missing** |

Hard asserts and `/register` block were not exercised because the attempt could not enter the recovery surface.

---

## Why STOP (no retry)

Per authorization: **one** live attempt only; on failure **STOP immediately**.

This session cannot complete admin login without operator credentials. Facebook Embedded Signup also requires interactive Meta user authorization after admin access. No second attempt was made. No Meta configuration was changed. No `/register`.

---

## Required to complete the single live attempt

Operator must do **one** of:

1. Take over the open browser tab, enter admin password, open recovery page, click **Start Embedded Signup**, complete Meta once, then paste the Result JSON (tokens already redacted by UI), **or**  
2. Provide `CARTFLOW_ADMIN_PASSWORD` in the agent/shell environment for a single orchestrated run (password must not be committed to git).

Expected success after that (exact IDs required):

```json
{
  "ok": true,
  "resolution_source": "browser_session",
  "waba_id": "1520530422625766",
  "phone_number_id": "1260388737156321",
  "register_called": false
}
```

or

```json
{
  "ok": true,
  "resolution_source": "server_shared_waba_fallback",
  "waba_id": "1520530422625766",
  "phone_number_id": "1260388737156321",
  "register_called": false
}
```

Note: deployed browser-path source string is `browser_session` (not `browser_session_event`).

---

## STOP

Single live attempt **not executed** due to admin auth blocker. Awaiting operator takeover or env password for a new authorized attempt.
