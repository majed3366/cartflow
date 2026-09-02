# Operational Guidance Layer V1 — Report

**Base SHA:** `90d919d850bef1c762bdb75ca80461b6b514c3d4`  
**Deploy:** NOT authorized / NOT performed

## Evidence audit (guidance families)

| Family | Classification | Grounding |
|--------|----------------|-----------|
| shipping_friction | SUPPORTED_NOW | hesitation dist / diagnostic shipping family |
| price_hesitation | SUPPORTED_NOW | hesitation dist thresholds (MIN_HESITATION_TOTAL=8, share≥40%) |
| product_confidence_quality | SUPPORTED_NOW | quality/warranty dist + interest diagnostic |
| wait_insufficient_evidence | SUPPORTED_NOW | always safe default |
| communication_followup | SUPPORTED_NOW | home teaser `no_phone` / contact diagnostic |
| Arbitrary price/discount uplift claims | UNSUPPORTED | not implemented |
| Fabricated shipping free-threshold tests | UNSUPPORTED | not implemented |

## Surfaces

- **Home:** executive OGL block (ما نراه / ماذا يعني / ماذا تفعل الآن / متى تعيد الفحص); satellite roles replace repeated «اعرف الآن»
- **Workspace:** diagnosis / recommendation / why / recheck on primary card
- **Recovery:** advanced demotion; template-owned timing summary
- **Widget settings:** reason display order reorder UI → `reason_display_order`

## Gate

`tests/test_operational_guidance_layer_v1.py`
