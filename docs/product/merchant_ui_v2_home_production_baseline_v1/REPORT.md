# Merchant UI V2 — Home Production Baseline Promotion V1

**Status:** VALIDATED  
**Promotion deploy:** `4103274`  
**Visual freeze baseline:** `71cf4e3` (Home Desktop Stage Closure V1 — unchanged)  
**Living Store default URL:** https://smartreplyai.net/dashboard#home

## Objective

Promote approved Merchant UI V2 Home to the **default** production `/dashboard` Home surface. No visual redesign.

## Default UI mode

- Default: **V2 ON** (`DEFAULT_MERCHANT_UI_V2 = True`)
- Merchants no longer need `?cf_ui=v2`
- Probe confirmed `hasCfUiQuery: false` on desktop / laptop / mobile

## Rollback path (preserved & verified)

| Method | How |
|--------|-----|
| Query | `/dashboard?cf_ui=v1` |
| Cookie | `cf_ui_v2=0` |
| Env | `CARTFLOW_MERCHANT_UI_V2=0` |
| Dev route | `/dev/merchant-ui-v1` |

Rollback smoke: `?cf_ui=v1` served `merchant_frame_v1` without V2 Home CSS.

## Confirmations

- Deployed SHA: **`4103274`**
- Default UI mode: **V2**
- Living Store validated **without** `cf_ui` query (desktop / laptop / mobile)
- Rollback path verified
- No visual drift: `data-cf2="home-stage-closure-v1"` present
- No legacy CSS / no mixed V1+V2 styles
- No overflow
- Home scene + stance + monitor present; navigation Home active

## Evidence

| File | Role |
|------|------|
| [desktop_production_home.png](desktop_production_home.png) | Desktop default Home |
| [laptop_production_home.png](laptop_production_home.png) | Laptop default Home |
| [mobile_production_home.png](mobile_production_home.png) | Mobile default Home |
| [production_home_closeup.png](production_home_closeup.png) | Board close-up |
| [production_probe.json](production_probe.json) | Gate probe |

## STOP

Production validation complete. Do **not** start Decision Workspace Final Product Composition V1 until tasked.
