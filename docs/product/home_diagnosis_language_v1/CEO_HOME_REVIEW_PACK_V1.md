# Home Diagnosis Language V1 — CEO Home Review Pack

**Status:** Awaiting production deploy + Home-only CEO Review  
**Date (UTC):** 2026-07-27  
**Scope:** Home only (`/dashboard#home`)

---

## Rule

Every Home card must read:

**Observation → Diagnosis → Recommendation**

Never: Observation → Recommendation.

Merchant reaction target: *“Now I understand why this is happening.”*

---

## Required language

| Card | Diagnosis shape | Recommendation |
|------|-----------------|----------------|
| حالة المتجر | يعتقد CartFlow أن… (contact / setup) أو أدلة غير كافية | راجع التواصل / الإعدادات / واصل جمع الأدلة |
| أهم قرار اليوم | يعتقد CartFlow أن أكبر فرصة… (never يبدأ بـ راجع) | راجع رحلة الشراء |
| أبرز المنتجات | نية شراء دون سبب مؤكد / شحن / عودة / أدلة غير كافية | بعد التشخيص |
| التواصل | لا يمكن التواصل… لأن رقم الهاتف غير متاح | راجع التواصل |

---

## STOP

Await explicit **HOME APPROVED** before any further Home changes.
No Workspace / Products / Carts / Communication / Settings work in this review.
