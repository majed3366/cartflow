# Phase 2B — OAuth redirect_uri mismatch fix (Meta 100 / 36008)

**Date (UTC):** 2026-08-09  
**Status:** Implemented + unit-validated. Deployed for live verification.  
**Deploy SHA:** `7b624e5` (`main`)  
**Live retry:** NOT performed by agent — STOP after deploy.  
**`/register`:** not called  

---

## Live failure (pre-fix)

| Field | Value |
|-------|--------|
| `meta_error_code` | `100` |
| `meta_error_subcode` | `36008` |
| `meta_error_type` | `OAuthException` |
| Message | Error validating verification code. Please make sure your `redirect_uri` is identical to the one you used in the OAuth dialog request |
| `token_obtained` | `false` |
| `/register` | not called |
| Assets | none created/deleted/deregistered |

FB.login opened; user authorized; authorization code returned; **server code→token exchange failed**.

---

## Audit — what each side used

### 1) Browser / FB.login (authorization)

- Client uses Facebook JS SDK `FB.login` with:
  - `response_type: "code"`
  - `override_default_response_type: true`
  - `config_id: <META_WHATSAPP_CONFIGURATION_ID>`
- **No custom `redirect_uri` is passed to `FB.login`.**
- Meta’s dialog therefore binds its **own** popup callback `redirect_uri` (typically an `xd_arbiter` / staticxx Facebook URL embedded in the dialog query string).
- Spawn page (admin recovery UI) is **not** the OAuth dialog redirect — guessing it (or `login_success.html`) causes 36008.

### 2) Server (code → access_token) — before fix

- Exchange hit `GET /{graph-version}/oauth/access_token` with `client_id`, `client_secret`, `code`.
- `redirect_uri` was **omitted** (no guessed page URL).
- Live still returned **100 / 36008**, so for this app/dialog Meta required the **exact dialog `redirect_uri`**, not omission alone.

### 3) Character-level mismatch diagnosis

| Component | Dialog (auth) | Prior exchange | Match? |
|-----------|---------------|----------------|--------|
| Custom app callback | Meta-owned (xd_arbiter-style) | omitted / none | No — Meta expected dialog URI |
| Spawn page host/path | admin ES recovery page | never sent as exchange URI | N/A (correctly not guessed) |
| Trailing slash / query / port | dialog-specific | N/A when omitted | Fail closed as 36008 |

**Rule implemented:** exchange `redirect_uri` MUST be character-for-character identical to the dialog’s `redirect_uri` when captured; otherwise omit (never guess).

---

## Fix

| Layer | Change |
|-------|--------|
| Helper | `services/oauth_redirect_uri_v1.py` — exact match, safe host/path diag, `build_token_exchange_params` (`dialog_exact` \| `omit`) |
| Service | `_exchange_code_internal` accepts `dialog_redirect_uri` + `spawn_page_uri`; attaches `oauth_exchange` diag; never uses spawn page as exchange URI |
| Route | `POST …/complete` forwards `dialog_redirect_uri` / `spawn_page_uri` from JSON |
| Client | Brief `window.open` intercept around `FB.login` captures dialog query `redirect_uri` (or `fallback_redirect_uri`); sends both URIs on complete |
| Tests | Exact match; trailing slash / scheme / host / query mismatch; omit vs dialog_exact passthrough |

### Exchange policy

```
if dialog_redirect_uri captured:
    params.redirect_uri = dialog_redirect_uri  # exact, no normalize
    mode = dialog_exact
else:
    # do NOT invent page URL / login_success.html
    omit redirect_uri
    mode = omit
```

### Safe diagnostics (`oauth_exchange`) — never logs code / token / secret

- `redirect_uri_mode`: `dialog_exact` \| `omit`
- `dialog_redirect`: `{ scheme, host, path, trailing_slash, query_keys, … }`
- `spawn_page`: same shape (diag only)
- `auth_exchange_compare.exact_match`
- `dialog_vs_spawn` (shows spawn ≠ dialog when both present)

---

## Expected live gate (manual, after deploy)

1. OAuth code returned  
2. Code exchange succeeds → `token_obtained = true`  
3. Existing path may continue: `debug_token` → target WABA assert → target Phone Number ID assert  
4. **STOP before `/register`**

Inspect response `oauth_exchange.redirect_uri_mode` and `auth_exchange_compare.exact_match` if exchange still fails.

---

## Out of scope (unchanged)

- Meta permissions / `business_management`
- `/register`
- Asset create/delete/deregister
- Automatic live ES retry by agent

---

## Verification

- Unit: `tests/test_oauth_redirect_uri_v1.py`, extended recovery exchange tests  
- Deploy: `7b624e5` → `main` (Living Store); **no agent live attempt**
