# Product Signal Collection V1 — Production Closure Evidence

**Date (UTC):** 2026-07-20  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `d85234af7cd5c2b56c51064f819115353d4701fe` (allowlist hotfix #17; builds on #15/#16)

---

## 1. Pull requests merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#15](https://github.com/majed3366/cartflow/pull/15) | Product Signal Collection V1 | `6c05db47689165d01873ea11c589d81672deb885` |
| [#16](https://github.com/majed3366/cartflow/pull/16) | Production closure probe | `82e776872db7bcdf4cda231f479de9efcbb5c18e` |
| [#17](https://github.com/majed3366/cartflow/pull/17) | Allow probe in production `/dev` middleware | `d85234af7cd5c2b56c51064f819115353d4701fe` |

**Source implementation commit:** `0109a6e` on `deploy/product-signal-collection-v1`

---

## 2. Pre-merge review (accepted)

| Check | Result |
|-------|--------|
| Unintended schema changes | **Pass** — additive `product_signal_events` only |
| Duplicate writes | **Pass** — unique `dedup_hash` + exists check |
| Merchant isolation | **Pass** — `store_slug` required; collectors store-scoped |
| Idempotency | **Pass** — dedup hash includes identity + window second |
| Transaction safety | **Pass** — nested savepoint + commit; hooks never raise |
| Kill-switch | **Pass** — `CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1=0` |
| Regression risk | **Pass** — additive hooks; no merchant UI |

---

## 3. Production deployment

| Item | Evidence |
|------|----------|
| Railway redeploy | Confirmed by operator from `main`; probe live after #17 allowlist |
| Production identifier | Host `https://smartreplyai.net` — GitHub `main` @ `d85234a` |
| `/health` | HTTP 200 |
| Home | HTTP 200 |
| `/dev/purchase-truth-trace` | HTTP 200 (existing path) |
| `/dev/product-signal-collection` | HTTP 200 JSON (after #17 allowlist) |
| No new merchant UI | Confirmed — diagnostic `/dev` only |

---

## 4. Verification script

```bash
python scripts/_verify_product_signal_collection_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true` (exit 0)

| Field | Value |
|-------|-------|
| `http_status_cart_event` | 200 |
| `http_status_probe` | 200 |
| `cart_event_ok` | true |
| `probe.table_exists` | true |
| `probe.total` | 14 (final closure run; grew from prior Demo activity) |
| `probe.duplicate_dedup_hash_groups` | 0 |
| `probe.evidence_linked.missing_refs` | 0 |
| `probe.collection_enabled` | true |
| `probe.migration_satisfied` | true |

Example session from final script: `psc-verify-a23ae6eae25f`

---

## 5. Demo Merchant signal counts (final probe)

`GET https://smartreplyai.net/dev/product-signal-collection?store=demo`

| Metric | Value |
|--------|-------|
| `store_slug` | `demo` |
| `table_exists` | true |
| `total` | **14** |
| `non_demo_row_count` | **0** |
| `all_probe_rows_match_store` | true |
| `duplicate_dedup_hash_groups` | **0** |
| `collection_enabled` | true |

### By `signal_type`

| signal_type | count |
|-------------|------:|
| `product_cart_added` | 6 |
| `product_cart_abandoned` | 1 |
| `product_evidence_linked` | 7 |

### Evidence-linked validation

| Field | Value |
|-------|------:|
| `evidence_linked.count` | 7 |
| `evidence_linked.with_valid_refs` | 7 |
| `evidence_linked.missing_refs` | **0** |

All evidence-linked samples include non-empty `evidence_ref_type` + `evidence_ref_id` (e.g. `session` / session id).

### Store isolation

- Probe filters exclusively on `store_slug=demo`.
- `non_demo_row_count == 0` (no rows for other stores in table at probe time).
- Sample rows all tied to Demo sessions (`psc-verify-*`, `psc-closure-*`).

### Deduplication

- `duplicate_dedup_hash_groups == 0` — no duplicate `dedup_hash` groups for Demo.

---

## 6. Migration status

| Check | Result |
|-------|--------|
| Target revision | `u4v5w6x7y8z9` |
| `alembic_version` stamp | `null` (not stamped on this host) |
| `alembic_stamped_exact` | false |
| `product_signal_events` table | **exists** |
| `migration_satisfied` | **true** |

**Interpretation:** Production created the table via runtime `ensure_product_signal_events_schema` / `create_all` (same pattern as Product Data Foundation mapping tables). Formal Alembic stamp to `u4v5w6x7y8z9` remains optional ops hygiene:

```bash
railway run --service <API> alembic upgrade u4v5w6x7y8z9
```

---

## 7. Governed Demo activity exercised

Supported paths used for closure (no new UI):

1. `POST /api/cart-event` `event=cart_state_sync` `reason=add` + `lines[]` (multiple verify sessions)
2. `POST /api/cart-event` `event=cart_abandoned` + `lines[]` (session `psc-closure-19ebb84406`)

Observed signal types from those paths: `product_cart_added`, `product_cart_abandoned`, `product_evidence_linked`.

---

## 8. Acceptance checklist

| Criterion | Status |
|-----------|--------|
| PR merged into main | **Yes** (#15, #16, #17) |
| Production deployment succeeds | **Yes** |
| Migration / table available | **Yes** (`migration_satisfied`; table present) |
| Verification script passes | **Yes** (`ok: true`) |
| Demo Merchant signals persisted | **Yes** (total 14) |
| Signal ownership / store isolation | **Yes** (`demo` only; `non_demo_row_count=0`) |
| No duplicate / malformed signals | **Yes** (dedup groups 0; evidence refs valid) |
| No merchant experience regression | **Yes** (home/health/existing `/dev` paths 200) |
| No new merchant UI | **Yes** |
| Production evidence documented | **Yes** (this file) |

---

## 9. Failure handling (armed)

If regression is detected later:

```text
CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1=0
```

Do **not** silently delete `product_signal_events` rows.

---

## 10. Closure

**Product Signal Collection V1 is CLOSED in production** with governed Demo evidence on 2026-07-20.
