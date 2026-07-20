# Knowledge Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-21  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `9a09a7beedea7c6aabbc993346e1fdd4c453f2c2` (PR #28)

---

## 1. Pull request merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#28](https://github.com/majed3366/cartflow/pull/28) | Knowledge Foundation V1 | `9a09a7beedea7c6aabbc993346e1fdd4c453f2c2` |

**Source commit:** `2ce04a0` on `deploy/knowledge-foundation-v1`

---

## 2. Scope confirmed

| Check | Result |
|-------|--------|
| Consumes Evidence Confidence only | **Pass** — `inputs_evidence_confidence_only=true` |
| Every statement refs `evidence_confidence_id` | **Pass** — `all_statements_reference_confidence=true` |
| No guidance / recommendations / decisions | **Pass** |
| Deterministic generation | **Pass** — `deterministic=true` |
| Refresh/materialize | **Pass** — upserted=20, errors=[] |
| No merchant UI | **Pass** |

---

## 3. Production deployment

| Item | Evidence |
|------|----------|
| Railway redeploy | Probe live after PR #28 |
| `/health` | HTTP 200 |
| Home | HTTP 200 |
| `/dev/knowledge-foundation` | HTTP 200 JSON |
| Kill switch | `CARTFLOW_KNOWLEDGE_FOUNDATION_V1=0` |

---

## 4. Verification script

```bash
python scripts/_verify_knowledge_foundation_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true` (exit 0)

| Field | Value |
|-------|-------|
| `probe.table_exists` | true |
| `probe.deterministic` | true |
| `probe.statement_count` | **20** |
| `probe.upserted` | **20** |
| `probe.errors` | `[]` |
| `probe.migration_satisfied` | true |

---

## 5. Demo Merchant sample statements (store grain)

| Type | Statement |
|------|-----------|
| `evidence_quality` | Evidence quality is very_high. |
| `evidence_gap` | Evidence does not include purchase_count. |
| `metric_trend_observation` | Cart additions have newly appeared during the last 7 days. |
| `metric_trend_observation` | Cart abandonments have newly appeared during the last 7 days. |
| `metric_trend_observation` | Evidence-linked events have newly appeared during the last 7 days. |

All sample rows include non-empty `evidence_confidence_id` and `confidence_level=very_high`.

---

## 6. Acceptance checklist

| Criterion | Status |
|-----------|--------|
| Deterministic knowledge generation | **Yes** |
| Evidence Confidence only | **Yes** |
| Confidence evaluation reference | **Yes** |
| Traceable / stable fingerprints | **Yes** |
| Refresh/recompute | **Yes** |
| Production probe + evidence | **Yes** |
| Documentation complete | **Yes** — `docs/architecture/knowledge_foundation_v1.md` |

---

## 7. Closure

**Knowledge Foundation V1 is CLOSED in production** with governed Demo evidence on 2026-07-21.

**STOP** — do not start Commercial Guidance / recommendations / merchant-facing knowledge UI until owner confirms.
