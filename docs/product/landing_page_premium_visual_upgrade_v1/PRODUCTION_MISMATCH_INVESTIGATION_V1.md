# Landing Premium Production Mismatch — Investigation V1

**Date (UTC):** 2026-07-30  
**Official URL:** https://smartreplyai.net/  
**Repo tip (`origin/main`):** `2275b3f` (includes merge `ef16e52` / feature `7d243fb`)

## Verdict

**No wrong service / no old template on the live origin.**

Independent probes (curl, Python, Cursor browser) against `GET https://smartreplyai.net/` return the **Premium Visual Upgrade V1** page:

| Check | Result |
|-------|--------|
| Old headline `ليس مجرد رسائل واتساب` | **Absent** |
| New headline `استعِد ما فات` | **Present** |
| `.cf-browser--hero` mockup markup | **Present** |
| `landing_v1/dashboard.png` | **Present + loads** (natural 1440×900) |
| CSS `Premium Visual Upgrade V1` marker | **Present** |
| CTAs `/signup` `/login` | **Present** |
| Server | `railway-hikari` edge `cdg1` |
| Service health | `GET /health` → `{"ok": true, "service": "cartflow"}` |
| `www.smartreplyai.net` | **Does not resolve** (apex only) |

## Root cause of the reported “old page”

1. **Live origin already serves Premium** — HTML/CSS/images match `feat/landing-premium-visual-upgrade-v1` / merge `ef16e52`.
2. The quoted old hero was removed from `templates/cartflow_landing.html` in **`0e7157c`** (Landing Page Production V1) and is **not** in current `main`.
3. Response HTML previously had **no `Cache-Control`**, so a **stale browser cache** (or an old tab/screenshot) can still show the pre–Production-V1 page locally while origin is correct.

## Not the cause

- Alternate `www` host (does not DNS-resolve)
- Separate settings-driven landing template still mounted on `GET /` (`routes/public.py` → `cartflow_landing.html` only)
- CDN `CF-RAY` / Cloudflare HTML cache (not present on responses)
- Failed Railway merge of Premium (markers + CSS comment prove Premium assets)

## Hardening shipped after investigation

`routes/public.py` `GET /` now sets:

- `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`
- `X-CartFlow-Git-Sha: <RAILWAY_GIT_COMMIT_SHA or equivalent>`
- `X-CartFlow-Landing: premium-visual-upgrade-v1`

No IA/copy/visual redesign.

## How to verify after deploy

```bash
curl -sI "https://smartreplyai.net/" | findstr /I "X-CartFlow Cache-Control"
curl -s "https://smartreplyai.net/" | findstr /I "cf-browser--hero landing_v1/dashboard"
```

Hard refresh / private window must show Premium hero (browser mockup + dashboard), not the old WhatsApp-settings story page.
