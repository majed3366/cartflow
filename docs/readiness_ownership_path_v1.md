# Readiness Ownership Path v1

**Date (UTC):** 2026-05-19  
**Commit:** `feat: add readiness ownership path v1`

---

## Question

**Can admin know exactly who should act?**

| Answer |
|--------|
| **YES** — every missing readiness item maps to one or more owner categories with Arabic labels, action, and expected result. |

---

## Owner categories

| Code | Arabic (admin card) |
|------|---------------------|
| `merchant` | التاجر |
| `cartflow_ops` | تشغيل CartFlow |
| `provider` | مزود واتساب |
| `platform` | المنصة |
| `shared` | مشترك (التاجر + التشغيل) |

Combined example: `merchant + provider` → **التاجر + مزود واتساب**

---

## Blocker matrix (examples)

| المشكلة | المسؤول | الإجراء | الأثر المتوقع |
|---------|---------|---------|---------------|
| اعتماد قوالب المزود | التاجر + مزود واتساب | قدّم قوالب واتساب للاعتماد | لا تُرفض الرسائل خارج 24 ساعة |
| متابعة تسليم الرسائل | تشغيل CartFlow | اضبط عنوان استدعاء حالة التسليم | تُسجَّل حالات queued/delivered/failed |
| مزود واتساب الإنتاج | تشغيل CartFlow + المنصة | ربط مزود واتساب الإنتاج | إرسال إنتاجي حقيقي |

---

## Logs

```text
[READINESS OWNER] store_slug=demo problem=مزود واتساب الإنتاج owner=cartflow_ops+platform action=ربط مزود واتساب الإنتاج
```

---

## Admin card (جاهزية المتجر)

Appends ownership section:

1. المشكلة  
2. المسؤول  
3. الإجراء  
4. الأثر المتوقع  

(Up to 4 blockers on the card.)

---

## Code

| Module | Role |
|--------|------|
| `services/readiness_ownership_path_v1.py` | Ownership catalog + logs + card enrich |
| `build_merchant_readiness_card_with_ownership` | Admin entry point |

No changes to merchant dashboard templates or recovery runtime.
