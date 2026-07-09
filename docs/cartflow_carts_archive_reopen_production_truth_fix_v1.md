# Carts Archive / Reopen — Production Truth Fix V1

**Date (UTC):** 2026-07-09  
**Status:** Fix implemented locally — **deploy required** before post-fix PASS  
**Prod base:** https://smartreplyai.net  
**Probe:** `scripts/_carts_archive_reopen_prod_truth_verify_v1.py`

---

## Root cause

### 1) Archive appears to work, then cart returns

| Layer | What happens |
|-------|----------------|
| API | `POST /api/dashboard/cart-lifecycle/archive` persists `merchant_cart_lifecycle_archives.is_archived=true` |
| Client | Optimistic move active → archived pool |
| Poll | `GET /api/dashboard/normal-carts` is **snapshot-enforced** |
| Hot slice | Live build correctly **excludes** archived keys from hot active rows |
| Merge bug | `merge_hot_slice_active_rows` still appends **stale snapshot active rows** for keys not in hot → archived cart reappears in `merchant_carts_page_rows` |
| Client | Successful poll **fully replaces** memory — optimistic archive lost |

**Not a visual bug.** Server payload after poll contradicts durable DB archive until the next snapshot builder tick (~45s), and even then hot-merge can reintroduce stale snapshot actives.

### 2) No Reopen on archived carts

Completed tab (`#page-completed` / `#ma-tbody-completed`) rendered via `cartRowTableDisplay()`, which cleared the “next step” cell for archived rows and **never rendered** `data-lc-reopen`. Reopen existed on PE panel footers only when the row was selected with projection synced.

### 3) Filter chips clickable but meaningless

| Issue | Detail |
|-------|--------|
| MI mode | `renderMiCartsV1Workspace` set `filters.hidden = true`, but PE CSS forced `#ma-cart-filters { display:flex }` so chips stayed visible |
| Filter apply | `maPeV2OnFilterApplied` **returned early** in MI mode — no queue filtering |
| Attrs | `miCartQueueItemHtml` omitted `data-ma-filter` / `data-ma-primary-bucket` / `data-ma-visible-tabs` |

---

## Fix summary

1. **`apply_merchant_archive_truth_to_normal_carts_payload`** (`services/merchant_cart_lifecycle_archive_v1.py`)  
   - After hot-slice merge on snapshot read (`dashboard_snapshot_read_v1.py`)  
   - Moves durable-archived keys out of active into archived pool  
   - Restores durable-reopened keys (`is_archived=false`) back to active  
   - Leaves terminal-only archived (no merchant archive row) alone  

2. **Completed table Reopen** — `cartRowTableDisplay` uses `merchantCartSecondaryLifecycleHtml` for archived rows  

3. **MI filters** — keep filter bar visible; add filter attrs on MI queue items; `applyMiCartsFilterMode` on chip click  

---

## API / DB / snapshot evidence (expected after deploy)

| Check | Expected |
|-------|----------|
| Archive API | `{ ok: true, archived: true, recovery_key }` |
| DB | `merchant_cart_lifecycle_archives.is_archived = true` for cart-specific key |
| `GET /api/dashboard/normal-carts` | `merchant_archive_truth_overlay: true`; key **absent** from `merchant_carts_page_rows`; **present** in `merchant_archived_carts_page_rows` with `dashboard_action=reopen` |
| After 8s poll | Key still absent from active |
| Reopen API | `{ ok: true, archived: false, cleared_persisted: true }` |
| After reopen poll | Key in active, not in archived |

---

## Production verification steps

```bash
# After deploy of this fix:
set CARTFLOW_PROD_EMAIL=...
set CARTFLOW_PROD_PASSWORD=...
python scripts/_carts_archive_reopen_prod_truth_verify_v1.py
# Expect verdict PASS in scripts/_carts_archive_reopen_prod_truth_v1_out/prod_truth_report.json
```

Manual (desktop + mobile):

1. Open Carts → archive one active cart → disappears from active  
2. Hard refresh → still archived; wait ~10s polling → does not return  
3. Open مكتملة / archived row → **إعادة فتح** visible → click → returns to active → refresh stays active  
4. Click each filter chip → visible story/queue set changes (or empty state); chips without matches hide groups  

---

## Pre-deploy production probe (2026-07-09)

Store seeded on https://smartreplyai.net (`archive.truth.30953fca@…`). Report: `scripts/_carts_archive_reopen_prod_truth_v1_out/prod_truth_report.json`.

| Check | Result | Evidence |
|-------|--------|----------|
| Archive API | **PASS** | `200` `{ ok:true, archived:true, recovery_key:…cf_cart_a9295be3… }` |
| Immediate poll after archive | Active excludes key; **archived pool empty** | `active:1`, `archived:0`, `overlay:false` — hot slice drops archived from active, but snapshot archived list not yet updated |
| After ~8s poll | Key in archived with `action:reopen` | Snapshot catch-up; `archive_survives_poll` true on this thin new store (bounce is intermittent when stale snapshot still lists the key as active) |
| Reopen API | **PASS** | `{ ok:true, archived:false, cleared_persisted:true, lifecycle… }` |
| After reopen poll | **FAIL (dual pool)** | Same `recovery_key` in **both** `active_keys` and `archived_keys` with archived still `action:reopen` — stale snapshot archived row not cleared. Overlay `bulk_merchant_reopened_keys` fixes this. |
| Filter chips desktop/mobile | **FAIL** | Bar `display:flex` while `hidden=true`; all chips show same `visible_items:2`; `mi_items_have_filter_attr:false` |

**Verdict pre-deploy:** `FAIL` (expected). Post-deploy re-run must show `merchant_archive_truth_overlay:true`, no dual-pool after reopen, and filter attrs + distinct chip counts.
