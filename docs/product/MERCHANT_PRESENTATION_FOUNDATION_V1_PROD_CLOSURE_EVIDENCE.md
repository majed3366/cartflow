# Merchant Presentation Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-21  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `bd10cd4176917ce4804c1e2e5d0da85b1cd4b5b8` (PR #36)

---

## 1. Pull request merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#36](https://github.com/majed3366/cartflow/pull/36) | Merchant Presentation Foundation V1 | `bd10cd4176917ce4804c1e2e5d0da85b1cd4b5b8` |

**Source commit:** `2f744c5` on `deploy/merchant-presentation-v1`  
**Migration:** Alembic `d3e4f5a6b7c8` → table `merchant_presentations`  
**Feature flag:** `CARTFLOW_MERCHANT_PRESENTATION_FOUNDATION_V1` (enabled)

---

## 2. Scope confirmed

| Check | Result |
|-------|--------|
| Consumes Guidance Routing only | **Pass** |
| Presentation + template registries | **Pass** (`mpres_v1`, `mtpl_v1`) |
| Expected presentation accounting | **Pass** — 11 = 11 ready |
| Claim boundaries | **Pass** — `claim_boundary_ok` |
| No Home presentation fields | **Pass** |
| Affordances do not execute | **Pass** |
| Deterministic | **Pass** |
| No merchant UI / Composition | **Pass** |

---

## 3. Production probe

```bash
python scripts/_verify_merchant_presentation_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true`

| Field | Value |
|-------|-------|
| `eligible_route_count` | 11 |
| `expected_presentation_count` | **11** |
| `ready_count` | **11** |
| `unaccounted_count` | 0 |
| `upserted` / `materialized_row_count` | **11** |
| `canonical_fingerprint` | `e297b12fc0f8d247cbd70e07f2255657fb3d9a8466845aa9decc519723291fa3` |

---

## 4. Registry samples

**Presentation types (Demo):** `executive_summary` (4), `decision_prompt` (4), `operational_notice` (3)  
**Templates:** `tpl_exec_investigate_v1`, `tpl_decision_investigate_v1`, `tpl_ops_investigate_v1`

---

## 5. Surface samples

| Surface | Type | Affordance | Notes |
|---------|------|------------|-------|
| Home | `executive_summary` | `navigate` | Summary slots; no known_facts list |
| Decision Workspace | `decision_prompt` | `review` | Full known/unknown facts |
| Carts | `operational_notice` | `inspect` | Operational wording |

**Home headline:** “Cart activity needs a closer look”  
**Decision known fact sample:** Cart additions newly appeared (d7)  
**Unknown fact sample:** No commercial root cause established  
**Prohibited claims:** Not rendered as advice (`claim_boundary_ok`)

---

## 6. Abstention / insufficient-evidence

Covered by unit tests (`no_guidance` / blocked → `abstention_state`). Demo live stock was all eligible `investigate_conversion_path` routes (no blocked routes in this snapshot).

---

## 7. Tests

`pytest tests/test_merchant_presentation_v1.py` → **10 passed**

---

## 8. STOP condition

**Merchant Presentation Foundation V1 is PRODUCTION CLOSED.**

Do **not** begin until reviewed and approved:

- Reusable Surface Composition
- Broad Home recomposition / Home guidance UI rollout
- Decision Workspace / Carts / Communication / Settings UI integration
- Merchant action execution
- Automatic actions
- AI-generated presentation or recommendations
