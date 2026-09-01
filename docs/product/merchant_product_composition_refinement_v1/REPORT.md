# Merchant Product Composition Refinement V1 — Report

**Base SHA:** `ca9525b38c05629fed3469948334c8b7132cf51f`  
**Candidate SHA:** `d3f8cef0f9a3c1730a432c9a3e1ba20707d08331`  
**Direct parent:** `ca9525b38c05629fed3469948334c8b7132cf51f`  
**Review host:** `http://127.0.0.1:8794` (`ENV=development`, pinned SHA)  
**Deploy:** NOT performed

## Proven outcomes

| Area | Result |
|------|--------|
| Contextual sidebar Carts/Comms/Settings | Page-specific `.cf2-ctx`; Products remain `null` |
| Home recovery | Operational KPI strip below decision board |
| Comms forms | Frame Open / CF grammar ticks; `border-radius: 50%` gone |
| Message body | `full_message_ar` / `preview_ar`; honest unavailable |
| Settings rename | «إعدادات واتساب»; primary «التواصل» preserved |
| Settings collision | ledger `padding-inline-start` 34px / mobile 32px |

## Gate

`tests/test_merchant_product_composition_refinement_v1.py` + preserved visual fix gates — PASS
