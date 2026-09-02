# Merchant Recovery Policy Composition + Packages Experience V4

**Status:** CANDIDATE — deploy NOT authorized  
**Base:** `47826f97a87e53b30db133bafd0fa548cc737fbe`  
**Cache:** `recv4` / `pkgv4`

## Scope

1. Rebuild Settings → سياسة الاسترجاع as a product workflow (summary → one reason → stage flow → edit/save).
2. Account → الباقات destination from `/api/merchant/plans-catalog` only (no fake checkout).

## Commercial audit (summary)

| Field | Class |
|-------|--------|
| Plan names `starter`/`growth`/`pro` | AUTHORITATIVE |
| Subscription state | AUTHORITATIVE |
| Catalog SAR prices / feature bullets | PARTIAL (read-only catalog API) |
| Upgrade/downgrade runtime | AUTHORITATIVE as blocked |

## Evidence

`evidence/` — 390 RTL + 1280 desktop.
