# CartFlow — Journey Completion vs Readiness Separation V1

**Date:** 2026-06-07 (UTC)

## Problem

Journey progress and WhatsApp production readiness were conflated in the merchant UI — merchants who completed journey steps still saw «متابعة التفعيل» and setup messaging.

## Principle

| Dimension | Question |
|-----------|----------|
| **Journey Completion** | Did the merchant complete the selected path? |
| **Readiness** | Is WhatsApp production-ready? |

These are independent.

## Completion criteria

| Journey | Completed when |
|---------|----------------|
| لدي واتساب أعمال | Number saved + recovery enabled |
| لا أملك واتساب أعمال | Number saved + recovery enabled (return path) |
| أريد رقماً جديداً | Number saved + recovery enabled |
| لدي إعدادات Meta جاهزة | Path selected |

## Merchant UX when journey completed

- Journey panel: «✓ تم إكمال هذا المسار», summary items, status badge
- Actions: «تغيير مسار واتساب», «مراجعة الإعدادات»
- Production panel: separate «جاهزية الإنتاج» with readiness engine copy/CTA
- No «متابعة التفعيل» when journey requirements are satisfied

## Module

`merchant_whatsapp_journey_execution_v1.py` — `build_journey_completion_ui`, completed-branch in `apply_journey_execution_to_readiness` preserves readiness `action_first` title/next-action.

## Tests

`tests/test_merchant_whatsapp_journey_completion_v1.py`
