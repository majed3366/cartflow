# Commercial Guidance Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-21  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `5990835eff7ed78f13b5b007d853bb76bec700b5` (PR #32)

---

## 1. Pull request merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#32](https://github.com/majed3366/cartflow/pull/32) | Commercial Guidance Foundation V1 | `5990835eff7ed78f13b5b007d853bb76bec700b5` |

**Source commit:** `36602c1` on `deploy/commercial-guidance-v1`  
**Migration:** Alembic `b1c2d3e4f5a6` → table `commercial_guidance_records`

---

## 2. Scope confirmed

| Check | Result |
|-------|--------|
| Consumes Guidance Eligibility only | **Pass** — `consumes_guidance_eligibility_only=true` |
| Eligibility `knowledge_context` used (no KF table bypass) | **Pass** |
| Registry-bounded keys only | **Pass** — `registry_valid=true` |
| Deterministic generation | **Pass** — `deterministic=true` |
| Known / unknown / prohibited separated | **Pass** — sample records |
| No root-cause / action invention | **Pass** — prohibited_claims present; keys investigate/monitor only |
| No merchant UI / routing / AI / actions | **Pass** |
| Refresh/materialize | **Pass** — upserted=4, errors=[] |

---

## 3. Production deployment

| Item | Evidence |
|------|----------|
| `/health` | HTTP 200 |
| `/dev/commercial-guidance?store=demo` | HTTP 200 JSON |
| Kill switch | `CARTFLOW_COMMERCIAL_GUIDANCE_FOUNDATION_V1=0` |

---

## 4. Verification script

```bash
python scripts/_verify_commercial_guidance_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true` (exit 0)

| Field | Value |
|-------|-------|
| `probe.table_exists` | true |
| `probe.deterministic` | true |
| `probe.guidance_count` | **4** |
| `probe.active_count` | **4** |
| `probe.deferred_count` | 0 |
| `probe.abstained_count` | 0 |
| `probe.upserted` | **4** |
| `probe.materialized_row_count` | **4** |
| `probe.errors` | `[]` |
| `probe.canonical_fingerprint` | `a6d25823b85099573583ac9d9c9c5843ae03601557da62ff9563b8854f1ec6ad` |

---

## 5. Registry sample (active keys)

`continue_observing`, `defer_until_more_evidence`, `investigate_conversion_path`, `monitor_new_pattern`, `no_guidance`, `review_cart_progression`, `review_product_experience`, `verify_evidence_gap`

---

## 6. Eligible sample (Demo product subject)

| Field | Value |
|-------|-------|
| `guidance_key` | `investigate_conversion_path` |
| `guidance_status` | `active` |
| `rationale_code` | `rule:intent_without_purchase_evidence` |
| `eligibility_status` | `eligible` |
| Known facts (sample) | Cart additions newly appeared (d7); Evidence does not include purchase_count |
| Unknown facts | No commercial root cause established |
| Prohibited claims | No specific root cause; no price/discount/campaign recommendations |

---

## 7. Abstained sample (unit / contract)

Ineligible eligibility statuses produce `guidance_key=no_guidance`, `guidance_status=abstained`, rationale `abstain:<status>` (covered in `tests/test_commercial_guidance_v1.py`).

---

## 8. Lineage sample

| Field | Example |
|-------|---------|
| `eligibility_id` | `8a4b6a24454c3474376615a401928f71` |
| `knowledge_reference_ids` | 5 ids on product sample |
| `rule_version` | `cgf_rule_investigate_conversion_v1` |
| `source_contract_version` | `gef_v1_guidance_context` |

---

## 9. Tests

`pytest tests/test_commercial_guidance_v1.py` → **13 passed** (eligibility-only import guard, abstention, investigate/monitor rules, determinism, materialize, flag-off, unsupported key reject, claim boundaries).

---

## 10. Acceptance checklist

| Criterion | Status |
|-----------|--------|
| Architecture documented | **Pass** |
| Eligibility-only input | **Pass** |
| Canonical registry | **Pass** |
| Deterministic rules | **Pass** |
| Claim boundaries | **Pass** |
| Explicit abstention | **Pass** |
| Stable fingerprints | **Pass** |
| Refresh/recompute | **Pass** |
| Feature flag + probe | **Pass** |
| Demo production verification | **Pass** |
| No merchant UI | **Pass** |

---

## 11. STOP condition

**Commercial Guidance Foundation V1 is PRODUCTION CLOSED.**

Do **not** begin until this layer is reviewed and approved:

- Guidance Routing
- Merchant Presentation
- Dashboard / Home guidance UI
- Decision Workspace integration
- Automatic actions
- AI-generated guidance
