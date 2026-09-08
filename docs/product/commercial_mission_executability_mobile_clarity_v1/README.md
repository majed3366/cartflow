# Commercial Mission Executability & Mobile Clarity V1

Closes merchant-facing gaps on the live R17 shipping mission:

COMMERCIAL DECISION → MERCHANT ACTION → EXECUTION PATH → SETTINGS → RECHECK

**Runtime candidate / live API SHA:** `867eddce62cdb8616414d7e477a0b1343426437d`  
**Deployment:** `52d70916-435a-4499-9b71-12bb16b1e7cc` SUCCESS  
**Lab:** `cf_live_reality_lab` · **R17_shipping_hesitation**  
**READY FOR FOUNDER LIVE PRODUCT REVIEW: YES.**  
**FOUNDER PRODUCT PASS: NOT YET.** Products V1 not started. General release: NO.  
Landing screenshot capture: NO.

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

## Live evidence

Canonical pack (production mobile 390px, `smartreplyai.net`):

`docs/product/commercial_mission_executability_mobile_clarity_v1/live/`

| File | Surface |
| --- | --- |
| `01_home_shipping_mobile.png` | Home CDA — shipping contract, 12/20 = 60% |
| `02_workspace_shipping_mobile.png` | Workspace — accept CTA + execution control |
| `03_workspace_after_accept_mobile.png` | Accepted CDC; اضبط أسباب التردد; no measurement |
| `04_settings_shipping_reasons_mobile.png` | Recovery policy — shipping/delivery reasons |
| `05_settings_timing_mobile.png` | Derived global range + selected stage from abandon |
| `06_sidebar_handle_mobile.png` | Contextual sidebar handle `#18B0A8` / white double-bar / edge `#0d6e69` |

Desktop convenience copy (review only, not source of truth):

`C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Commercial_Mission_Executability_Mobile_Clarity_V1_Live\`
