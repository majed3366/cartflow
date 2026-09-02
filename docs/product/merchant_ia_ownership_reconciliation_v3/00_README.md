# Merchant IA & Ownership Reconciliation V3

**Base SHA:** `9a5a6acf4b606629c5380c3d8b7fa9b2c96f9d15`  
**Cache bust:** `iarec3`  
**Deploy:** NOT authorized

## Scope

1. Canonical Recovery Policy owns reason-specific templates (no V1 handoff)
2. Block merchant-facing legacy shell navigation (`cf_ui=v1`)
3. Account drawer shows current store + package
4. Replace merchant-facing «العتبة» with VIP cart minimum-value language
5. Preserve V2 composition / runtime contracts; Products unchanged

## Gate

`tests/test_merchant_ia_ownership_reconciliation_v3.py`
