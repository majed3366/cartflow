# Zid OAuth Partner Checklist v1

**Date (UTC):** 2026-06-01  
**Scope:** Store connection OAuth only (`/api/merchant/store-connection/zid/connect` → `/auth/callback`).

## Authorize URL requirements

CartFlow builds:

```http
GET https://oauth.zid.sa/oauth/authorize
  ?client_id=…
  &redirect_uri=https://smartreplyai.net/auth/callback
  &response_type=code
  &scope=abandoned_carts.read orders.read
  &state=…
```

| Parameter | Requirement |
|-----------|-------------|
| `response_type` | Must be `code` |
| `client_id` | Partner Dashboard Client ID |
| `redirect_uri` | Must **exactly** match **Callback URL** in Partner Dashboard (https, no trailing slash) |
| `scope` | Space-separated; must be subset of **Application Scopes** enabled for the app |
| `state` | Signed CartFlow merchant/store binding |

Override scopes via `ZID_OAUTH_SCOPE`. Set `ZID_OAUTH_SCOPE=` (empty) to omit scope (debug only).

## Partner Dashboard URLs (do not confuse)

| Dashboard field | CartFlow route | Role |
|-----------------|----------------|------|
| **Callback URL** | `https://…/auth/callback` | OAuth `redirect_uri` — receives `?code=&state=` |
| **Redirection URL** | `https://…/auth/zid` | App Market “Install” entry (optional for dashboard-initiated connect) |
| **Application URL** | `https://…/` or marketing site | Merchant-facing app home |

If Callback URL ≠ `redirect_uri`, Zid login succeeds but **no callback** is issued.

## Draft / unpublished apps

Per [Zid Create your First App](https://docs.zid.sa/create-first-app) and [Test your application](https://help-partner.zid.sa/en/articles/8645309-test-your-application):

- **Draft apps can complete OAuth** on a **development store** after scopes and URLs are configured.
- **Unpublished** apps are not listed in the public App Market but OAuth still works for test merchants when the authorize URL is opened directly (CartFlow dashboard flow).
- **Missing Application Scopes** in the dashboard → consent may fail or redirect to Zid dashboard without issuing a code.
- **Not approved / rejected scopes** block production merchants until Zid review passes.

## Manual verification

1. Trigger connect → copy `authorize_url_safe` from `[ZID OAUTH START]` logs.
2. Replace `[REDACTED]` with real Client ID (from dashboard only — never commit).
3. Open in browser (logged out of Zid first).
4. **Expected:** login → **permission/consent** screen listing scopes → redirect to `https://smartreplyai.net/auth/callback?code=…`.
5. **Failure signal:** login → Zid merchant dashboard/orders with **no** redirect to CartFlow → OAuth authorization did not complete (check callback URL, scopes, app status).

## Log markers (success path)

```
[ZID OAUTH START]
[ZID OAUTH CALLBACK HIT]
[ZID OAUTH TOKEN EXCHANGE] success=true
[ZID OAUTH STORE LINKED]
```

Browser lands on `/dashboard#settings?store_connected=1`.
