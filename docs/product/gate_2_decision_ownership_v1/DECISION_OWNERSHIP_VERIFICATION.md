# Decision Ownership Verification — Gate 2

**Date (UTC):** 2026-07-24  
**Canonical owner:** Cart Workspace `#workspace`

---

## 1. Single Decision Engine (merchant paint)

| Layer | Role | Owner after Gate 2 |
|-------|------|--------------------|
| BFL materialization | Durable findings | Data (not UI) |
| Finding Decision Engine | `merchant_decision_v1` attach | Data (not UI) |
| CW enrichment | `enrich_projection_with_fde_v1` | **Sole business Decision mapper → UI** |
| CW card renderer | `cart_workspace_decision_card_v1.js` | **Sole business Decision paint** |
| MEIF `#meif-decision-root` | Legacy Decision paint | **Retired** (dual-stack OFF) |

**Verdict:** Exactly one merchant-facing Decision paint path — Cart Workspace. FDE/BFL remain the reasoning pipeline; they do not paint Home/Carts/Comms.

---

## 2. Surface verification matrix

| Surface | Business Decision paint? | Evidence |
|---------|--------------------------|----------|
| `#workspace` | **YES** — FDE cards in `zone_b` (`card_kind=business_finding`) + ops judgment cards | Enrichment + card renderer |
| `#home` (HES) | **NO** — teaser count/title only; CTA `عرض التفاصيل ← مساحة القرار` → `#workspace` | `compose_v1` + slim FDE teaser |
| `#home` (fat MEIF fallback) | **NO** — stub block + link to `#workspace`; no FDE explanation | `applyHome` Gate 2 |
| `#carts` | **NO** — MI recommendations / «يلزم إجراء» stripped; MEIF findings focus cleared | `merchant_intelligence_carts_v1.js` + `applyCarts` |
| `#communication` | **NO** — status facts only | `applyCommunication` |
| `#meif-decision-root` | **NO** (default) — `hidden` + empty unless `CARTFLOW_DECISION_DUAL_STACK_V1=1` | Template + `applyDecision` |

---

## 3. Constitution fields on Workspace cards

For `card_kind=business_finding`:

| Field | Source |
|-------|--------|
| Evidence | `evidence_summary` |
| Confidence | `decision_confidence` / `_ar` |
| Why | `explanation.why_here` |
| Impact | `expected_business_impact` |
| Recommended action | `required_merchant_action` |
| Status | `DECISION` / `NO_DECISION` (honest empty) |

Ops command buttons are **disabled** for business finding cards (`commands_enabled=false`; label-only CTA).

---

## 4. Canonical flow check

```text
Evidence
  → Business Finding (BFL)
  → Confidence (FDE)
  → Recommended Action (FDE)
  → Decision / NO DECISION (FDE)
  → Cart Workspace (sole UI)
  → Merchant
```

No alternate merchant path paints the same Decision.

---

## 5. Unit verification

`tests/test_decision_ownership_gate2_v1.py`:

- Dual-stack default OFF  
- FDE card map (decision + no-decision)  
- Enrich keeps ops cards; stamps `gate_2_single_decision_owner`  
- Home decisions `view_details_href=#workspace` + explicit CTA copy  

---

## 6. Production verification (live)

| Check | Result (`76b9728`) |
|-------|--------------------|
| `GET /api/cart-workspace/v1/projection` | `ok=true`, `gate_2_single_decision_owner=true`, mission constitutional |
| `#meif-decision-root` | `meif_hidden=true`, empty; `dual_stack=false` |
| Home decisions CTA | `view_details_href=#workspace`; CTA «عرض التفاصيل ← مساحة القرار»; MEIF absent on slim summary |
| Organic Workspace | Quiet state OK for new store (`business_finding_count=0`) |
| Screenshots | `after_desktop_workspace.png` · `after_mobile_workspace.png` · Home sanity pair |

Probe: `after_verification.json` (`ok=true`, status `AWAITING_CEO_REVIEW_BEFORE_GATE_2_CLOSE`).
