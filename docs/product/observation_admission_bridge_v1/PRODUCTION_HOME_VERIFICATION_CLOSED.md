# Production Home Verification — CLOSED

**Date (UTC):** 2026-07-25  
**Deploy:** PR [#101](https://github.com/majed3366/cartflow/pull/101) → `68b58f7`  
**Living Store prod run:** `srs_68ff9ac5019849f9a693cb0a917fa638`

---

## Objective answers

| Question | Answer |
|----------|--------|
| Where did the **original** `living_store_reality_v1.py` run? | **Local** SQLite tempfile — not staging/production |
| Which `store_slug` received that lab mass? | **`demo`** |
| Was the reviewed production Home that same store? | **No** — fresh signup (`oab-…`) until review session |
| Why did “Home-visible = 4” not appear in production? | Count was local compose; prod `demo` unseeded; Home auth = signup primary |

---

## Production path after closure

```
POST /dev/living-store-reality-run  →  production DB store_slug=demo (wall-clock)
        ↓
Observation Foundation  →  4 statement capabilities ready
        ↓
ORV admission           →  findings_count=4 · silent_drops=0
        ↓
POST /dev/living-store-home-review-session  →  primary_store_id=demo
        ↓
GET /api/dashboard/summary  →  store_slug=demo · observations count=4 · empty=false
        ↓
Browser /dashboard#home  →  Product Observations badge 4 · Raven teaser visible
```

---

## Exact admitted observations (production `demo`)

From `GET /dev/observation-reality-validation?store=demo` / job observation:

1. **high_interest_low_conversion** — Raven — حزام جلد للساعة  
2. **shipping_stronger_than_price** — TrueSound — سماعة لاسلكية  
3. **repeated_return_without_purchase** — Raven — حزام جلد للساعة  
4. **no_quality_issue_evidence** — Horizon Steel / Velvet Musk (admission pick)

Reconciliation: foundation 4 → ORV 4 → Home-visible 4 → Workspace 3.

---

## Exact Home executive API (demo-primary session)

From `prod_home_verify_after.json` → `home_api_probe`:

| Field | Value |
|-------|-------|
| `store_slug` | `demo` |
| `obs_count` | `4` |
| `obs_empty` | false |
| `obs_summary` | المنتج Raven — حزام جلد للساعة: يحظى باهتمام واضح، لكن التحويل إلى شراء لا يزال منخفضاً. |
| `text_has_raven` | true |

---

## Visual evidence

| Asset | Result |
|-------|--------|
| `prod_before_empty_desktop_home.png` | Empty / insufficient-evidence (signup store) |
| `prod_after_desktop_home.png` | Observations **4** + Raven teaser |
| `prod_after_mobile_home.png` | Observations **4** + Raven teaser |
| `prod_home_verify_after.json` | Full API/path probe |

Review URL (sets demo-primary cookie):  
https://smartreplyai.net/dev/living-store-home-review

---

## First divergence (historical)

Local Living Store → local `demo` ORV ✓ → report measured direct HES compose ✓  
→ Home API / browser session store ≠ that `demo` ✗  
→ production never seeded ✗  

**Closed** by wall-clock prod seed + demo-primary review session.
