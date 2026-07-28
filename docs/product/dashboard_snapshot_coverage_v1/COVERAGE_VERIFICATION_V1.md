# Dashboard Snapshot Coverage Verification V1

## Objective

Prove why Living Store Home reported `reason=no_snapshot`, and whether the builder produces, persists, refreshes, and selects the expected Home summary snapshot.

## End-to-end trace

```text
Scheduler loop (dashboard_snapshot_loop_v1, ~45s)
  → run_dashboard_snapshot_builder_tick
  → list_store_slugs_for_snapshot_build
  → is_snapshot_build_eligible_store
  → build_store_dashboard_snapshots(summary, …)
  → write_dashboard_snapshot_guarded / upsert_dashboard_snapshot

Home GET /api/dashboard/summary
  → resolve_merchant_store_slug_for_snapshot (Living Store cookie → demo)
  → fetch_latest_snapshot_row(store_slug=demo, snapshot_type=summary)
  → None → reason=no_snapshot
```

## Identity

| Actor | Value |
|-------|--------|
| Living Store review session | `store_slug=demo` |
| Review email | `cf.living.store.review@smartreplyai.net` |
| Binding | `issue_demo_home_review_session_v1` sets `primary_store_id` → demo |

## First divergence (BEFORE)

`is_snapshot_build_eligible_store` returned `False, "widget_placeholder_slug"` for **any** `demo` / `demo2` / `default` via `is_widget_recovery_zid`, **even when `merchant_user_id` was bound**.

So the builder never selected Living Store `demo` → no `dashboard_snapshots` summary row → Home `no_snapshot`.

Diagnostic snapshots (`diagnostic_snapshots`) are a **separate** table filled by `/dev/diagnostic-reasoning-materialize` / builder hooks for stores that *are* built — explaining “diagnostics exist, summary snapshot missing”.

## Fix (selection defect only)

Merchant-bound stores remain eligible regardless of widget-recovery zid naming.

- Unowned sandbox (`merchant_user_id is None`) → still excluded (`no_merchant_user`)
- Audit prefixes → still excluded
- Home fast fallback (`diagnostic_hes_only` / no ORV) **preserved**

## Ownership

| Concern | Owner |
|---------|--------|
| Background production | `dashboard_snapshot_loop_v1` when builder enabled (scheduler role / flag) |
| Write | `dashboard_snapshot_change_v1` → `dashboard_snapshots` |
| Home read | Snapshot only; never invents rows |
| Freshness | TTL per type; stale still serves row if present |

## STOP

No Home behavior redesign. No diagnosis changes. No collectors. No other pages.
