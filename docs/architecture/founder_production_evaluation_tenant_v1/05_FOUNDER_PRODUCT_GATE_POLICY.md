# Permanent development policy — Founder Product Gate

From this point forward CartFlow uses three gates:

## LOGIC GATE

**Where:** tests / fixtures / candidate environment / local labs  

**Purpose:** Prove ranking, evidence, COL, CDC, catalog, portfolio, and mission truth contracts.

**Allowed:** `cf_fe_v1_*`, unit tests, screenshots for logic packs, simulation-marked contexts where governed.

**Not sufficient for:** founder product PASS.

## FOUNDER PRODUCT GATE

**Where:** real production runtime + founder evaluation tenant  

**Requirements:**

- `smartreplyai.net`
- `/dashboard`
- Merchant UI V2
- Production API + DB schema
- Authenticated `cf_founder_evaluation` session
- Server-side evaluation feature gate

**Law:** NO FOUNDER PRODUCT PASS OUTSIDE REAL PRODUCTION MERCHANT UI.

## GENERAL RELEASE GATE

**Where:** all production merchants  

**Requirements:**

- Founder production PASS on evaluation tenant
- Explicit ops/general-release control (env or equivalent)
- Normal merchants unchanged until this gate opens

## Anti-patterns (forbidden)

- Treating lab screenshots as founder product pass
- `?preview=1` / frontend-only feature unlocks
- Hardcoding missions in templates for review
- Mock recommendation objects on production paths
- Global admin bypass into evaluation features
- Enabling evaluation features for all merchants “temporarily”
