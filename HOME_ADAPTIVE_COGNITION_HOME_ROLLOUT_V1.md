# Adaptive Cognition V2 — Merchant Home Production Rollout

**Date (UTC):** 2026-07-18  
**Status:** Deployed for Product Experience Review  

## What changed

Merchant Home (`/dashboard#home`) consumes Adaptive Cognition Engine V2 for **section sequencing only**.

| Changed | Unchanged |
|---------|-----------|
| Presentation order of existing Home sections | Card/section HTML components |
| Session lock + governed re-eval on summary | Constitution / Inventory / Surface Contract |
| `adaptive_cognition_v1` metadata on home payload | Business truth content |

## Consumer wiring

| Layer | File |
|-------|------|
| Bridge | `services/home_adaptive_cognition_home_bridge_v1.py` |
| Summary attach | `finalize_dashboard_summary_payload` |
| Request context | `api_dashboard_summary` query: `acf_trigger`, `acf_session`, `acf_fixture` |
| Paint order | `static/merchant_dashboard_home_v1.js` |
| Fetch + return trigger | `static/merchant_dashboard_lazy.js`, `static/merchant_app.js` |

## Production URL

https://smartreplyai.net/dashboard#home

### Product path fixtures (sequence validation)

Append query before hash:

| Path | URL |
|------|-----|
| VIP | `https://smartreplyai.net/dashboard?acf_fixture=vip#home` |
| Healthy | `https://smartreplyai.net/dashboard?acf_fixture=healthy#home` |
| Operational | `https://smartreplyai.net/dashboard?acf_fixture=operational#home` |
| Attention | `https://smartreplyai.net/dashboard?acf_fixture=attention#home` |
| Pending | `https://smartreplyai.net/dashboard?acf_fixture=pending#home` |
| Insufficient | `https://smartreplyai.net/dashboard?acf_fixture=insufficient#home` |

Fixture overrides **router sequencing only**; live section content remains store truth.

Root element exposes `data-acf-path` / `data-acf-label` for verification.

## Session stability

- First visit: `acf_trigger=session_start`
- Subsequent summary polls: `view_stable` (no reshuffle)
- Full reload: `full_page_refresh`
- Return from Carts/Comms/Settings: `return_from_surface`
- `periodic_poll` rejected

## STOP

Await Product Experience Review.  
Do not begin Wireframe.  
No further Home redesign in this rollout.
