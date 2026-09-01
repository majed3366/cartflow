# Merchant Configuration & Context Composition V2

**Base SHA:** `652ad169c56d13791417e1f9d2a98ff640e0b560`  
**Cache bust:** `setcomp2`  
**semantic-visual-model-v1:** unchanged  
**Deploy:** NOT authorized

## Scope

1. Home contextual sidebar → independent **الملخص** destination (recovery KPIs moved out of overview)
2. Recovery Policy → reason-specific message/template models (`#ma-tpl-root` under `#settings/recovery`)
3. Settings **التجربة** → **الودجيت** with real widget configuration (color, timing, appearance intent)
4. Remove remaining generic emoji WhatsApp mode forms on authorized V2 surfaces
5. `mock_sent_*` presentation contract — strip SRS/simulator bodies from merchant comms API/UI
6. Contextual sidebar maturity — authoritative counts/hints on Carts, Communication, Settings

## Out of scope

- Products (unchanged)
- semantic-visual-model-v1 / page organisms
- Scheduler / autodeploy / deploy

## Gate

`tests/test_merchant_config_context_composition_v2.py`  
+ preserved gates: `test_merchant_product_composition_refinement_v1.py`, `test_merchant_whatsapp_mode_v1.py`, `test_controlled_production_visual_fix_v1.py`
