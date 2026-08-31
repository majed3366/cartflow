# 08 — MERCHANT_VISUAL_IDENTITY_REGRESSION_GATE

**Active when:** `tests/test_merchant_visual_identity_regression_gate_v1.py` is in the candidate and passing.

A Merchant UI deploy must fail if:

- legacy renderer / template become canonical
- required Home / Workspace identity anchors disappear
- canonical shell markers disappear or `cf-rail` returns on V2
- `visual_system_version` mismatches `merchant-visual-system-v1`
- leftover `cf_ui_v2=0` can select V1 (covered by contract tests)

Run:

```
python -m unittest tests.test_merchant_visual_identity_contract_v1 tests.test_merchant_visual_identity_regression_gate_v1 tests.test_merchant_runtime_identity_v1
```
