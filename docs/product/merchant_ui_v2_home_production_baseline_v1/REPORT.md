# Merchant UI V2 — Home Production Baseline Promotion V1

**Status:** pending deploy validation  
**Visual freeze baseline:** `71cf4e3` (Home Desktop Stage Closure V1)  
**Living Store default URL:** https://smartreplyai.net/dashboard#home

## Objective

Promote approved Merchant UI V2 Home to the **default** production `/dashboard` Home surface. No visual redesign.

## Default UI mode

- Default: **V2 ON** (`DEFAULT_MERCHANT_UI_V2 = True`)
- Merchants no longer need `?cf_ui=v2`

## Rollback path (preserved)

| Method | How |
|--------|-----|
| Query | `/dashboard?cf_ui=v1` |
| Cookie | `cf_ui_v2=0` |
| Env | `CARTFLOW_MERCHANT_UI_V2=0` |
| Dev route | `/dev/merchant-ui-v1` |

## Confirmations (fill after Living Store validation)

- Deployed SHA: _pending_
- Default UI mode: V2
- Living Store validated without `cf_ui` query: _pending_
- Rollback path verified: _pending_
- No visual drift from frozen Home (`home-stage-closure-v1`): _pending_
- No behavioral regression / no legacy CSS mix: _pending_

## Evidence

| File | Role |
|------|------|
| [desktop_production_home.png](desktop_production_home.png) | Desktop default Home |
| [laptop_production_home.png](laptop_production_home.png) | Laptop default Home |
| [mobile_production_home.png](mobile_production_home.png) | Mobile default Home |
| [production_home_closeup.png](production_home_closeup.png) | Board close-up |
| [production_probe.json](production_probe.json) | Gate probe |

## STOP

Do not start Decision Workspace Final Product Composition V1.
