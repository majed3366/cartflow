# Operational Guidance Layer V1 + Recovery Policy Semantics Cleanup

**Status:** CANDIDATE — deploy NOT authorized  
**Base:** `90d919d850bef1c762bdb75ca80461b6b514c3d4`  
**Cache:** `ogl1`

## Guidance contract

`EVIDENCE → DIAGNOSIS → RECOMMENDATION → WHY → ACTION → RECHECK`

Object: `services/operational_guidance_v1/`

## Families (SUPPORTED_NOW = 5)

1. `shipping_friction`
2. `price_hesitation`
3. `product_confidence_quality`
4. `wait_insufficient_evidence`
5. `communication_followup`

Unsupported families are not implemented.

## Recovery cleanup

- Primary timing label: أقرب إرسال من القوالب
- Store delay / attempts: إعدادات متقدمة only
- Merchant copy: يُستخدم فقط عندما لا يوجد قالب سبب قابل للتطبيق

## Widget reason order

Immutable keys; merchant `reason_display_order` via drag / touch / arrows on Settings → الودجيت.
