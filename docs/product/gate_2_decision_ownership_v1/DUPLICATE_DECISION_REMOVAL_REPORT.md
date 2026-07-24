# Duplicate Decision Removal Report — Gate 2

**Date (UTC):** 2026-07-24  
**Goal:** Exactly one decision pipeline for merchant business decisions.

---

## 1. Parallel stacks identified (pre–Gate 2)

| Stack | Surface | Status after Gate 2 |
|-------|---------|---------------------|
| **A — Cart Workspace ops + FDE enrich** | `#workspace` | **CANONICAL** — sole business Decision paint |
| **B — MEIF Decision root** | `#meif-decision-root` | **RETIRED** (default hidden; dual-stack rollback only) |
| **C — Home MEIF / HES decision explanation** | `#home` | **TEASER ONLY** — no explanation; CTA → Workspace |
| **D — Carts MI recommendations** | `#carts` | **STRIPPED** from paint (service may still compute; UI does not show) |
| **E — Communication MEIF findings** | `#communication` | **REMOVED** from paint |

---

## 2. Removals / migrations performed

| Item | Action | Notes |
|------|--------|-------|
| MEIF `applyDecision` | No-op when dual-stack OFF; root cleared + hidden | Painter kept for rollback / Gate 5 cleanup |
| `#meif-decision-root` | `hidden` in template when dual-stack OFF | `window.CARTFLOW_DECISION_DUAL_STACK_V1` |
| Home fat MEIF decision cards | Replaced with teaser + link to `#workspace` | No FDE explain on Home |
| Home HES decisions CTA | Explicit «عرض التفاصيل ← مساحة القرار» → `#workspace` | Gate 2 copy |
| Carts MI recommendation rows | Not rendered in story/group cards | Ops narrative kept |
| Carts MEIF findings focus | Cleared / hidden | Subcopy: decisions live in Workspace |
| Communication findings/decision blocks | Not painted | Status facts + message/WA links only |
| FDE → CW | **Migrated in** via `business_findings_enrichment_v1` | Restores Decision under HES slim (was missing) |

---

## 3. Intentionally kept (not Decision UI)

| Component | Why kept |
|-----------|----------|
| `finding_decision_engine_v1` | Reasoning data for Workspace |
| BFL / MEBF binding | Materialize + bind findings |
| `merchant_intelligence_v1` service | May still attach recommendations on API; **Carts UI must not paint business recommendations** |
| Recovery automation / admin | Non-merchant Decision surfaces (out of Gate 2 UI scope) |
| CW ops judgment cards | Operational decisions (take-over, VIP, discount) — coexist with business findings in Workspace |

---

## 4. Residual / deferred

| Item | Defer to |
|------|----------|
| Delete MEIF Decision painter JS entirely | Gate 5 legacy retirement |
| Full Carts ops-only (remove all MI meaning narratives if required) | Gate 3 |
| Communication merge | Gate 4 |
| Product Intelligence hosting in Workspace | Gate 7 + separate PI auth |

---

## 5. Rollback

Set `CARTFLOW_DECISION_DUAL_STACK_V1=1` to temporarily show MEIF Decision root beside Cart Workspace. Default remains **OFF**.

---

## 6. Verification statement

After Gate 2 deploy: **no duplicate merchant business Decision UI** remains in production. Home / Carts / Communication do not explain or own Decisions. Cart Workspace is the sole constitutional Decision Owner.
