# Merchant Recovery Policy Composition + Packages Experience V4 — Report

**Base SHA:** `47826f97a87e53b30db133bafd0fa548cc737fbe`  
**Candidate SHA:** `(see git HEAD after freeze)`  
**Direct parent:** `47826f97a87e53b30db133bafd0fa548cc737fbe`  
**Deploy:** NOT performed

## Recovery Policy

| Check | Result |
|-------|--------|
| Composition | Summary → reason picker → one detail → stage flow → message/delay/save |
| Canonical reasons | 7 (`price` `shipping` `warranty` `thinking` `quality` `delivery` `other`) |
| Long theory banners in V2 | 0 (ownership/seq intro suppressed; timing in `<details>`) |
| One-reason-at-a-time | PASS |
| Stage flow truth-driven | YES (enabled vs disabled from `message_count`) |
| Legacy shell merchant-reachable | NO |

## Packages

| Check | Result |
|-------|--------|
| Source | `GET /api/merchant/plans-catalog` |
| Authoritative packages | 3 (`starter` `growth` `pro`) |
| Pricing | PARTIAL catalog SAR labels (read-only footnote) |
| Upgrade/downgrade | BLOCKED_BY_COMMERCIAL_CONTRACT |
| Fake commercial claims | 0 |
| Account entry | Drawer → الباقات → `#packages` |

## Evidence

`docs/product/merchant_recovery_packages_composition_v4/evidence/`
