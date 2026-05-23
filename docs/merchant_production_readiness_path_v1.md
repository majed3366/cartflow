# Merchant Production Readiness Path v1

**Date (UTC):** 2026-05-19  
**Commit:** `feat: add merchant production readiness path v1`  
**Scope:** Actionable progression on top of `merchant_onboarding_reality_v1`. **No** runtime/send/recovery changes.

---

## Question

**Can a merchant understand exactly what to do next?**

| Answer | Detail |
|--------|--------|
| **YES** (with path v1) | Each state returns Arabic `next_action`, `expected_result`, labeled `missing_items`, score %, and remaining count. |
| **Caveat** | Server-only steps (Twilio env, status callback) still require ops — labeled clearly in missing items. |

---

## Onboarding states → path output

| State | Score cap / typical | Primary next action |
|-------|---------------------|---------------------|
| `not_started` | 0% | تهيئة/ربط المتجر |
| `sandbox_only` | ≤55% | ربط مزود واتساب الإنتاج |
| `partial` | 1–99% | أول بند ناقص في القائمة |
| `production_ready` | 100% | متابعة التشغيل |

---

## Capability matrix (example: `sandbox_only`)

| Missing (AR) | Action | Expected outcome |
|--------------|--------|------------------|
| مزود واتساب الإنتاج | ربط مزود واتساب الإنتاج | PRODUCTION_MODE + Twilio على الخادم |
| متابعة تسليم الرسائل | اضبط رابط استدعاء حالة التسليم | تُعرَف حالات التسليم بعد الإرسال |
| اعتماد قوالب المزود | قدّم قوالب واتساب للاعتماد | رسائل خارج 24 ساعة مقبولة |

Risk: **high** · Effort: **medium** (typical for sandbox → production gap)

---

## Logs

```text
[MERCHANT READINESS] store_slug=demo level=sandbox_only missing=...
[MERCHANT NEXT ACTION] store_slug=demo state=sandbox_only next_action=ربط مزود واتساب الإنتاج remaining=...
```

---

## Admin card (جاهزية المتجر)

On `/admin/operational-health`:

1. الحالة الحالية  
2. جاهزية الإنتاج: **72%** (example)  
3. متبقي: **N** بند  
4. البنود الناقصة (bullets)  
5. الخطوة التالية  
6. النتيجة المتوقعة  

---

## API surface

| Function | Module |
|----------|--------|
| `build_merchant_production_readiness_path(store)` | `merchant_production_readiness_path_v1.py` |
| `build_merchant_production_readiness_card(store)` | Admin card payload |

---

## Verification matrix (automated)

| Scenario | PASS |
|----------|------|
| Empty store | ✅ |
| Sandbox | ✅ |
| Partial | ✅ |
| Production | ✅ |
