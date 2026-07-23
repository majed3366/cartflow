# Evidence Confidence Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-20  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `8c77b2dadbd057af5a9493e6218790f9a36382b3` (PR #26)

---

## 1. Pull request merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#26](https://github.com/majed3366/cartflow/pull/26) | Evidence Confidence Foundation V1 | `8c77b2dadbd057af5a9493e6218790f9a36382b3` |

**Source commit:** `81cc4b2` on `deploy/evidence-confidence-v1`

---

## 2. Scope confirmed

| Check | Result |
|-------|--------|
| Consumes Evidence Assembly only | **Pass** — `inputs_evidence_assembly_only=true` |
| No Signals/Metrics/Trends/provider reads | **Pass** (via PEA API only) |
| No knowledge / guidance / ranking / health | **Pass** |
| Deterministic evaluation | **Pass** — `deterministic=true` |
| Versioned (`ecf_v1` / `ecf_v1_eval`) | **Pass** |
| Refresh/materialize | **Pass** — upserted=4, errors=[] |
| No merchant UI | **Pass** |

---

## 3. Production deployment

| Item | Evidence |
|------|----------|
| Railway redeploy | Probe live after PR #26 |
| `/health` | HTTP 200 |
| Home | HTTP 200 |
| `/dev/evidence-confidence` | HTTP 200 JSON |
| Kill switch | `CARTFLOW_EVIDENCE_CONFIDENCE_V1=0` |

---

## 4. Verification script

```bash
python scripts/_verify_evidence_confidence_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true` (exit 0)

| Field | Value |
|-------|-------|
| `probe.table_exists` | true |
| `probe.deterministic` | true |
| `probe.evaluation_count` | **4** |
| `probe.upserted` | **4** |
| `probe.errors` | `[]` |
| `probe.migration_satisfied` | true |

---

## 5. Demo Merchant sample store evaluation

`GET https://smartreplyai.net/dev/evidence-confidence?store=demo&assembly_window=d7`

| Field | Value |
|-------|-------|
| `confidence_level` | `very_high` |
| `confidence_score` | **95** |
| `completeness` | 75 |
| `freshness` | 100 |
| `consistency` | 100 |
| `source_diversity` | 100 |
| `sample_size` | 100 |
| `missing_sources` | `["purchase_count"]` |
| `conflicting_signals` | false |

---

## 6. Acceptance checklist

| Criterion | Status |
|-----------|--------|
| Deterministic evaluation | **Yes** |
| Provider-independent | **Yes** |
| Evidence Assembly only | **Yes** |
| Stable confidence identities | **Yes** |
| Versioned evaluation | **Yes** |
| Refresh/recompute | **Yes** |
| Production probe + evidence | **Yes** |
| Documentation complete | **Yes** — `docs/architecture/evidence_confidence_foundation_v1.md` |

---

## 7. Closure

**Evidence Confidence Foundation V1 is CLOSED in production** with governed Demo evidence on 2026-07-20.

**STOP** — do not start Knowledge / Commercial Guidance / merchant UI until owner confirms.
