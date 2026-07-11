# Carts Sprint 2.3 — Row pipeline probe (investigation)

**Status:** OPEN — counters refresh proven; desktop row paint still failing in production.  
**Build:** `ui-setup-v8i-cart-row-trace-v1`  
**Semantics:** unchanged (instrumentation + probe only).

## Pipeline under test

Same SPA for desktop and mobile. After data refresh:

1. `1_api_response` — `/api/dashboard/normal-carts` rows + MI flags  
2. `2_hot_slice_merge_client_view` — server-merged payload as seen by client  
3. `3_merchant_carts_page_rows` — prepared `merchant_carts_page_rows`  
4. `4_filtered_rows` — filter mode vs visible `.v2-queue-item`  
5. `5_virtual_list_input` / `5b_mi_render_*` — RSC bodyMode + MI stories/groups (no virtual list)  
6. `6_final_dom_render` — `#ma-carts-groups-v2` DOM snapshot  

## Highest-likelihood drop points (unproven — probe must confirm)

Given counters update while the list stays empty, filter badges are painted by `renderNormalCartsTables` **before** RSC body paint. So data can refresh while the list body stays on a prior empty/calm paint.

| Stage | Symptom if this is the drop |
|-------|-----------------------------|
| `5_virtual_list_input` `paint_calm_follow` / `pending` | `memory_rows > 0`, `bodyMode !== stories`, calm whisper in `#ma-carts-groups-v2` |
| `5b_mi_render_stories` `matched_rows: 0` | Stories/cards exist but no `.v2-queue-item` (key mismatch) |
| `4_filtered_rows` | Items in DOM, `visible_queue_items: 0` under active filter |
| `silent_skip` / `workspace_skip_reuse_dom` | Trace shows skip while DOM still empty from earlier calm |
| Resize same-tab | If desktop→mobile resize keeps empty, not CSS; if mobile device alone has rows, separate session/RSC state |

## How to capture (merchant or engineer)

On **desktop** carts tab after a new cart (counters already moved):

```js
copy(JSON.stringify(window.__maCartsRowProbe(), null, 2))
```

Then resize to mobile width (or open mobile) and run again. Compare:

- `memory_rows` / `memory_keys` — if desktop already empty here, drop is pre-paint  
- `rsc.bodyMode` — `pending`/`calm` with rows → paint never calls MI stories  
- `trace_tail` stages — first stage where `visible_queue_item_count` becomes 0  
- `5b_mi_render_stories.match_audit` — stories with `matched_rows: 0` while `page_rows > 0`

## Automated probe

```bash
python scripts/_carts_sprint2_3_row_pipeline_probe.py
```

Requires `CARTFLOW_PROD_EMAIL` / `CARTFLOW_PROD_PASSWORD` after this build is deployed.

## Definition of done (unchanged)

Desktop and mobile render the same canonical rows from the same payload. No fix until the first disappearance stage is proven.
