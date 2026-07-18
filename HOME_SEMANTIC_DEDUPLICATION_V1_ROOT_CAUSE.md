# Home Repetition Root-Cause & Semantic Deduplication V1

**Date (UTC):** 2026-07-18  
**Status:** Production fix deployed — await Product Experience Review  

---

## 1. Root cause (ownership)

| Layer | Verdict |
|-------|---------|
| **Commercial Interpretation Layer** (`commercial_interpretation_v1.apply_commercial_interpretation_to_home_v1`) | **PRIMARY** — intentionally fans one truth (`missing_contact_blocks_recovery_v1`) into Priority + Revenue Risk + Understanding |
| **Daily Brief finalize** (`merchant_home_composition_v1.finalize_home_daily_business_brief_v1`) | **AMPLIFIER** — Health + Learning re-derive contact language from `has_primary_risk` / `no_phone` |
| **Pre-CIL `seen_facts`** | Incomplete — runs before CIL injects; does not cover Risk/Health/Learning |
| **Adaptive Cognition** | Not causal for content — previously only reordered sections |
| **JS / Reality Fix** | Not causal for semantic repetition |

**Defect class:** Independent section selectors + missing semantic identity + missing Home-level composition authority after CIL.

---

## 2. Per-surface trace (contact scenario)

| Surface | Source | IDs | Knew prior show? | Why no dedupe |
|---------|--------|-----|------------------|---------------|
| Health | finalize from `no_phone` / `has_primary_risk` | none | indirect | Regenerates condition + evidence line |
| Priority | CIL `interpretation_to_attention_decision_v1` | `decision:obtain_contact`, CIL id | no | Designed as action role |
| Risk | CIL `interpretation_to_revenue_risk_item_v1` | same CIL id | no | Designed as risk role (same truth) |
| Understanding | CIL `interpretation_to_home_understanding_item` | same CIL id | no | Designed as explain role (same truth) |
| Opportunity | finalize `recoverable_with_contact` | different fact_key | weak blocklist | Inverse of same problem |
| Learning | finalize hardcodes contact pattern | `fact:learning:contact_blocker_pattern` | skips CIL und row only | Still ships its own paraphrase |
| Timeline | activity timeline | filtered | yes via `seen_facts` | Already mostly clean |

---

## 3. Fix

New composition authority: `services/home_semantic_composition_v1.py`

1. Canonical `semantic_identity_v1` on every card  
2. Cognitive roles: condition / action / explain / risk / opportunity / learning / event  
3. Progressive disclosure: one problem may keep **condition + action + explain** only  
4. Suppress semantic duplicates, inverse opportunity, learning restatement, timeline echoes  
5. ACF path eligibility filters `section_order` to admitted sections only  
6. JS `sectionAdmitted` — never re-appends suppressed sections  

Wired at end of `finalize_home_daily_business_brief_v1`; path filter in ACF attach.

---

## 4. Contact scenario — after composition

**Survives:** Health (condition) → Priority (action) → Understanding (explain)  
**Suppressed:** Revenue Risk, Opportunity (inverse), Learning (paraphrase), Timeline contact echoes  

Evidence: `HOME_SEMANTIC_DEDUPLICATION_V1_EVIDENCE.json`

---

## 5. STOP

Await Product Experience Review. No Wireframe. No new Home features.
