# Merchant Setup Experience v1

## Goal

Translate operational readiness into a **30-second merchant setup** view. Admin operational cards keep full truth (`readiness_ownership_path_v1`, admin health).

## Merchant sees

| Field | Example |
|--------|---------|
| Title | متجرك قريب من التشغيل الكامل |
| جاهزية | 72٪ |
| تبقى | 3 إعدادات |
| النتيجة | ستبدأ رسائل الاسترجاع بالوصول للعملاء |
| الخطوة التالية | ربط واتساب الإنتاج |
| Button | أكمل الإعداد → ordered steps |

Progress ladder: **0% → 33% → 66% → 100%** with states **غير جاهز → قريب من التشغيل → جاهز → تشغيل كامل**.

## Merchant does NOT see

Risk, effort, owner matrix, provider jargon, callback wording, internal readiness codes.

## Wiring

| Surface | Mechanism |
|---------|-----------|
| `GET /dashboard` | `merchant_app.html` + `static/merchant_dashboard_lazy.js` hydrates from `GET /api/dashboard/summary` → `merchant_setup_experience` |
| `GET /dashboard/analytics` | `templates/partials/merchant_setup_experience_card.html` |
| `GET /api/merchant/setup-experience` | JSON for tests / tools |
| Service | `services/merchant_setup_experience_v1.py` (maps `merchant_production_readiness_path_v1`) |

## Before vs after (merchant home)

### Before

```
┌─────────────────────────────────────┐
│ حالة الواتساب                       │
│ [شارة: غير جاهز / تجريبي …]        │
│ فقرة تقنية عن التسليم / المزود …   │
│ [زر إعدادات]                        │
└─────────────────────────────────────┘
```

### After

```
┌─────────────────────────────────────┐
│ متجرك قريب من التشغيل الكامل        │
│ جاهزية: 72٪   تبقى: 3 إعدادات      │
│ النتيجة: ستبدأ رسائل الاسترجاع …   │
│ الخطوة التالية: ربط واتساب الإنتاج  │
│ [ أكمل الإعداد ]                    │
│   1. ربط واتساب الإنتاج ↓           │
│   2. اعتماد الرسائل ↓               │
│   3. اختبار الإرسال                 │
└─────────────────────────────────────┘
```

## Verification

**Can a non-technical merchant know what to do in &lt;30 seconds?** **YES** — single headline, remaining count, next step, and three ordered actions with expected outcomes.

Log tag: `[MERCHANT SETUP EXPERIENCE]`.
