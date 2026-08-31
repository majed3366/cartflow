# Controlled Semantic Visual Restoration Implementation V1

**Date (UTC):** 2026-08-31  
**BASE SHA:** `e80b4d38c738236df83f53251a0389bdaff1fb70`  
**Branch:** `candidate/semantic-visual-restoration-v1`  
**DIRECT PARENT:** `e80b4d38` (exact)  
**SEMANTIC MODEL VERSION:** `semantic-visual-model-v1`  
**VISUAL SYSTEM:** `merchant-visual-system-v1`  
**CANONICAL RUNTIME:** `/dashboard` + `merchant_app_v2.html` + `merchant_ui_v2`

IMPLEMENTATION PERFORMED: **YES** (candidate only)  
PRODUCTION CHANGED: **NO**  
DEPLOY: **not performed** — real-device review required first

---

## What was implemented

RAW CANONICAL TRUTH → `CartFlowSemanticVisualV1` / `services/semantic_visual_model_v1.py` → painters.

Seven variables only: `core_silence`, `attention_intensity`, `decision_readiness`, `evidence_sufficiency`, `evidence_conflict`, `uncertainty_level`, `wait_kind`.

Commerce Object row is a **0–3 role clause**. Home omits R2/R3 when `status_ar` is absent. Diagnosis copy is not a driver. `evidence_lines_ar.length` is not a density driver. Momentum is not rendered.

---

## Files

| File | Role |
|------|------|
| `services/semantic_visual_model_v1.py` | Derivation (tests + SoT) |
| `static/merchant_ui_v2_semantic_model.js` | Client projection |
| `static/merchant_ui_v2_language.js` | `commerceClause`, `evidenceFieldFromSufficiency` |
| `static/merchant_ui_v2_home.js` | Home bind |
| `static/merchant_ui_v2_workspace.js` | Workspace bind |
| `static/merchant_ui_v2_language.css` | Bounded openness / tension / wait / label-hidden review |
| `templates/merchant_app_v2.html` | Load order + `semvis1` cache bust |
| Identity headers | `X-CartFlow-Merchant-Semantic-Model` |

No HES/Workspace API contract change. No Carts/Comms/Settings/Shell/Scheduler/DB change.

---

## Tests

`tests/test_semantic_visual_restoration_v1.py` covers Cases A–G plus JS↔Python parity and render HTML.

Also green: restoration, visual identity contract, regression gate, runtime identity, `test_merchant_ui_v2`.

---

## Evidence fragments

Under `evidence/`: Home quiet / attention / incomplete / omission; Workspace insufficient / sufficient / uncertainty / conflict / not-ready / ready.

Same decision sentence, READY vs NEEDS_MORE → different roles, density, mass. Conflict vs not-ready → tension `high` vs `none`.

Review-only label hide: `?cf_sem_proof=labels-hidden`.

---

## Review / deploy gate

Phase 20 real-device review is **not** done in this task. Do not deploy until that PASS.

STOP before Phase 21.
