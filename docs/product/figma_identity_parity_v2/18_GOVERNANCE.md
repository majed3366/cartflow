# 18 — Permanent regression gate extension

Future Merchant UI change must fail closed if any of:

| Failure | How gated |
|---------|-----------|
| Semantic primitives become static/decorative | Painters must call `CartFlowSemanticVisualV1` / `commerceClause` / `evidenceFieldFromSufficiency`; `densityFromCount` forbidden in Home/WS painters |
| Home/Workspace identity anchors disappear | `CANONICAL_HOME_EMITTERS` / `CANONICAL_WORKSPACE_EMITTERS` |
| Legacy dashboard renderer becomes canonical | Forbidden markers + identity `canonical=true` requires `merchant_ui_v2` |
| Signature primitive contract disappears | `FIGMA_MAPPED_PRIMITIVES` in language layer |
| Mobile falls back to generic structure | Frame `@media (max-width: 1023px)` + `cf2-ctx-handle`; no `cf-rail` |
| Shell changes unexpectedly | `X-CartFlow-Merchant-Shell` = utility-row+global-upbar+contextual-sidebar |
| Visual system / semantic model version diverges | Identity + headers must match `merchant-visual-system-v1` / `semantic-visual-model-v1` |
| Figma / visual-law traceability missing | `visual_law_set`, `figma_identity_parity=pass`, VIS-INV-08 |

Tests: `tests/test_figma_identity_parity_v2.py` + `tests/test_merchant_visual_identity_regression_gate_v1.py` + `tests/test_semantic_visual_restoration_v1.py`.

Do not rely on pixel screenshot CI as the only gate.
