# Guidance Routing Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-21  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `b4a4a0b0e519ad2ce2341fd9a3d5feab187d7718` (PR #34)

---

## 1. Pull request merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#34](https://github.com/majed3366/cartflow/pull/34) | Guidance Routing Foundation V1 | `b4a4a0b0e519ad2ce2341fd9a3d5feab187d7718` |

**Source commit:** `44e4637` on `deploy/guidance-routing-v1`  
**Migration:** Alembic `c2d3e4f5a6b7` → table `guidance_routes`

---

## 2. Scope confirmed

| Check | Result |
|-------|--------|
| Consumes Commercial Guidance only | **Pass** |
| Surface + routing registries | **Pass** (`gsurf_v1`, `grule_v1`) |
| Expected route accounting | **Pass** — 20 = 11+9+0+0+0+0 |
| No silent route loss | **Pass** — `unaccounted_route_count=0` |
| No Home presentation fields | **Pass** |
| Deterministic | **Pass** |
| No merchant UI / Presentation | **Pass** |

---

## 3. Production probe

```bash
python scripts/_verify_guidance_routing_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true`

| Field | Value |
|-------|-------|
| `guidance_count` | 4 |
| `expected_route_pairs` | **20** |
| `eligible_route_count` | **11** |
| `ineligible_route_count` | **9** |
| `upserted` / `materialized_row_count` | **20** |
| `canonical_fingerprint` | `82261da7956e7daf852bbaf36118f80907b9c7b9ac47af452bea0adfb9e61ffd` |

---

## 4. Surface registry sample

Active: `home`, `decision_workspace`, `carts`, `communication`, `settings`

---

## 5. Route samples (Demo)

| Surface | Scope | Role | Status |
|---------|-------|------|--------|
| Home | `summary` | `awareness` | eligible |
| Decision Workspace | `full_context` | `investigation` | eligible |
| Carts | `operational` | `operational_attention` | eligible |
| Settings | `internal_only` | `suppressed` | ineligible |
| Communication | `internal_only` | `suppressed` | ineligible |

Guidance key: `investigate_conversion_path` (product subjects).

---

## 6. By-surface accounting

| Surface | eligible | ineligible |
|---------|----------|------------|
| home | 4 | 0 |
| decision_workspace | 4 | 0 |
| carts | 3 | 1 |
| communication | 0 | 4 |
| settings | 0 | 4 |

---

## 7. Tests

`pytest tests/test_guidance_routing_v1.py` → **12 passed**

---

## 8. STOP condition

**Guidance Routing Foundation V1 is PRODUCTION CLOSED.**

Do **not** begin until reviewed and approved:

- Merchant Presentation
- Home / Decision Workspace / Carts / Communication / Settings UI
- merchant-facing guidance components
- automatic actions
- AI routing or presentation
