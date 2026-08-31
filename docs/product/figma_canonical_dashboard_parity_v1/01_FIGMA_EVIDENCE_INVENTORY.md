# 01 — Authoritative Figma evidence inventory

Observed 2026-08-31 against live Figma files and repo artifacts.

| Artifact | Class | Why |
|----------|-------|-----|
| Visual Language Constitution V1 (`docs/product/merchant_ui_v2_visual_language_maturity_v1/VISUAL_LANGUAGE_CONSTITUTION_V1.md`) | **CANONICAL** | Frozen Figma CIM / Signature product language (hist. pages 23, 29) |
| `static/merchant_ui_v2_language.css` + `.js` | **CANONICAL** | Runtime of that constitution |
| Merchant Visual System V1 P1–P16 | **CANONICAL** | Surface law extracted from accepted V2 |
| Figma `1NnI69Jd7BhfnNdehmBq0Q` page Foundations | **REFERENCE_ONLY** | Tokens only. File text: “Variables only — no product screens.” Inter, not Tajawal. |
| Figma `0YWwVn1cKxH45M6mLZfGJE` Visual Asset System | **NOT_APPLICABLE_TO_MERCHANT_UI** | Marketing / illustration libraries. No Merchant pages. |
| Historical Dashboard V3 wireframes (Hero + 2×2 metrics) on `1NnI69Jd7BhfnNdehmBq0Q` | **OBSOLETE** | Pages no longer in the live file. Layout conflicts current executive Home. |
| Historical Figma 25–34 (V1 frame recomposition) | **OBSOLETE** | Bound to `merchant_app.html` / `cf-rail`, not V2 shell |
| SA-02 / SA-03 `figma_refs` (left rail, dark card wall) | **REJECTED** | Historical snapshot; would restore obsolete shell |
| Landing Figma `fPur35ZnK96pDvKPLUGXTb` | **NOT_APPLICABLE_TO_MERCHANT_UI** | Public `/` only |
| Language-maturity / figma-parity capture PNGs | **REFERENCE_ONLY** | Proof of constitution on V2, not a second SoT |

## Canonical evidence by surface

| Surface | Canonical evidence |
|---------|--------------------|
| Home | Constitution DNA + P12–P16 + `CartFlowUiV2Home` |
| Workspace | Constitution decision/route + P12–P15 + `CartFlowUiV2Workspace` |
| Carts / Communication / Settings | Visual System P2–P11 (same language, different responsibility) |
| Shell | UtilityRow → GlobalUpbar → ContextualSidebar → PageStage |
| Mobile | Constitution §11 + Visual System mobile law (1023px) |
| Shared primitives | `merchant_ui_v2_language.*` |
| Interaction states | Visual System `03_STATE_SYSTEM.md` |

**Authoritative Figma artifacts (finite): 3** — Constitution, language layer, Visual System P1–P16.
