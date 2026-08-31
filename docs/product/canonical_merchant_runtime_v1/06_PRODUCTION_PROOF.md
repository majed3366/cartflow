# 06 — Production route proof (`90e28b8f`)

Read-only. No deploy. Landing SHA used only to confirm process identity — **not** as Merchant renderer proof.

## Live SHA

`X-CartFlow-Git-Sha` on `GET /` = `90e28b8f142635887df9a78a1024f88946697c0a`  
`X-CartFlow-Landing` = `landing-mobile-visual-correction-v1`

## `/` — not Merchant UI

| Check | Result |
|-------|--------|
| Landing header | present |
| `merchant_ui_v2_home.js` | absent |
| `data-cf-ui=v2` | absent |
| Merchant identity headers | absent |

**Do not use `/` for Merchant Dashboard visual proof.**

## `/dashboard` — Living Store session, no `cf_ui`

| Check | Result |
|-------|--------|
| `data-cf-ui="v2"` | yes |
| `merchant_ui_v2_home.js` | yes |
| `merchant_ui_v2_workspace.js` | yes |
| `home_executive_summary_v1.js` | no |
| `cf2-utility` | yes |
| V1 rail as chrome | no |

**PRODUCTION DASHBOARD PARITY: PASS** (matches canonical V2).

Live SHA does **not** yet emit `X-CartFlow-Merchant-*` or runtime meta (this closure is not deployed). Renderer identity was proven from the HTML document itself.

## `/dashboard?cf_ui=v2`

Same V2 family as default. **PASS.**

## `/dashboard?cf_ui=v1`

| Check | Result |
|-------|--------|
| `home_executive_summary_v1.js` | yes |
| V1 `cf-rail` | yes |
| V2 Home/Workspace painters | no |

**ROLLBACK_ONLY.** Not valid for canonical visual approval.

## `/dev/living-store-home-review`

On live SHA this route **302s to `/dashboard#home`** and sets a Living Store session cookie. It does not render its own template.

`GET /dev/merchant-runtime-identity` = **404** on live SHA (added in this closure, not deployed).

Live bind does **not** yet force `cf_ui_v2=1`. If a leftover V1 cookie exists, the follow-up `/dashboard` can still be V1. That residual is closed in this repo (bind writes `cf_ui_v2=1`).

**LIVING STORE PARITY (live, no V1 cookie): PASS** — same V2 dashboard after bind.  
**LIVING STORE PARITY (live, leftover V1 cookie): documented difference** — closed in this closure, not on `90e28b8f`.

## Until this closure is deployed

Verify Merchant UI with:

`https://smartreplyai.net/dev/living-store-home-review`  
then confirm the document is `/dashboard` with `data-cf-ui="v2"`  
**or** open `/dashboard?cf_ui=v2` after bind.

Never treat landing SHA as renderer proof.
