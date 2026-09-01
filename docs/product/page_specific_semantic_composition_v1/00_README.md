# Page-Specific Semantic Composition Implementation V1

**Base SHA:** `b8c1318a06e99fe75eccefecf7e4492db489ab4d`  
**Candidate:** branch `candidate/page-specific-semantic-composition-v1` (exact child of base)  
**Direct parent:** `b8c1318a06e99fe75eccefecf7e4492db489ab4d`  
**Source RCA:** `docs/product/page_specific_semantic_visual_grammar_rca_v1/`  
**Cache bust:** `psg1` on Home / Workspace / Carts / Comms / Settings assets  
**semantic-visual-model-v1:** unchanged  
**Deploy:** NOT performed (real-device review required)

## Organisms shipped

| Page | `data-cf2-organism` | Painter / CSS |
|------|---------------------|---------------|
| Home | `gravity-well` | `merchant_ui_v2_home.js/.css` |
| Workspace | `formation` | `merchant_ui_v2_workspace.js/.css` |
| Carts | `weighted-queue` | `merchant_ui_v2_carts.js/.css` |
| Communication | `lifecycle-continuum` | `merchant_ui_v2_comms.js/.css` |
| Settings | `config-ledger` | `merchant_ui_v2_settings.js/.css` |

## Identity contracts

`services/merchant_visual_identity_v1.py` emitters updated to organism markers (CO row no longer page-defining on Home/WS). Language-layer `.cf2-co-row` remnants remain for shared grammar.

## Tests

- `tests/test_page_specific_semantic_composition_v1.py` — mandatory regressions
- Updated: figma parity, visual restoration painter contracts, home/WS restoration, identity gate/contract

## STOP

No production deploy from this pack until real-device review passes page-name-hidden acceptance.
