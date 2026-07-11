# Sprint 2.3 — Operational Fast Path Investigation

**Status:** SUPERSEDED by live confirmation — see `docs/cartflow_sprint2_3_operational_fast_path_live_confirmation_v1.md`  
**Date (UTC):** 2026-07-11  
**Build under review:** `ui-setup-v8j-lifecycle-e2e-v1` (deployed)  
**Method:** Single operational pipeline; code-constant latency budget + production symptom mapping. **Live timestamps captured 2026-07-11** — bridge ensure was **not** the first over-budget stage after reason click; **reason POST arm (~2343 ms)** was.

---

## One-pipeline model

```
Widget click
  → Reason persisted (POST /api/cartflow/reason)
  → Lifecycle updated (classify on next dashboard build)
  → Recovery decision / schedule arm (sync in reason request)
  → Provider decision (delay dispatch; optional WhatsApp)
  → Queue / CartRecoveryLog
  → Provider accepted (sent_real) or mock_sent
  → Merchant snapshot (builder) + hot-slice (read)
  → Dashboard refresh (refresh-state poll)
  → Merchant UI render
```

---

## Timing table (code budget — not a workaround)

Sources: widget bridge, reason route, recovery coordinator, refresh watcher, hot-slice, snapshot loop.

| Stage | Typical (code) | Worst (code) | Owner |
|-------|----------------|--------------|--------|
| **Widget click → handler** | &lt; 5 ms | &lt; 35 ms | `cartflow_widget_ui.js` |
| **Cart bridge before reason** (`ensureCartTruthBeforeReason`) | 0–200 ms (already persisted) | **4 200 ms** empty-cart retries 500+1200+2500 | `cartflow_storefront_cart_bridge_core.js` |
| **Reason persist** `POST /api/cartflow/reason` | 50–150 ms | ~1–2 s (DB + sync arm) | `routes/cartflow.py` |
| **Lifecycle classify** | &lt; 20 ms | &lt; 50 ms | `customer_lifecycle_states_v1.py` (on dashboard build) |
| **Recovery decision + schedule persist** | in reason request | same request | `coordinator_v1` / materialization |
| **Queue / log row** | sync with arm | same | `CartRecoveryLog` |
| **Provider selected / delay** | config 0–300 s | merchant template delay | **not** dashboard row path |
| **Provider accepted** (`sent_real`) | Twilio RTT | fail → `whatsapp_failed` | `whatsapp_send.py` |
| **Hot-slice merge on read** | 50–200 ms | 500 ms budget then degrade | `dashboard_hot_slice_v1.py` |
| **Snapshot rebuild (store picked)** | 0–45 s | **`ceil(N/5)×45 s`** (fleet rotation) | `dashboard_snapshot_loop_v1.py` |
| **Dashboard refresh detect** | ~0–1.25 s avg | **2 500 ms** poll | `merchant_dashboard_lazy.js` `setInterval(2500)` |
| **Dashboard API serve** | 50–200 ms | 500 ms hard | `dashboard_snapshot_read_v1.py` |
| **Merchant UI render** | &lt; 50 ms | RSC/MI paint | `merchant_dashboard_lazy.js` |

### End-to-end composites

| Path | Typical | Worst from constants |
|------|---------|----------------------|
| New cart → open tab (hot-slice ON, `:c` token bumps) | **~1.5–3 s** | ~7 s (+ empty-cart retries) |
| Snapshot-only / hot-slice degraded / no token bump | — | **minutes** via builder rotation |

---

## Observed symptoms → first over-budget stage

### 1) Widget waits several seconds after reason click

**First stage over budget:** **Cart bridge `ensureCartTruthBeforeReason` empty-cart retries** (worst **4.2 s**), then (after v8j) **awaited reason POST** which includes sync recovery arm.

Not a missing listener. Persist-then-advance made the wait *visible* as blocked UI until POST returns; multi-second stalls are dominated by bridge empty-cart retries and/or cart-event in-flight, not lifecycle/UI.

**Operational target for this stage:** sub-second when cart already known (`cart_persisted`). Exceeded when retries fire.

