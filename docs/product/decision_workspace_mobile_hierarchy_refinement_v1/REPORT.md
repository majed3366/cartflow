# Decision Workspace — Mobile Hierarchy Refinement V1

**Status:** Living Store evidence captured — **STOP for real-device visual review**  
**Deploy:** `7921135`  
**URL:** https://smartreplyai.net/dashboard#workspace  
**Shell:** Protected (`shell-integration-v1`) — unchanged  
**Marker:** `data-cf2-mobile-hierarchy="v1"` / class `cf2-ws--mobile-hierarchy-v1`

## Objective

Reduce first-viewport density on **mobile only** so the decision owns the page, with clearer breathing and quieter support layers.

## What changed

Mobile (`max-width: 1023px`) content-stage CSS only:

| Layer | Change |
|-------|--------|
| Page question | Smaller, muted — orientation, not conclusion |
| Primary decision | Strongest type; title ordered above status |
| Evidence status | Metadata under decision (not a second headline) |
| Evidence / CIM | Quieter route spine + smaller density field |
| Meaning | Lower weight than decision + evidence |
| CartFlow confirmation | Confirmation strip, not competing headline |
| Action | Pulled closer to confirmation |
| بعده | Secondary opacity / type |

**Unchanged:** shell, nav, APIs, projection, decision semantics, Commerce Objects presence, Living Route identity, desktop composition intent.

## Gates

All `true` in `production_probe.json` / `mobile_overflow_probe.json` (see `REGRESSION_RESULTS.md`).

## STOP

No PASS. No freeze. Await real-device visual review.
