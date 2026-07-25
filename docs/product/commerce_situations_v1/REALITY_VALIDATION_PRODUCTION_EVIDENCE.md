# Reality Validation Certification V1 — Production Evidence

**Verdict: CERTIFIED**  
**Host:** https://smartreplyai.net  
**Store:** `demo`  
**Certified at (UTC):** 2026-07-25T21:42:59Z (identity JSON) · Workspace projection re-verified after PR #112 deploy  

## Success criteria

| Criterion | Result |
|-----------|--------|
| Production deployment complete | PASS — PR [#111](https://github.com/majed3366/cartflow/pull/111) + [#112](https://github.com/majed3366/cartflow/pull/112) |
| No endpoint 404 | PASS |
| Living Store executed in production browser | PASS |
| `simulation_run_id` persisted | PASS |
| `CEO_REVIEW_SAFE = TRUE` | PASS |
| `Status = CONSISTENT` | PASS |
| Home / Workspace / Products / Carts / Communication same reality | PASS (identity matrix) |
| No Workspace «تعذر التحميل» | PASS (projection `ok: true` after #112) |
| Complete evidence package | PASS (this file) |

## Canonical identity (locked)

| Field | Value |
|-------|-------|
| environment | `production` |
| database_environment | `production:postgresql` |
| store_slug | `demo` |
| merchant_id | `429` |
| merchant email | `cf.living.store.review@smartreplyai.net` |
| simulation_run_id | `srs_572fcb62fffc4955b0e7ae8fbe552642` |
| living_store_profile | `living_store` |
| last_simulation_timestamp | `2026-07-25T21:40:48.858044+00:00` |
| observations | `4` |
| facts | `6` |
| situations | `5` |

### Situation IDs (dataset)

1. `cs:interest_without_purchase|DEMO-WATCH-BAND:demo`
2. `cs:shipping_friction|b|demo_earbuds|demo-earbuds:demo`
3. `cs:product_demand|b|demo_perfume_velvet|demo-perfume-velvet:demo`
4. `cs:communication_coverage|store:demo`
5. `cs:store_health|store:demo`

## Step log

### 1 — Deployment

| Endpoint | HTTP |
|----------|------|
| `/dev/reality-validation-console` | 200 |
| `/dev/reality-validation-context?store=demo` | 200 |
| `/dev/reality-validation-context?store=demo&format=html` | 200 |
| `/dev/living-store-home-review` | 302 → `/dashboard#home` |
| `/dev/living-store-reality-status` | 200 |

Deploy commits: `980ede3` (PR #111), `3a5939b` (PR #112).

### 2 — Living Store (browser console only)

- Opened `/dev/reality-validation-console`
- Clicked **Run Living Store** (no terminal / no local / no SQLite)
- Job: `started_at_utc=2026-07-25T21:28:49Z` → `finished_at_utc=2026-07-25T21:40:48Z`
- Status: `completed`, `ok=true`, `status_source=in_memory` (durable control also written)
- `simulation_run_id=srs_572fcb62fffc4955b0e7ae8fbe552642`
- ORV admitted: 4 · silent_drops: 0 · plan_event_count: 2124 · reality_score: 80.0

### 3 — Identity Certification

URL: `/dev/reality-validation-context?store=demo&format=html`

```text
Status = CONSISTENT
CEO_REVIEW_SAFE = TRUE
```

All identity matrix rows ✔ (Environment, Database, Store, Merchant Session, Simulation Run, Living Store Profile/Timestamp, Observation/Facts/Situation counts, Home, Workspace, Products, Carts, Communication, Status).

`divergences=[]` · `divergence_begins_at=null`

### 4 — Surface identity audit

| Surface | store_slug | merchant_id | simulation_run_id | obs | facts | situations |
|---------|------------|-------------|-------------------|-----|-------|------------|
| Living Store | demo | 429 | srs_572fcb62… | 4 | 6 | 5 |
| Merchant session | demo | 429 | srs_572fcb62… | 4 | 6 | 5 |
| Home | demo | 429 | srs_572fcb62… | 4 | 6 | 5 |
| Decision Workspace | demo | 429 | srs_572fcb62… | 4 | 6 | 5 |
| Products | demo | 429 | srs_572fcb62… | 4 | 6 | 5 |
| Carts | demo | 429 | srs_572fcb62… | 4 | 6 | 5 |
| Communication | demo | 429 | srs_572fcb62… | 4 | 6 | 5 |

Projection counts (situation consumers): home=5 · workspace=3 · products=3 · carts=2 · communication=1 (subsets of the same 5-id dataset).

### 5 — Projection verification

| Check | Result |
|-------|--------|
| `/api/cart-workspace/v1/projection` | `http=200`, `ok=true`, `store_slug=demo`, `degraded=false` |
| UI «تعذر التحميل» | **Absent** |
| Workspace paints situations | Yes (shared `situation_id`s visible) |

### 6 — Truth pipeline (same `simulation_run_id`)

```text
Browser (Reality Validation Console)
  → Living Store  srs_572fcb62fffc4955b0e7ae8fbe552642
  → Observations  (4 admitted)
  → Business Facts  (6)
  → Commerce Situations  (5)
  → Home
  → Workspace
  → Products
  → Carts
  → Communication
```

Every certified surface references `srs_572fcb62fffc4955b0e7ae8fbe552642`.

## First divergence (resolved) — do not ignore

| Field | Value |
|-------|--------|
| Component | `services/cart_workspace/merchant_api_v1._auth_slug` |
| Expected | `demo` (same as Home / Living Store review session) |
| Actual | `unauthorized` (HTTP 401) |
| Affected surfaces | Decision Workspace |
| Root cause | `merchant_authenticated_store_slug` rejects `demo` via `is_widget_recovery_zid` while Home uses `resolve_authenticated_store_slug` |
| Fix | PR [#112](https://github.com/majed3366/cartflow/pull/112) — Workspace auth uses `resolve_authenticated_store_slug` |
| Restart | Re-bound `/dev/living-store-home-review` → projection 200 → cert still CONSISTENT + CEO_REVIEW_SAFE=TRUE |

Prior divergence (deployment): console 404 until PR #111.

## Constitutional note

Official certification authority is:

`GET /dev/reality-validation-context?store=demo(&format=html)`

Home hot-path chips may show `CEO_REVIEW_SAFE=FALSE` even when the certification probe is TRUE — always trust the probe for Gate / Product Review unlock.

## Deploy references

| Item | Value |
|------|-------|
| PR (RV stack) | https://github.com/majed3366/cartflow/pull/111 |
| PR (Workspace demo auth) | https://github.com/majed3366/cartflow/pull/112 |
| Merge commits | `980ede3`, `3a5939b` |
| Living Store run | `srs_572fcb62fffc4955b0e7ae8fbe552642` |
