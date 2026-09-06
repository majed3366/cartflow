# Live Reality Lab V1 — Tenant Identity

## Ownership

| Field | Value |
|-------|--------|
| store_slug / zid_store_id | `cf_live_reality_lab` |
| MerchantUser email | `reality.lab@cartflow.local` |
| integration_source | `live_reality_lab_v1` |
| Display name | CartFlow Live Reality Lab |
| WhatsApp recovery | Forced `False` on ensure |
| Bootstrap password | In `ensure_v1.py` — rotate before production use |

## Isolation

- Exact allowlist size **1** (no wildcards).
- Lab control APIs require authenticated session resolving to this slug.
- Client `store_slug` is never trusted for apply/reset/verify.
- Cleanup deletes only:
  - `CartRecoveryReason` where `store_slug=cf_live_reality_lab` AND `source=live_reality_lab_v1`
  - `AbandonedCart` where `store_id` is lab store AND `zid_cart_id` prefix `lrl_v1_`
  - `CommercialDecisionCommitment` where `store_slug=cf_live_reality_lab`

## Authority map (visual truth)

| Tenant | Role |
|--------|------|
| **cf_live_reality_lab** | **CANONICAL LIVE PRODUCT VALIDATION** |
| cf_founder_evaluation | Legacy founder production evaluation (keep isolated) |
| cf_fe_v1_* | Test-only fixtures |
| demo / Living Store | Not canonical founder product truth |

## Same product path

Lab consumes unchanged: COL · OGL · mission_catalog_v1 · CDC · mission_portfolio_v1 · Priority Surface Contract · Home/Workspace Merchant UI V2.
