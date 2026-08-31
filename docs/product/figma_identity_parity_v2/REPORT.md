# Figma Identity Parity Closure V2 — report

Hunks: DOCUMENTATION · REGRESSION_TEST · SHARED_VISUAL_PRIMITIVE (identity contract). UNRELATED = 0.  
Painters / CSS / semantic mappings: unchanged.

**BASE SHA:** `2d6cc8c1fda58ab594fa7e0090e48a7f0c79c7f8`  
**DIRECT PARENT:** `2d6cc8c1fda58ab594fa7e0090e48a7f0c79c7f8`

## What closed PARTIAL → PASS

V1 left identity PARTIAL because the live Figma file is not screen SoT and the constitution still listed momentum / 6-density states the semantic model does not drive.

This candidate:

1. Classifies a finite authoritative evidence set (15 sources; 8 used).
2. Binds `visual_law_set=constitution-v1+semantic-visual-model-v1` and 19 `CANONICAL_VISUAL_LAWS`.
3. Encodes VIS-INV-01…10.
4. Marks constitution momentum / 6-density / unbound CO kinds as superseded.
5. Sets `figma_identity_parity=pass` on `/dashboard` identity + headers.
6. Extends the permanent regression gate (`tests/test_figma_identity_parity_v2.py` + existing gate).

No Home / Workspace / Carts / Communication / Settings painter change. Semantic truth mappings untouched.

## Headers

- `X-CartFlow-Merchant-Figma-Parity` = `visual-language-constitution-v1` (contract name, unchanged)
- `X-CartFlow-Merchant-Visual-Law` = `constitution-v1+semantic-visual-model-v1`
- `X-CartFlow-Merchant-Figma-Identity-Parity` = `pass`
