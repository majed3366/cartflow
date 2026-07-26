# Merchant Session Identity Panel V1

**Status:** Implemented  
**Date (UTC):** 2026-07-26

## Purpose

Make the authenticated merchant identity visible and verifiable from every merchant session (Desktop + Mobile), so reviewers can confirm they are looking at the same account/store before comparing VIP or other settings.

## Surface

- Control: `#ma-gtb-account-btn` in the global topbar
- Panel: Account Identity dialog (`static/merchant_session_identity_v1.js` + `.css`)
- API: `GET /api/merchant/session-identity?dashboard_store_slug=…`
- Composition: `services/merchant_session_identity_v1.py` (no new engines)

## Fields

Merchant name · email · store name · store slug · merchant ID · commerce provider · connection status · environment · session fingerprint · session start time · review label

Does **not** expose `simulation_run_id` or developer diagnostics.

## Consistency check

Compares authenticated merchant/store with the loaded dashboard `store_slug`.

- Match → «✓ أنت تعرض نفس التاجر والمتجر عبر هذه الجلسة.»
- Mismatch → «✕ يوجد اختلاف في الجلسة…» + action «افتح حساب المراجعة الصحيح» → `/dev/living-store-home-review`

## Living Store review

Expected principal: `cf.living.store.review@smartreplyai.net` · store `demo` · merchant ID from issued review session (production evidence: `429`).