### 2) Dashboard counters take several minutes

**First stage that can reach minutes:** **Snapshot builder store-rotation queue** — `ceil(eligible_stores / 5) × 45s`.

Under default hot-slice + `:c` overlay, new carts should update in **~2.5 s poll + hot-slice**, not minutes. Minutes imply one of:

1. Hot-slice degraded/off → merchant depends on snapshot age  
2. Refresh token **did not bump** (reason-only on existing cart, no new `CartRecoveryLog`, `:c` unchanged) → **no refetch** until another signal  
3. Counter fields frozen in stale snapshot while UI partially updates  

**First divergence for “minutes”:** not client poll (2.5 s max wait) — **snapshot rebuild coverage / missing refresh-token bump**.

### 3) «رسالة أُرسلت» without WhatsApp provider

See classification below.

---

## «رسالة أُرسلت» — exact truth class

**Answer: C) Provider accepted**

| Class | Meaning | Enters «رسالة أُرسلت» after v8j? |
|-------|---------|----------------------------------|
| A Scheduled only | `RecoverySchedule` / `waiting_first_send` | **No** → waiting |
| B Queue created | `queued` / `delay_started` | **No** |
| C Provider accepted | `CartRecoveryLog.status = sent_real` (Twilio ok + SID) | **Yes** |
| D Provider delivered | delivery webhook | **No** (not required) |

**Pre-v8j (and mock path):** `mock_sent` (ok without SID / no real WhatsApp) could inflate the sent filter → merchant saw «رسالة أُرسلت» without an activated provider. That was **operational mock acceptance**, not C. Fixed server-side by `merchant_filter_bucket_for_lifecycle` requiring `sent_real` only.

Hard-refresh still needed so client cache does not show stale row membership.

---

## Root cause confirmation (investigation verdict)

| Symptom | First stage exceeding operational intent | Fix candidate (NOT applied this sprint step) |
|---------|------------------------------------------|-----------------------------------------------|
| Widget multi-second wait | Cart-bridge empty retries + sync work on reason path before advance | Make bridge fail-fast when cart already known; keep persist-then-advance; do not add retries |
| Counter minutes lag | Snapshot rotation **or** refresh token not bumping on reason/lifecycle change | Ensure token bumps on lifecycle-material truth changes; do not lengthen poll |
| False «رسالة أُرسلت» | Merchant filter treated `mock_sent` as sent | Already remapped to require `sent_real` (v8j) |

**Confirmed:** The pipeline’s minute-scale latency is **not** introduced by the 2.5 s refresh poll. The first stage capable of **minutes** is **snapshot builder fleet coverage** when hot-slice/token fast path fails. The first stage capable of **multi-second widget stall** is **`ensureCartTruthBeforeReason` empty-cart retry ladder**.

---

## What was NOT done (per mandate)

- No increased polling  
- No timeout extension  
- No artificial delay  
- No manual-refresh UX  
- No pipeline repair in this document  

---

## Next step (only after explicit repair approval)

1. Instrument production with stage timestamps (`t0` widget click → … → UI) on one real cart (read-only logs).  
2. Confirm measured first over-budget stage matches this table.  
3. Repair **that** stage only (bridge fail-fast and/or refresh-token completeness and/or hot-slice reliability — not poll interval).

---

## Key files

| Stage | Path |
|-------|------|
| Bridge retries | `static/cartflow_widget_runtime/cartflow_storefront_cart_bridge_core.js` |
| Reason + sync arm | `routes/cartflow.py`, `main.py` recovery hook |
| Refresh poll 2500 ms | `static/merchant_dashboard_lazy.js` |
| Live `:c` overlay | `services/dashboard_refresh_cart_revision_v1.py` |
| Hot-slice | `services/dashboard_hot_slice_v1.py` |
| Snapshot loop 45 s / 5 stores | `services/dashboard_snapshot_loop_v1.py` |
| Sent filter = `sent_real` | `services/customer_lifecycle_states_v1.py` `merchant_filter_bucket_for_lifecycle` |
