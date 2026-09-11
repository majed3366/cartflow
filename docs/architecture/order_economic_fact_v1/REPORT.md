# Order Economic Fact V1 — Report

**Date (UTC):** 2026-09-11  
**Status:** AUTHORIZED CONTRACT IMPLEMENTATION + TESTS  
**Deploy:** NO

## IMPLEMENTATION STATUS

Implemented. Sibling owner `OrderEconomicFact` persists fail-closed paid-order money after authoritative `PLATFORM_PAID` Purchase Truth. Tests cover the failure matrix. Not deployed. Not on the merchant dashboard. Level 3 still closed.

## CANONICAL OWNER

`OrderEconomicFact` (`models.py`). Service package `services/order_economic_fact_v1/`.

## TABLE / STORAGE OWNER

`order_economic_facts`  
DDL: Alembic `k2l3m4n5o6p7` + `schema_order_economic_fact_v1.ensure_order_economic_fact_schema` for SQLite tests.

## GRAIN

`(store_slug, external_order_id, truth_version)`  
`truth_version = oef_v1`  
Canonical paid-order count uses `(store_slug, external_order_id)`, not recovery_key row count.

## ZID PAID AUTHORITY

`payment_status == paid` AND `payment_summary.paid_amount > 0` AND known currency.  
`order_total` / `transaction_amount` / `remaining_amount` are supporting reconciliation only.

## PAID_AMOUNT SOURCE

Zid `payment_summary.paid_amount` via `integrations/zid_order_economic_v1.py` → `ZidAdapter.map_order_economic_fact`.

## CURRENCY SOURCE

`currency.order_currency.code`. Conflict with `currency_code` → reject. Missing / non-ISO-4217 → reject.

## SHIPPING SOURCE

`payment.invoice[code=shipping].value`. Absent → NULL.

## ORDER SUBTOTAL SOURCE

`payment.invoice[code=sub_totals].value` only.  
`sub_totals_before_vat` is not treated as subtotal (V2 pending lesson).

## DISCOUNT SEMANTICS

NULL unless an explicit invoice `coupon`/`discount` line or `coupon.discount` is present. Absent coupon → NULL, not 0.

## TAX SEMANTICS

NULL unless invoice `vat` or `tax` exists. Line-item `tax_amount=0` is not used as order tax.

## REFUND SEMANTICS

UNKNOWN. No `refund_amount` column. No zero assumption. Gross paid amount only. Not net-after-refund.

## PLATFORM_PAID ONLY

YES

## USER_CLAIM EXCLUDED

YES

## PRE_PURCHASE EXCLUDED

YES

## CANONICAL DEDUPE

Unique `(store_slug, external_order_id, truth_version)`. Webhook replay upserts the same grain.

## BRIDGE DEDUPE

`zid_webhook:platform_paid_bridge` is not `PLATFORM_PAID`. Hook skips. No second monetary fact.

## EXTERNAL API ON DASHBOARD

0 required

## FETCH TRIGGER

After successful `ingest_purchase_truth` write, only if post-policy source is still authoritative `PLATFORM_PAID`. Bounded `GET /v1/managers/store/orders/{id}/view`. Tenant-scoped. Not a dashboard path. Not a scheduler job.

## MANAGER FAILURE BEHAVIOR

Purchase Truth remains valid. Economic fact remains unavailable. No Purchase Truth downgrade. 401 / timeout / 404 / auth-incomplete / monetary fail-closed → no row.

## AOV CONTRACT

`sum(paid_amount) / count(distinct external_order_id)`  
Same currency. Explicit window. Authoritative facts only. Not net AOV.

## STORE PAID-ORDER VALUE CONTRACT

`sum(paid_amount)` for store + currency + window.  
Safe name: **قيمة الطلبات المدفوعة**. Not merchant revenue.

## SAFE MERCHANT TERM

قيمة الطلب المدفوع

## NET REVENUE CLAIM

NO

## QUERY DELTA TARGET

+0 (not attached to merchant dashboard bundle). Future use: +1 bounded aggregate from persisted facts.

## N+1

0

## AI

0

## SCHEDULER

0

## DB TABLE REQUIRED

YES (`order_economic_facts`)

## DB COLUMN REQUIRED

NO (no money columns on `purchase_truth_records`)

## NEW TECHNICAL DEBT

NONE required. No cart-value fallback. No guessed money.

## TESTS

`tests/test_order_economic_fact_v1.py`  
Matrix: paid + paid_amount>0; remaining=0; pending+order_total; paid_amount missing/0; missing currency; currency mismatch; duplicate webhook; bridge key; replay; cross-tenant; GET 401/timeout/404; shipping absent; discount null; tax absent; refund unknown; USER_CLAIM / PRE_PURCHASE excluded.

## READY FOR CLEAN CANDIDATE

YES

## READY FOR EXACT-SHA DEPLOY

NO

## READY FOR ECONOMIC TRUTH EXPANSION

YES (gross paid owner exists; refund/net/COGS still unknown)

## READY FOR LEVEL 3

NO

## DEPLOY

NO

STOP.
