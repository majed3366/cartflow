# Audit — Why «✗ واتساب جاهز» persists after journey completion

**Date:** 2026-06-07 (UTC)  
**Type:** Root-cause only — no behavior change.

## Symptom

Merchant completes journey (number saved, recovery toggle on, journey `completed`) but checklist still shows:

```
✗ واتساب جاهز
```

## Render path (exact)

| Step | Location | Output |
|------|----------|--------|
| 1 | `GET /api/recovery-settings` → `merchant_whatsapp_mode_fields_for_api` | includes `whatsapp_connection_readiness` |
| 2 | `connection_readiness_for_merchant_api(store)` | merchant readiness payload |
| 3 | `evaluate_onboarding_readiness(store)` | `flags`, `blocking_steps` |
| 4 | `_readiness_dimensions(store, flags)` | dimension `key=whatsapp_ready`, `label_ar=واتساب جاهز`, `ready=whatsapp_ok` |
| 5 | `whatsapp_setup_checklist_for_merchant(store, dimensions)` | `setup_checklist.checklist_ar[]` with `mark_ar` ✓/✗ |
| 6 | `static/merchant_whatsapp_settings.js` → `renderReadinessCard` | renders `✗ واتساب جاهز` when `complete=false` |

## Field responsible for ✗

```python
# merchant_whatsapp_connection_readiness_v1.py → _readiness_dimensions
{
    "key": "whatsapp_ready",
    "label_ar": "واتساب جاهز",
    "ready": whatsapp_ok,  # ← when False → mark_ar = "✗"
}
```

## `whatsapp_ok` formula (exact)

```python
whatsapp_ok = (
    recovery_on                    # flags.recovery_enabled
    and wa_number                  # store.store_whatsapp_number non-empty
    and not sandbox                # flags.sandbox_mode_active must be False
    and (prov or not sandbox_mode_active)
    and (wa_cfg or sandbox)        # wa_cfg = flags.whatsapp_configured
)

if sandbox and store_ok and widget_ok and wa_number and recovery_on:
    whatsapp_ok = False  # explicit sandbox override
```

## Journey completion vs checklist (different inputs)

| Concern | Source | Fields |
|---------|--------|--------|
| **Journey completed** | `merchant_whatsapp_journey_execution_v1.compute_journey_status` | `store_whatsapp_number`, `store.whatsapp_recovery_enabled` |
| **«واتساب جاهز» checklist** | `_readiness_dimensions` | `flags.recovery_enabled` (from `is_active` + `recovery_attempts`), `flags.sandbox_mode_active`, `flags.whatsapp_configured` (Twilio env), `flags.provider_ready` |

Journey completion does **not** feed the checklist item.

## Typical failing conditions (sandbox / cartflow_managed)

When merchant has number + recovery toggle but checklist stays ✗:

1. **`flags.sandbox_mode_active = True`**  
   - Source: `recovery_uses_real_whatsapp()` is False  
   - `PRODUCTION_MODE` unset OR Twilio env incomplete  
   - Fails `not sandbox` in base formula

2. **`flags.whatsapp_configured = False`**  
   - Source: `whatsapp_real_configured()` — needs `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`  
   - Required when not in sandbox branch of `(wa_cfg or sandbox)`

3. **`sandbox_merchant_setup_complete_override`**  
   - When sandbox + store + widget + number + recovery all true → **forces `whatsapp_ok = False`**  
   - Code: `_readiness_dimensions` lines 426–427  
   - **Primary root cause** for merchants who did everything CartFlow journey asked

## Readiness title («جاري إعداد الاتصال»)

Separate from checklist item:

- `build_action_first_card` → `CONNECTION_STATE_ACTION_FIRST[connection_state].title_ar`
- When `sandbox_mode_active` and store/widget ok → `connection_state = pending_configuration` → title **«جاري إعداد الاتصال»**

## Temporary diagnostic

- API: `whatsapp_connection_readiness.readiness_diagnostic_temp`
- UI: collapsible «تشخيص مؤقت» on `#whatsapp` readiness card
- Module: `merchant_whatsapp_readiness_diagnostic_v1.py`

Remove after audit concludes.
