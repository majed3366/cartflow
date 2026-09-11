# Order Economic Fact V1

**Status:** AUTHORIZED CONTRACT IMPLEMENTATION + TESTS  
**Date (UTC):** 2026-09-11  
**Deploy:** NO · **Exact-SHA:** NO · **General release:** NO · **Level 3:** NO

Platform-neutral monetary owner for **authoritative paid orders** only.

Question answered: **كم دفع العميل فعليًا لهذا الطلب؟**

Not revenue attribution. Not margin. Not Level 3.

## Law

Create a fact only when:

1. Purchase Truth provenance = `PLATFORM_PAID` (`zid_webhook:platform_paid`)
2. Zid order detail `payment_status == paid`
3. `payment_summary.paid_amount > 0`
4. Currency is a known ISO-4217 code (no conflict)

Do not use `cart_value`, `order_total` alone, `transaction_amount` alone, `order_created`, WhatsApp claim, or event-name inference.

## Owner

| Item | Value |
| --- | --- |
| Canonical owner | `OrderEconomicFact` |
| Table | `order_economic_facts` |
| Grain | `(store_slug, external_order_id, truth_version)` |
| Truth version | `oef_v1` |
| Sibling of | `PurchaseTruthRecord` (boolean + identity only; no money columns) |

## Zid paid authority

Raw paths stay in `integrations/zid_order_economic_v1.py`.

- Paid amount: `payment_summary.paid_amount`
- Currency: `currency.order_currency.code` (fail if it conflicts with `currency_code`)
- Shipping: `payment.invoice[code=shipping].value`
- Subtotal: `payment.invoice[code=sub_totals].value` only (not `sub_totals_before_vat`)
- Tax / discount: only explicit invoice `vat`/`tax` or coupon/discount codes
- Refund: unknown — no `refund_amount` column, no zero assumption

Supporting (not paid authorities): `order_total`, `transaction_amount`, `remaining_amount`.

## Fetch

Triggered after successful PLATFORM_PAID Purchase Truth write. Bounded authenticated `GET /managers/store/orders/{id}/view`.

Not called from dashboard render. Manager failure leaves Purchase Truth valid and the economic fact unavailable.

## Safe terms

- Merchant: **قيمة الطلب المدفوع**
- Aggregate: **قيمة الطلبات المدفوعة**
- AOV: gross paid-order AOV only — not net AOV, not net revenue
