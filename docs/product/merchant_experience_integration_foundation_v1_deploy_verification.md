# Merchant Experience Integration Foundation V1 — Deploy Verification

**Flag:** `CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1` (default on)  
**Probe:** `GET /dev/merchant-experience?store=demo`

## Local

```bash
pytest tests/test_merchant_experience_integration_v1.py -q
python scripts/merchant_experience_validation_v2.py
```

## Production

```bash
python scripts/_verify_merchant_experience_v1.py --base https://smartreplyai.net --store demo
```

Expect `ok: true` with:

- `foundation_enabled: true`
- `governed_consumption_pct: 100`
- `navigation_integrity: true`
- `routing_integrity: true`
- `mev1_high_resolution` all true
- `integration_failures: []`
- `canonical_fingerprint` present

## Reality Validation V2

```bash
python scripts/merchant_experience_validation_v2.py --prod-only
```

Expect materially improved readiness vs MEV1 **28/100**.

## STOP

No visual redesign until V2 confirms truthful merchant reflection.
