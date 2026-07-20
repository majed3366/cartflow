# Product Evidence Assembly Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-20  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `3f595237fa52281666d15eb8a1bbfd8fed75a9cf` (hotfix #24; builds on #23)

---

## 1. Pull requests merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#23](https://github.com/majed3366/cartflow/pull/23) | Product Evidence Assembly Foundation V1 | `31de19dbf8ccdc8f446f621cbefd99f1503349c1` |
| [#24](https://github.com/majed3366/cartflow/pull/24) | Fix source_record_id length for materialize | `3f595237fa52281666d15eb8a1bbfd8fed75a9cf` |

**Source commit:** `efb6651` (+ hotfix `ab013e1`)

---

## 2. Scope confirmed

| Check | Result |
|-------|--------|
| Inputs Metrics + Trends only | **Pass** — `inputs_metrics_and_trends_only=true` |
| No Signals / provider tables | **Pass** |
| No confidence / ranking / guidance | **Pass** |
| Lineage preserved | **Pass** — `source_layer`, `source_record_id`, lineage hashes |
| Deterministic assembly | **Pass** — `deterministic=true` |
| Refresh/materialize safe | **Pass** — upserted bundles/items; no DataError after #24 |
| No merchant UI | **Pass** |

---

## 3. Production deployment

| Item | Evidence |
|------|----------|
| Railway redeploy | Probe live after #23/#24 |
| `/health` | HTTP 200 |
| Home | HTTP 200 |
| `/dev/product-evidence-assembly` | HTTP 200 JSON |
| Kill switch | `CARTFLOW_PRODUCT_EVIDENCE_ASSEMBLY_V1=0` |

---

## 4. Verification script

```bash
python scripts/_verify_product_evidence_assembly_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true` (exit 0)

| Field | Value |
|-------|-------|
| `probe.table_exists` / `items_table_exists` | true |
| `probe.deterministic` | true |
| `probe.bundle_count` | **4** |
| `probe.item_count` | **10** |
| `probe.upserted_bundles` | **4** |
| `probe.upserted_items` | **10** |
| `probe.errors` | `[]` |
| `probe.migration_satisfied` | true |

---

## 5. Demo Merchant sample store bundle

`GET https://smartreplyai.net/dev/product-evidence-assembly?store=demo&assembly_window=d7`

| metric_key | metric_value | trend_direction | trend_window | source_layer |
|------------|-------------:|-----------------|--------------|--------------|
| `cart_abandoned_count` | 1 | `newly_appeared` | d7 | `metrics+trends` |
| `cart_added_count` | 7 | `newly_appeared` | d7 | `metrics+trends` |
| `evidence_linked_count` | 8 | `newly_appeared` | d7 | `metrics+trends` |

---

## 6. Acceptance checklist

| Criterion | Status |
|-----------|--------|
| Deterministic assembly | **Yes** |
| Canonical ownership | **Yes** |
| Metrics+Trends inputs only | **Yes** |
| Source lineage preserved | **Yes** |
| Bundle fingerprint stable (fixed `as_of`) | **Yes** |
| Refresh safe / recompute supported | **Yes** |
| Production probe + evidence | **Yes** |
| Documentation complete | **Yes** — `docs/architecture/product_evidence_assembly_v1.md` |

---

## 7. Closure

**Product Evidence Assembly Foundation V1 is CLOSED in production** with governed Demo evidence on 2026-07-20.

**STOP** — do not start Evidence Confidence / Knowledge / Commercial Guidance / merchant UI until owner confirms.
