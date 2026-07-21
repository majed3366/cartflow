# Commerce Intelligence Synthesis V1 — Deferred Dependencies

**Status:** Tracked (not abandoned)  
**Date (UTC):** 2026-07-22  
**Parent:** Commerce Intelligence Synthesis Foundation V1  

These items are **temporary upstream dependency gaps**. They produce truthful `blocked` candidates with governed reason codes. They must not be silently dropped.

---

## D-CISYN-01 — Message strategy classification contract

| Field | Value |
|-------|--------|
| Synthesis rule | `discount_message_weakness` |
| Blocked reason | `upstream_truth_incomplete` |
| Missing | `message_strategy_classification` |
| Owner layer | `message_strategy_classification` (not yet a cisrc_v1 contract) |
| Why deferred | V1 source registry has no governed message-strategy classification; inventing one from raw WhatsApp/template text would violate provider-independence and claim boundaries |
| Demo behavior | On `d7`: also `temporal_alignment_failed` (rule allows d14/d30/d60 only). On `d14+` with hesitation+signals: blocked deferred until contract exists |
| Exit criteria | Canonical `message_strategy_classification` contract registered in `cisrc_v1` with subject types and timestamp authority |

---

## D-CISYN-02 — VIP follow-up comparison cohorts

| Field | Value |
|-------|--------|
| Synthesis rule | `vip_followup_outcome` |
| Blocked reason | `comparison_cohort_unavailable` |
| Missing | `comparable_vip_followup_cohorts` |
| Owner layer | `vip_followup_comparison_cohorts` |
| Why deferred | Comparative merchant-vs-automated VIP outcomes require a governed comparison contract (inclusion/exclusion, min group size, comparable windows). Not available in V1 without fabricating cohorts |
| Demo behavior | On `d7`: `temporal_alignment_failed` (rule allows d14+). On `d14+` with commerce_signals: blocked deferred |
| Exit criteria | Canonical VIP comparison cohort materialization accepted by cisrc_v1 + comparison governance fields populated |

---

## Non-deferred expected blocks (not tracked as debt)

| Rule | Reason | Why expected |
|------|--------|--------------|
| `shipping_hesitation_recovery_outcome` | `required_source_data_unavailable` | Demo window has no in-window shipping hesitation mappings (`product_hesitation` empty) |
| `discount_message_weakness` / `vip_followup_outcome` on `d7` | `temporal_alignment_failed` | Registry `allowed_windows` exclude `d7` by design |

---

## Governance

- Do not bypass deferred gaps with provider-specific or raw payload reads.
- Do not mark deferred rules `active=false` without an explicit product decision.
- Closure validation requires `blocked_defect=0` and `blocked_runtime_misclassified=0`.
