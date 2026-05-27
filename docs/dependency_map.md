# CartFlow Dependency Map

**Date (UTC):** 2026-05-27  
**Scope:** Read-only architecture freeze — data/control flow from storefront to dashboard.

---

## End-to-end pipeline (merchant production path)

```mermaid
flowchart TB
  subgraph client [Storefront client]
    WL[widget_loader.js]
    RT[cartflow_return_tracker.js]
    CAT[cart_abandon_tracking.js]
    V2[cartflow_widget_runtime/*]
    WL --> RT
    WL --> V2
    CAT --> CE
    V2 --> CFAPI
  end

  subgraph api [HTTP API]
    CE[POST /api/cart-event]
    REASON[POST /api/cartflow/reason]
    CONV[POST /api/conversion]
    CFAPI[GET /api/cartflow/ready public-config]
  end

  subgraph ingest [main.py ingest]
    RK[recovery_key derivation]
    ABANDON[handle_cart_abandoned]
    SYNC[cart_state_sync handler]
    REASONSAVE[CartRecoveryReason persist]
  end

  subgraph schedule [Scheduling durable]
    ARM[_arm_recovery_schedule_from_saved_reason]
    RSS[persist_recovery_schedule_durable]
    RS[(RecoverySchedule)]
    RSS --> RS
    ARM --> RSS
  end

  subgraph send [Send execution]
    DELAY[recovery_delay_dispatcher / scanner]
    WA[whatsapp_send / Meta path]
    CRL[(CartRecoveryLog)]
    DELAY --> WA
    WA --> CRL
  end

  subgraph timeline [Truth timeline]
    RTV[recovery_truth_timeline_v1]
    RTE[(recovery_truth_timeline_events)]
    RTV --> RTE
  end

  subgraph reply [Inbound WhatsApp]
    WH[POST /webhook/whatsapp]
    RIE[reply_intent_handling]
    RTEng[recovery_transition_engine]
    CRI[cartflow_reply_intent_engine]
    WH --> RIE
    WH --> RTEng
    RTEng --> RTV
    RTEng --> CRI
    CRI --> RTV
    CRI --> WA
  end

  subgraph classify [Dashboard read model]
    ROW[_build_merchant_normal_cart_row_payload]
    CLS[merchant_cart_row_classifier]
    LC[customer_lifecycle_states_v1]
    ARCH[merchant_cart_lifecycle_archive_v1]
    ROW --> CLS
    ROW --> LC
    LC --> ARCH
  end

  subgraph dash [Dashboard UI]
    API[GET /api/dashboard/normal-carts]
    JS[merchant_dashboard_lazy.js]
    API --> JS
  end

  V2 --> REASON
  REASON --> REASONSAVE
  REASONSAVE --> ARM
  CE --> RK
  RK --> ABANDON
  RK --> SYNC
  ABANDON --> ARM
  ARM --> DELAY
  DELAY --> RTV
  WA --> RTV
  ROW --> API
  CONV --> PT[(purchase_truth_records)]
  PT --> CLS
  PT --> LC
```

---

## Linear dependency chain (text)

```
Widget (V2 runtime + shared tracking)
    ↓
POST /api/cart-event          ← abandon, cart_state_sync, return signals
POST /api/cartflow/reason     ← objection tag; arms schedule (except handoff-only)
    ↓
handle_cart_abandoned / schedule persist
    ↓
RecoverySchedule + delay worker
    ↓
WhatsApp send → CartRecoveryLog + timeline (provider_sent)
    ↓
Inbound webhook → timeline (customer_reply, continuation_started)
    ↓
merchant_cart_row_classifier + customer_lifecycle_states_v1
    ↓
GET /api/dashboard/normal-carts
    ↓
merchant_dashboard_lazy.js (filters, chips, archive actions)
    ↓
POST /api/dashboard/cart-lifecycle/archive|reopen
```

---

## Parallel paths (same identity, different entry)

| Entry | Joins at | Notes |
|-------|----------|-------|
| `cartflow_return_tracker.js` | `POST /api/cart-event` | Return-to-site; throttled client-side |
| `POST /api/conversion` | `purchase_truth` + session converted cache | Demo checkout COD |
| Zid `POST /webhook/zid` | `purchase_truth` ingest | Production orders |
| `POST /api/cartflow/assist-handoff` | Audit log only | **Does not** schedule recovery |
| Merchant test `reset_demo` / identity contract | New `session_id`/`cart_id` | Isolated test lifecycles |

---

## Store slug coercion (identity boundary)

```
Browser payload.store
    ↓
coerce_cart_event_store_slug (merchant_test_widget_store_v1)
    ↓
Authenticated merchant zid (never demo/default when logged in)
    ↓
recovery_key store segment
```

Demo sandbox (`demo`, `demo2`) only when **no** merchant activation and public demo URLs.

---

## Session truth cache (side channel — not in main diagram)

```
has_sent_truth / has_conversion_truth
    ↓
_session_recovery_* dict (per process)
    ↓
fallback: CartRecoveryLog / purchase_truth_records
    ↓
rehydrate cache on DB hit
```

Used at **abandon gate** and **duplicate schedule** checks — must not override timeline for dashboard labels.

---

## Key modules by layer

| Layer | Primary files |
|-------|----------------|
| Widget | `static/widget_loader.js`, `static/cartflow_widget_runtime/*`, `static/cart_abandon_tracking.js`, `static/cartflow_return_tracker.js` |
| API routes | `main.py`, `routes/cartflow.py`, `routes/cart_recovery_reason.py` |
| Schedule | `main.py`, `services/recovery_restart_survival.py`, `services/recovery_delay_dispatcher.py` |
| Timeline | `services/recovery_truth_timeline_v1.py` |
| Classifier | `services/merchant_cart_row_classifier.py`, `services/customer_lifecycle_states_v1.py` |
| Archive | `services/merchant_cart_lifecycle_archive_v1.py` |
| Dashboard | `static/merchant_dashboard_lazy.js`, `main.py` dashboard routes |

---

## Debug shortcuts (read-only)

| Question | Endpoint / tool |
|----------|-----------------|
| Timeline for one lifecycle | `GET /dev/recovery-truth?recovery_key=` |
| Why row missing from dashboard | `GET /api/debug/cart-presence?recovery_key=` |
| Send chain divergence | `GET /api/debug/recovery-trace?recovery_key=` |
| Test-widget identity | `GET /dev/test-widget-identity-trace?store_slug=&session_id=` |
| Inclusion stages | `services/merchant_cart_presence_trace_v1.py` |
