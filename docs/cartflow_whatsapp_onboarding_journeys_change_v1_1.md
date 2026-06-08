# CartFlow — WhatsApp Onboarding Journeys V1.1 (Change Journey)

**Date:** 2026-06-07 (UTC)

## Change

Merchants can change `whatsapp_onboarding_journey` after initial selection without DB/API reset.

- Selected state: «مسار واتساب الحالي» + link «تغيير مسار واتساب»
- Change opens the same 4-option selector; current path marked «المسار الحالي»
- Safety copy on change panel
- Switching journey updates readiness/CTA/guidance; does **not** clear phone, recovery, or other settings

## Files

- `static/merchant_whatsapp_settings.js` — change UX + `journeyChangeOpen` toggle
- `services/merchant_whatsapp_onboarding_journeys_v1.py` — API copy fields
- `static/merchant_app.css` — change button, current badge, safety note

## Tests

`tests/test_merchant_whatsapp_onboarding_journeys_change_v1.py`
