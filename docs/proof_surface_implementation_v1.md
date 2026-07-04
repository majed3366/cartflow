# CartFlow Proof Surface Implementation V1

**Date (UTC):** 2026-07-04  
**Status:** Implemented — presentation only  
**Governance:** [`proof_of_value_governance_v1.md`](proof_of_value_governance_v1.md)  
**Foundation:** [`proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md)

---

## Executive summary

Proof Surface V1 is the **first Value Delivery Era implementation sprint**. It surfaces **existing** engineering truth on merchant-visible dashboard rows and Knowledge Layer cards — without new intelligence, new claims, or changes to Purchase Truth, Lifecycle Truth, Provider Reliability, Snapshot Generation, or Dashboard Read Model logic.

**Verdict:** Presentation-only compliance pass — PV-11 honored (acceptance ≠ delivery); PV-5 honored (unknown delivery stays unknown); PV-7 partial (`proof_source` = `recovery_key` on cart rows).

---

## Phase 1 — Proof Surface Inventory

| Surface | Existing evidence | Missing proof (pre-V1) | Confidence (post-V1) | Owner |
|---------|-------------------|------------------------|------------------------|-------|
| **Carts lifecycle block** (`#carts`) | LT-C1 fields, reason chip | Why we know; recovery chain | **Confirmed** for lifecycle; weakest-link for bundle | Presentation: `merchant_dashboard_lazy.js` |
| **Recovery status (row)** | `merchant_whatsapp_line_ar`, logs | Delivery vs acceptance | **Unknown** until Provider Truth row exists | `merchant_proof_surface_v1` |
| **Knowledge cards** (`#home`) | KL insight + `ins.confidence` | Evidence type label | KL-native confidence shown | `merchant_knowledge_layer.js` |
| **Home weekly reasons** | Reason distribution | Proof metadata | Unchanged (aggregate only) | Snapshot summary |
| **VIP tab** | VIP lane + alert | Delivery proof | Not in V1 scope (normal carts only) | VIP batch |
| **Monthly summary** | Recovery highlights | Attributed SAR | Unchanged (**Future** PV-3) | `#home-month` |
| **Daily Brief** | — | Not implemented | **Future** PV-18 | — |
| **Recovery timeline** | Messages API timeline | Not on cart row | **Future** dedicated surface | — |

---

## Phase 2 — Proof Mapping

| Merchant claim (wording) | Truth owner | Evidence | Confidence | Merchant wording |
|--------------------------|-------------|----------|------------|------------------|
| Lifecycle state label | LT-C1 | `customer_lifecycle_*` | Confirmed | «الحالة: …» (existing) |
| What happened | LT-C1 | `customer_lifecycle_what_happened_ar` | Confirmed | «ماذا حدث؟» (existing) |
| Scheduling step | Recovery Truth | schedules / `next_attempt_due_at` | Medium–Confirmed | «جدولة الإرسال: …» |
| Provider accepted message | Recovery Truth | `sent_real` / `mock_sent` logs | Confirmed | «قبول المزود للرسالة: تم» + note acceptance ≠ delivery |
| Message delivered to customer | Provider Truth | `WhatsAppDeliveryTruth` via `message_sid` | Confirmed / Unknown | «تسليم الرسالة للعميل: …» — never «تم» without delivery evidence |
| Customer purchased | Purchase Truth | `purchase_truth` / completed variant | Confirmed | «إتمام الشراء: تم» |
| Recovery stopped | Recovery + Lifecycle | stop logs / terminal states | Medium–Confirmed | «إيقاف مسار الاسترجاع: …» |
| KL insight | Knowledge Layer | `/api/knowledge/report` | high/medium/low/insufficient | «مستوى الثقة: … · نوع الدليل: Knowledge Layer» |

---

## Phase 3 — Proof Presentation Rules

Every proof surface block answers (implementation behavior, not UI redesign):

1. **What happened?** — lifecycle block (existing) + optional `what_happened_ar` in bundle  
2. **Why do we know?** — `why_we_know_ar` composed from lifecycle state, reason capture, purchase truth, send log  
3. **What evidence supports it?** — `evidence_source_ar` + recovery step list with `evidence_type` per step  
4. **What is the current confidence?** — `confidence_ar` on bundle; per-step confidence on recovery steps  

**Rules:**

- Proof block appended **below** lifecycle block in expanded cart row — no layout redesign  
- KL cards append proof meta footer — no card structure change  
- No new KPIs, charts, or ROI numbers  
- VIP lane rows: attach skipped when `merchant_cart_fact_v1` is None (VIP) — same attach runs but domain may differ  

---

## Phase 4 — Recovery Proof Surface (implemented)

Recovery steps in `merchant_proof_surface_v1.recovery_steps`:

| Step key | Source | PV compliance |
|----------|--------|---------------|
| `scheduled` | `next_attempt_due_at`, log statuses, `sent_count` | Recovery Truth |
| `message_accepted` | `sent_real` / `mock_sent` | PV-11 — labeled acceptance, not delivery |
| `provider_delivered` | `get_delivery_truth(provider_message_sid)` read-only | PV-11 — Unknown if no delivery row |
| `customer_purchased` | Purchase Truth flag | PV-2 |
| `recovery_stopped` | stop logs + lifecycle terminal | Recovery Truth |

---

## Phase 5 — Evidence Visibility (implemented)

Cart row JSON adds `merchant_proof_surface_v1`:

```json
{
  "version": "v1",
  "primary_domain": "understanding",
  "confidence": "confirmed",
  "confidence_ar": "مؤكد",
  "evidence_type": "lifecycle_truth",
  "evidence_source_ar": "حالة دورة العميل (Lifecycle Truth)",
  "proof_source": "store:session",
  "why_we_know_ar": "...",
  "recovery_steps": [ ... ]
}
```

Merchant dashboard renders Arabic labels only — no internal module names in UI.

---

## Phase 6 — Compliance Verification

| Contract | Status |
|----------|--------|
| PV-1 evidence-backed | **Pass** — bundle maps to Tier 0 sources |
| PV-11 acceptance ≠ delivery | **Pass** — delivery step Unknown without Provider Truth; acceptance note explicit |
| PV-5 unknown stays unknown | **Pass** |
| PV-7 proof source | **Partial** — `recovery_key` on row |
| PV-3 attributed SAR | **N/A** — not surfaced |
| PV-17 eligible actions | **Unchanged** — existing decision layer |
| CI-1 fake ROI | **Pass** — no ROI metrics added |
| CI-3 fake delivered | **Pass** |
| CI-6 hidden uncertainty | **Pass** — Unknown labeled |

---

## Phase 7 — Regression Protection

| Area | Verified |
|------|----------|
| Purchase Truth | **No changes** |
| Lifecycle Truth LT-C1 | **No changes** — attach reads fields only |
| Provider Reliability | **Read-only** `get_delivery_truth` lookup |
| Recovery scheduling / send | **No changes** |
| Snapshot generation | **No changes** — slim allowlist extended only |
| Dashboard read model | **No changes** |
| Merchant workflow | **No changes** — archive/reopen/filters unchanged |

**Tests:** `tests/test_merchant_proof_surface_v1.py`

---

## Implementation files

| File | Role |
|------|------|
| `services/merchant_proof_surface_v1.py` | Read-only proof composition |
| `main.py` | `attach_merchant_proof_surface_v1` on normal-carts row build |
| `services/dashboard_snapshot_normal_carts_slim_v1.py` | Allowlist `merchant_proof_surface_v1` |
| `static/merchant_dashboard_lazy.js` | Render `merchantProofSurfaceHtml` |
| `static/merchant_knowledge_layer.js` | KL confidence + evidence type footer |
| `static/merchant_app.css` | Minimal proof surface styles |

---

## Known gaps (unchanged by design)

- Attributed Recovered Revenue (PV-3) — not surfaced  
- Daily Brief (PV-18) — not implemented  
- VIP cart proof block — deferred  
- Fleet-wide proof quality metrics (governance §7) — internal **Future**

---

## Success criteria

| Criterion | Met |
|-----------|-----|
| Merchant sees existing value more clearly | **Yes** — recovery chain + why we know on cart rows |
| No new intelligence | **Yes** |
| No unsupported claims | **Yes** — PV-11 / CI-3 enforced |
| Merchant trust via visible proof | **Partial uplift** — foundation for Level 2 Proven |

**Next:** Proof Surface V2 — attributed SAR when PV-3 implementation approved; Daily Brief surface when PV-18 implementation approved.
