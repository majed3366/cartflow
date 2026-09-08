# Commercial Mission Executability & Mobile Clarity V1

Closes merchant-facing gaps on the live R17 shipping mission:

COMMERCIAL DECISION → MERCHANT ACTION → EXECUTION PATH → SETTINGS → RECHECK

**Runtime candidate SHA:** `867eddce62cdb8616414d7e477a0b1343426437d`  
**FOUNDER PRODUCT PASS: NOT YET.** Products V1 not started. General release: NO.

## Law

CartFlow must not recommend an action the merchant cannot actually execute or reach.

Acceptance CTA remains frozen: `اعتمد هذه المهمة` = decision accepted, not execution started.

## Shipping truth (R17)

- Known: shipping is the most repeated hesitation family (12 / 20 = 60%).
- Unknown: whether shipping cost or delivery duration dominates.
- Next action: distinguish those two customer reason choices.
- Not claimed: which one stops purchase; customers leaving after the shipping step.

## Execution path

Platform taxonomy already has separate authoritative reasons:

| Key | Merchant label | Customer widget label |
| --- | --- | --- |
| `shipping` | الشحن | الشحن |
| `delivery` | مدة التوصيل | مدة التوصيل |

Merchant can enable/disable each, edit recovery wording and stage timing. Merchant cannot add/delete reasons. Widget chip labels are platform-fixed.

Secondary control after accept: **اضبط أسباب التردد** → `#settings?area=recovery&focus=shipping-hesitation` (UI location only).

## Timing

One model: configured stages. Global summary is derived min–max of enabled first-message delays. Selected stage is independently labeled from cart abandonment.

## Evidence

Live supporting shots (after exact-SHA deploy) belong in `live/`. Desktop convenience copy is review-only.
