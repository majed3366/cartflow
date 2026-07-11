# Widget Fast Path Root Cause Investigation V1

**Status:** COMPLETE (investigation only — no fix)  
**Date (UTC):** 2026-07-11  
**Commit (instrumentation):** `951eaba`  
**Runtime:** `v2-widget-fast-path-invest-v1`  
**Evidence:** `scripts/_widget_fast_path_invest_v1_out/timing_breakdown.json`  
**Samples:** N=12 production merchant `test-widget` journeys (reason + phone each)

---

## Method

- **Server:** additive `cf_timing.stages_ms` on `POST /api/cartflow/reason` (handler wall clock). No persistence/lifecycle/business change.
- **Client:** `[CF FAST PATH TRACE]` stage deltas (ui → bridge → POST → render / phone close).
- Recovery arm remains `BackgroundTasks` (not on the response-critical path in code).

### Operational budgets

| Stage class | Budget |
|-------------|--------|
| UI feedback | &lt;50 ms |
| Bridge | &lt;100 ms |
| API receive / warm | &lt;50 ms |
| Database ops | &lt;100 ms |
| Lifecycle | &lt;100 ms |
| Total click → next screen | &lt;500 ms |

---

## Flow A — Reason click → phone screen

### Client end-to-end (P50 / P90 / P95 / Max)

| Stage | P50 | P90 | P95 | Max | Budget | Over? |
|-------|-----|-----|-----|-----|--------|-------|
| UI ack (`ui_ack`) | **6.1** | 8.1 | 8.1 | 8.2 | 50 | |
| **Bridge ensure** | **3390.7** | 3746.4 | 3886.0 | 4046.4 | **100** | **YES ← FIRST** |
| Payload ready | 1.6 | 5.7 | 5.9 | 6.0 | 50 | |
| POST /reason (client wait) | **2704.3** | 3007.2 | 3031.0 | 3045.5 | (see server) | YES |
| Next screen render | 94.5 | 114.0 | 114.9 | 115.2 | — | |
| **Total click → phone** | **6345.5** | 6710.9 | 6734.9 | 6744.1 | **500** | YES |

### Server handler inside POST /reason — reason-only (P50 / P90 / P95 / Max)

| Stage | P50 | P90 | P95 | Max | Budget | Over? |
|-------|-----|-----|-----|-----|--------|-------|
| **db_warm** | **120.5** | 121.9 | 124.1 | 126.6 | **50** | **YES (first on server)** |
| json_parse | 0.8 | 1.5 | 1.6 | 1.7 | 50 | |
| validate_coerce | 29.4 | 32.3 | 32.5 | 32.7 | 50 | |
| phone_normalize | ~0 | | | | 50 | |
| db_lookup_crr | 7.7 | 8.8 | 9.5 | 10.4 | 100 | |
| db_prepare_writes | 0.1 | 0.1 | 0.1 | 0.1 | 50 | |
| db_flush | 15.4 | 20.3 | 22.2 | 24.1 | 100 | |
| phone_sync_session | 0.0 | 0.0 | 0.0 | 0.0 | 100 | |
| db_commit | 8.2 | 9.5 | 10.3 | 11.2 | 100 | |
| phone_side_effects | 0.0 | | | | 100 | |
| vip_alert_optional | 0.0 | | | | 100 | |
| schedule_recovery_bg | 0.0 | | | | 50 | |
| **total_handler** | **182.4** | 192.2 | 193.5 | 194.9 | — | |

**Client net vs server:** client POST wait P50 **2702 ms**; server handler P50 **182 ms**.  
≈ **2.5 s outside the measured handler** (queue / proxy / transport / connection) — secondary to bridge for Flow A ordering.

---

## Flow B — Phone save → close

### Client (P50 / P90 / P95 / Max)

| Stage | P50 | P90 | P95 | Max | Budget | Over? |
|-------|-----|-----|-----|-----|--------|-------|
| Click validated | **0.2** | 0.5 | 0.9 | 0.9 | 50 | |
| **POST /reason (phone merge) client wait** | **~2166** | ~2296 | ~2338 | 2623 | — | **YES ← FIRST** |
| Success UI | (sub-ms→tens) | | | | 50 | |
| Close dwell | ~700 (fixed UX) | | | | — | |

### Server handler — phone merge posts (P50)

| Stage | P50 | Budget | Over? |
|-------|-----|--------|-------|
| **db_warm** | **~120** | 50 | **YES (first on server)** |
| validate_coerce | ~30 | 50 | |
| db_lookup / flush / commit | each &lt;20 | 100 | |
| phone_sync_session | present when phone | 100 | (check samples in JSON) |
| schedule_recovery_bg | ~0 | 50 | |
| **total_handler** | **190.7** | — | |

Same pattern: client wait ≈ 2.1 s while handler ≈ 0.19 s.

---

## Root cause summary

### Flow A (reason → phone)

```
UI ack          6 ms
Bridge ensure   3391 ms  ← FIRST OVER BUDGET (budget 100 ms)
POST /reason    2704 ms client / 182 ms server
Render          95 ms
TOTAL           ~6346 ms
```

The extra **~3.4 s before the reason POST even starts** is spent in  
`StorefrontCartBridge.ensureCartTruthBeforeReason` → `readAndPersist`  
(on merchant test-widget, `cart_persisted` is false → full persist path; may wait on in-flight / cart-event work).  
Empty-retry ladder delays are `[500, 1200, 2500]` ms when cart reads empty.

### Flow B (phone → close)

```
Validate        ~0 ms
POST /reason    ~2166 ms client / ~191 ms server  ← FIRST OVER BUDGET (client-observed)
Close           ~700 ms dwell
```

Server work is not the multi-second consumer; **transport/queue gap** dominates the client POST wait. Within the handler, **`db_warm` (~120 ms)** is the first stage over the 50 ms API budget.

### Not the multi-second consumer (this run)

- Recovery schedule arm (`schedule_recovery_bg` ≈ 0 ms on response path)
- DB lookup / flush / commit (each tens of ms)
- Lifecycle hooks on the HTTP return path

---

## ONE answer — first stage over operational budget

### Flow A (reason selection → phone screen)

**`bridge_ensure` (Storefront cart bridge before reason POST)**  
**P50 ≈ 3391 ms** (budget &lt;100 ms).

Everything after that (including the slow client POST wait) is **downstream**.

### Flow B (phone save → close)

**Client-observed `POST /api/cartflow/reason` wait**  
**P50 ≈ 2166 ms**, while server handler P50 ≈ **191 ms**.  
First **server** stage over budget: **`db_warm` P50 ≈ 120 ms** (budget &lt;50 ms).

---

## Recommendation (do not implement in this task)

1. **Single first bottleneck to attack for Flow A:** make `ensureCartTruthBeforeReason` fail-fast when cart is already known / skip empty-retry wait on the reason critical path (merchant test-widget + storefront).  
2. **Second (phone + reason POST gap):** investigate why client round-trip is ~2.1–2.7 s when handler is ~0.18–0.19 s (proxy/queue/connection), and why `db_warm` still costs ~120 ms when already warmed.

---

## Files

- `routes/cartflow.py` — `_ReasonStageClock` + `cf_timing`
- `static/cartflow_widget_runtime/cartflow_widget_flows.js` — `[CF FAST PATH TRACE]`
- `static/cartflow_widget_runtime/cartflow_widget_fetch.js` — `_cf_client_net_ms`
- `scripts/_widget_fast_path_invest_v1_prod.py`
- `tests/test_widget_fast_path_invest_v1.py`
