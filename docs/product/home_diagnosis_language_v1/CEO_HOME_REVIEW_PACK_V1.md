# Home Diagnosis Language V1 — CEO Home Review Pack

**Status:** Production deployed · Home-only CEO Review  
**Date (UTC):** 2026-07-27  
**Commit:** `72f614b`  
**Store:** Living Store review · `demo` · `cf.living.store.review@smartreplyai.net`  
**Verdict (automated):** `PASS_HOME_DIAGNOSIS_LANGUAGE_V1`  
**Evidence:** `prod_home_ceo_review.json` · `prod_desktop_home.png` · `prod_mobile_home.png`

---

## Rule

Every Home card must read:

**Observation → Diagnosis → Recommendation**

Never: Observation → Recommendation.

Merchant reaction target: *“Now I understand why this is happening.”*

---

## Painted slots (Living Store at capture)

| Slot | Diagnosis (short) | Recommendation |
|------|-------------------|----------------|
| حالة المتجر | يعتقد CartFlow أن متابعة العملاء مقيدة لأن السلال بلا معلومات تواصل قابلة للاستخدام | راجع التواصل. |
| أهم قرار اليوم | يعتقد CartFlow أن أكبر فرصة ضائعة هي Nano 20W لأن العملاء يغادرون عند الشحن | راجع رحلة الشراء. |
| أبرز المنتجات | يغادر العملاء بعد ظهور الشحن في مسار Nano 20W | راجع رحلة الشراء. |
| السلال | omitted | — |
| التواصل | لا يمكن التواصل… لأن رقم الهاتف غير متاح | راجع التواصل. |

Desktop and Mobile: **identical diagnosis meaning**.

---

## Automated checks (all green)

- Diagnosis nodes painted (4)
- Recommendation nodes painted (4)
- No card diagnosis starts with راجع / اذهب / افتح
- Marker `home_diagnosis_language_v1` on surface + API
- No event-summary title «اهتمام مرتفع دون شراء» as diagnosis

---

## STOP

Await explicit **HOME APPROVED** before any further Home changes.
No Workspace / Products / Carts / Communication / Settings work in this review.
