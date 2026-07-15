# CartFlow Store Reality Simulator V1 — Architecture (Phase 1)

**Status:** Phase 1 design — **STOP for review**  
**Date (UTC):** 2026-07-15  
**Scope:** Design only. No Phase 2 infrastructure, no execution, no product fixes.  
**Target store:** `store_slug = demo` (`Store.zid_store_id ∈ {"demo"}` for Lab; `demo2` out of scope)

---

## 1. Purpose

Build a **validation environment** that generates governed historical source events for the canonical demo merchant so CartFlow’s **existing** pipelines derive cart state, movement, recovery, Purchase Truth, Knowledge, decisions, dashboards, and attention — the same way a real store would.

This is **not**:

- A demo filler or visual showcase
- A parallel truth pipeline
- A replacement for the approved product roadmap
- Permission to inject Knowledge Cards, confidence, recovered totals, or dashboard summaries

Honest outcome of Phase 1: the platform can support a powerful simulator, but **historical backdating is a first-class integration gap**. The simulator must document that gap and only exercise layers that genuinely exist.

---

## 2. Roadmap position

| Rule | Binding |
|------|---------|
| Validate existing layers | Widget, movement, cart lifecycle, recovery scheduling, WhatsApp paths, Purchase Truth, Product Foundation, hesitation mapping, Knowledge / Decision / Routing (as implemented), Dashboard, Monthly Summary, attention semantics, operational isolation, data-growth protections |
| Do not introduce unrelated product features | No AI recommendations, no new merchant claims engines |
| Do not change production merchant logic to beautify sim results | Defects are reported, not patched inside this program |

---

## 3. Existing foundations (reuse, do not reinvent)

| Asset | Path | Role for Reality Simulator |
|-------|------|----------------------------|
| Demo Commerce Lab reset | `services/demo_lab_reset_v1.py` | Demo-only purge pattern (identity-scoped). **Not** multi-run historical cleanup |
| Lab Scenario 1 | `services/demo_lab_scenario1_v1.py` | **Gold template** for truth path: HTTP `cart-event` → `reason` → return → `conversion` |
| Demo catalog | `services/demo_sandbox_catalog.py`, `services/cartflow_demo_catalog_seed.py` | Stable product identities (`demo_{key}`, SKU `DEMO-…`) |
| `sim-store-*` dry-run | `services/cartflow_simulation_report_v1.py` | Load/dry-run only. **Must not** be treated as merchant reality (direct inserts + mock sends) |
| Ops pause | `services/operational_control_v1.py`, `/admin/control` | Platform WA / schedule pause |
| Purchase Truth | `services/purchase_truth.py`, `services/cartflow_purchase_truth.py` | Canonical purchase ingest |
| Timeline | `services/recovery_truth_timeline_v1.py` | Recovery chain statuses |
| Movement | `services/customer_movement_snapshot_v1.py` | Movement snapshots (`event_at` accepted; row clocks still wall-now) |
| Attribution | `services/purchase_attribution_v1.py` | `confirmed_recovery` / `likely_recovery` / `assisted_recovery` / `organic_or_unknown` / `not_attributed` |
| Knowledge Layer | `services/knowledge_layer_v1.py` + metrics/insights | **Derived** read-only report |
| Knowledge Routing | `services/knowledge_routing_v1.py` | Routes published producer items (Daily Brief consumer) |
| Dashboard snapshots | `services/dashboard_snapshot_builder_v1.py` | Hot-path read model; must rebuild after bulk history |
| VIP | `services/vip_cart.py`, `services/vip_abandoned_cart_phone.py` | Threshold + phone capture |

---

## 4. Capability readiness (honest)

For each referenced layer: **Fully** | **Partial** | **Deferred** | **Missing integration**

| Layer | Status | Simulator may exercise? | Notes |
|-------|--------|-------------------------|-------|
| Demo store identity / isolation | Fully | Yes | Lab hard-gates `demo` |
| Widget reason capture | Fully | Yes | `/api/cartflow/reason`; tags: `price`, `shipping`, `warranty`, `thinking`, `quality`, `delivery`, `other` |
| Cart abandon / sync | Fully | Yes | `/api/cart-event` |
| Recovery schedule materialization | Fully | Yes | Via reason/abandon paths |
| WhatsApp send (real) | Fully (dangerous) | **No real send** | Use WA disabled + mock + ops pause |
| WhatsApp mock / skip statuses | Partial | Yes | `mock_sent`, skip statuses; no dedicated sim provider adapter yet |
| Purchase Truth | Fully | Yes | `/api/conversion` + internal `ingest_purchase_truth(..., purchase_time=)` |
| Purchase attribution | Fully | Yes | Derived after truth; wording differs from spec (“possible influence” → `assisted_recovery`) |
| Recovery Truth Timeline | Fully | Yes | Status chain; **no** `created_at` override today |
| Customer movement snapshots | Partial | Yes (limited) | Writers exist; dashboard hot-path consumption still limited |
| Product Foundation / demo catalog | Fully | Yes | Demo JSON catalog + `ProductCatalogEntry` where used |
| Product hesitation mapping | Partial | Yes when reason+product path fires | Do not invent product-wide claims |
| Knowledge Layer report | Fully (derived) | Yes | Needs sufficient sample; visitor/checkout metrics often unavailable |
| Merchant Decision Layer | Partial | Yes when evidence exists | Derived; do not seed shadow Decision cards for “reality” |
| Knowledge Routing | Partial | Yes for Daily Brief path | Other surfaces still migrating / partial consumers |
| Daily Brief | Partial | Yes | Consumes routed decisions |
| Dashboard snapshots / monthly | Fully (read model) | Yes after rebuild | Stale until `build_store_dashboard_snapshots` |
| Attention / Home composition | Partial | Yes | Often sparse without volume |
| Historical backdating / Time Machine | **Missing integration** | Blocker for Phase 3–4 honesty | HTTP paths stamp wall-clock `now` |
| Multi-journey / multi-day generator | **Missing** | Phase 2 | Lab Scenario 1 = single live journey |
| Simulation run model + cleanup by run | **Missing** | Phase 2 | Lab reset is identity purge, not run-scoped |
| Simulation-safe provider adapter | **Missing** | Phase 2 | Compose existing mock + flags |
| Restricted admin control surface for Reality Sim | **Missing** | Phase 2 | Prefer `/admin/*` or locked `/dev/*` |
| Storefront behavioral events (page/scroll/dwell) | **Unsupported** | Report only | No durable ingest vocabulary |
| Knowledge candidate ingest events | **Unsupported** | N/A | Knowledge is computed, not ingested |

---

## 5. Core architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Admin/Dev Control Surface (Phase 2)                             │
│ Dry Run | Execute | Pause | Resume | Cancel | Cleanup | Report  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│ Simulation Orchestrator                                         │
│ - simulation_run_id / scenario_id / seed / clock                │
│ - checkpoint + batch bounds + idempotency                       │
│ - event accounting (planned→…→reconcile)                        │
└───────┬───────────────────────────────┬─────────────────────────┘
        │ plan (deterministic)          │ execute
        ▼                               ▼
┌───────────────────┐     ┌───────────────────────────────────────┐
│ Scenario Registry │     │ Ingress Adapters (prefer real paths)  │
│ + Customer/Product│     │ 1) HTTP: cart-event / reason /        │
│   profiles        │     │    conversion / return                │
└───────────────────┘     │ 2) Internal services (documented)     │
                          │ 3) Bootstrap DB only (catalog/run)    │
                          │ 4) Timestamp authority (see §7)       │
                          └───────────────┬───────────────────────┘
                                          │ side effects
                          ┌───────────────▼───────────────────────┐
                          │ Platform pipelines (unchanged)          │
                          │ schedules · timeline · movement ·     │
                          │ purchase truth · attribution · KL ·   │
                          │ decisions · snapshots                   │
                          └───────────────┬───────────────────────┘
                                          ▼
                          ┌───────────────────────────────────────┐
                          │ Run Report + Truth Reconciliation       │
                          └───────────────────────────────────────┘
```

### 5.1 Identifiers (required)

Every generated record must be traceable:

| ID | Meaning |
|----|---------|
| `simulation_run_id` | One execution namespace (cleanup/archive key) |
| `simulation_scenario_id` | Scenario registry key (e.g. `S03_shipping_hesitation`) |
| `simulation_customer_id` | Stable simulated customer within run |
| `simulation_session_id` | Session within customer journeys |
| `simulation_cart_id` | Cart identity fragment used in `recovery_key` |
| `simulation_product_id` | Maps to demo catalog `id` / key |
| `simulated_event_id` | Deterministic event id + idempotency key |

**Proposed recovery_key shape (demo-safe):**

```text
demo:srs_{run_short}_{customer_short}_{cart_short}
```

Must remain parseable by existing `parse_recovery_key` / dashboard attach (`store_slug` first segment = `demo`).

**Proposed provenance envelope** (JSON on allowed context columns / log context — not a parallel event store):

```json
{
  "simulation": true,
  "simulation_run_id": "...",
  "simulation_scenario_id": "...",
  "simulation_customer_id": "...",
  "simulated_event_id": "...",
  "seed": 42
}
```

### 5.2 Modes

| Mode | Behavior |
|------|----------|
| **DRY RUN** | Build full deterministic plan; no persist; counts, affected models/pipelines, unsupported events, ETA |
| **EXECUTE** | Persist/process via adapters; checkpoints; run report |
| **CLEANUP** | Delete **only** rows tagged with `simulation_run_id` on `demo`; never non-demo; never untagged demo Lab fixtures unless explicitly scoped |

Also required later: **Pause / Resume / Cancel**, **Archive Run** (report retained) vs **Delete Run**.

### 5.3 Determinism

Same `(scenario set, start_date, duration_days, seed, scale)` → same event plan (ids, timestamps, outcomes).  
RNG: seeded PRNG inside planner only. Platform non-determinism (workers, snapshot loop timing) must be documented in report as environmental variance, not hidden.

---

## 6. Real pipeline requirement

### Prefer (truth path)

Mirror Lab Scenario 1:

1. `POST /api/cart-event` (`cart_state_sync` / `cart_abandoned` / return variants)
2. `POST /api/cartflow/reason` (hesitation / phone / VIP phone capture)
3. Internal schedule progression under **simulation-safe** send policy
4. `POST /api/conversion` or `ingest_purchase_truth(...)` for purchases
5. `build_store_dashboard_snapshots(store_slug="demo")` after batches / at end

### Direct DB writes — allowed only for

| Write | Why |
|-------|-----|
| Simulation run / checkpoint / report archive tables (Phase 2 models) | Orchestration metadata |
| Demo catalog seed if empty | Existing Lab pattern |
| Provenance tagging columns / context JSON | Traceability |
| **Documented timestamp authority** corrections (§7) | Platform lacks historical HTTP clocks |

### Must not direct-insert as “truth”

| Table / artifact | Why forbidden as primary write |
|------------------|--------------------------------|
| Derived Knowledge insights | Computed by KL |
| Dashboard snapshot totals | Built by snapshot builder |
| Attribution level as static label | Computed by `purchase_attribution_v1` |
| Merchant Decision / Pulse cards (seed) | Would fake intelligence |
| Fake `sent_real` without adapter policy | Contaminates delivery truth |

---

## 7. Time Machine — critical design gap

### 7.1 Reality today

| Path | Historical timestamp support |
|------|------------------------------|
| `POST /api/cart-event` | **No** — wall-clock |
| `POST /api/cartflow/reason` | **No** — wall-clock |
| `POST /api/conversion` | **Does not pass** `purchase_time` to ingest |
| `ingest_purchase_truth(..., purchase_time=)` | **Yes** (internal) |
| `record_recovery_truth_event(...)` | **No** — `created_at=_utc_now()` |
| `apply_movement_event(..., event_at=)` | **Partial** — accepts `event_at`; row `created_at` still now; monotonic guard blocks going backward |
| Schedules `due_at` | Computed from **now + delay** at arm time |

**Conclusion:** A 60-day backdated run **cannot** be honest if it only fires live HTTP today and hopes `created_at` defaults look historical.

### 7.2 Proposed Phase 2 strategies (for review — not implemented)

**Strategy A — Timestamp Authority Adapter (recommended direction)**  
1. Plan events with simulated timestamps.  
2. Ingress via real service functions where possible.  
3. Immediately apply a **governed post-write timestamp correction** for the `simulation_run_id` row set (`first_seen_at`, `due_at`, timeline `created_at`, reason logs, purchase_time, movement `*_at`, etc.).  
4. Re-arm schedule `due_at` relative to simulated abandon time.  
5. Mark corrections in event accounting as `timestamp_authority_applied` (not silent).

**Strategy B — Clock injection**  
Patch/process-local clock for duration of execute job. High risk under concurrent workers; only acceptable in isolated process with WA paused.

**Strategy C — Extend writers** (product change — **out of Phase 1/2 unless approved**)  
Add optional `event_at` to timeline/reason/cart writers. Do **not** do this merely to make the simulator pretty; requires separate product review.

**Phase 1 recommendation:** Approve Strategy A as the Phase 2 default; treat Strategy C as optional follow-on if post-write correction proves insufficient for reconciliation.

### 7.3 Relative delays inside history

Simulated WhatsApp delays, return visits, and purchases must be planned on the **simulated clock**, then persisted so:

- `purchase_time` vs `provider_sent` gaps drive real attribution windows
- Midnight / multi-day / monthly windows are real for KL `window_days` and monthly snapshots

---

## 8. Safety and isolation (non-negotiable)

| Control | Mechanism |
|---------|-----------|
| Demo only | Hard reject unless `store_slug == "demo"` |
| No production merchants | Explicit gate in orchestrator |
| No real outbound WhatsApp | `whatsapp_recovery_enabled=False` for execute prep + ops pause + mock adapter; never call Twilio/Meta for sim customers |
| No merchant alerts | Suppress VIP merchant alert path for simulation phones / flag |
| No billing impact | No plan mutations |
| No global feature-flag flips | Local to process/run config only |
| Cleanup scoped | `simulation_run_id` only |
| Jobs off merchant request path | Background/admin job only; batch limits |

Simulation-safe send policy (Phase 2):

- Prefer recording schedule + timeline transitions with `mock_sent` / governed skip
- Still exercise due-scanner **claim/cancel** logic under `dry_run` or mock dispatch
- Event accounting must show `provider_suppressed_simulation` when outbound blocked

---

## 9. Event accounting (no silent loss)

Every planned event ends in exactly one bucket:

`planned | persisted | processed | rejected | unsupported | failed | replayed | duplicate_suppressed`

Report must reconcile:

```text
planned = persisted + rejected + unsupported + failed
          (+ in-flight if paused)
duplicate_suppressed and replayed reported separately
```

Unsupported events are **first-class** (see Event Compatibility Matrix). They appear in DRY RUN and final reports — never dropped quietly.

---

## 10. Product catalog (simulated behavior profiles)

Reuse/extend demo sandbox products with **behavior profiles** (planner probabilities only — not injected conclusions):

| Profile | Example catalog keys | Intent |
|---------|----------------------|--------|
| Low-price high-volume | `charger`, `watch_band` | Baseline volume |
| High-price consideration | `hp_pro`, `watch_pro` | VIP / long dwell |
| Shipping hesitation | perfume / electronics with shipping-heavy reason mix | S03 |
| High ATC, low purchase | dedicated key (extend catalog if needed) | S04 |
| Strong WA recovery | mid-price with phone capture | S06 |
| Comparison | related family (`hp_pro` / `earbuds` / `hp_air`) | S08 |
| VIP high-value | cart total ≥ `Store.vip_cart_threshold` | S15 |

Each product: stable `id` (`demo_{key}`), name, category, price, shipping_info, behavior profile id.

---

## 11. Customer archetypes (planner only)

Fast buyer · Price-sensitive · Shipping-sensitive · Comparison shopper · Needs reassurance · High-value VIP · Repeated visitor · Widget engager · WhatsApp responder · Recovery-resistant · Organic buyer · Anonymous/no-phone  

Profiles adjust event probabilities. They **must not** write Knowledge, confidence, or ROI fields.

---

## 12. Observability

Structured logs: `simulation_run_id`, scenario, simulated date, stage, event id, latency.  
Not console-only.

Expose: run status, current simulated date, scenario progress, event counters, failures, slow stages, scheduler actions, purchase closures, KL outputs (post-derive), confidence distribution, timeline counts, dashboard refresh status, query/cost samples where available.

---

## 13. Run report + reconciliation (required sections)

Configuration · date range · seed · scenario/customer/session/product/cart counts · widget/WA/return/purchase counts · Purchase Truth closures · recovery classifications (platform levels) · timeline · movement · Knowledge candidates/outputs (derived) · recommendations / suppressed · confidence · attention · unsupported/failed/duplicates · data-growth metrics · slow stages · detected inconsistencies

**Reconciliation checks (surface mismatches; never auto-hide):**

- Planned purchases vs Purchase Truth rows  
- Purchases vs completed/closed carts  
- Purchased carts vs cancelled schedules  
- Returns vs movement snapshot flags/counts  
- Widget reasons vs persisted reason tags  
- WA replies vs attention state  
- Knowledge claims vs evidence sample sizes  
- Dashboard totals vs canonical counts (after snapshot rebuild)  
- Monthly totals vs source truth  
- No-phone counts vs row semantics  
- VIP counts vs threshold-eligible carts  
- Simulation events vs timeline events (where timeline applies)

---

## 14. Admin / control surface (Phase 2 placement)

**Preferred:** locked Admin or Dev diagnostics route (same auth class as `/admin/operations`, `/dev/*`).  
**Forbidden:** merchant dashboard exposure.

Controls: scenario multi-select, start date, days, seed, scale, Dry Run, Execute, Pause, Resume, Cancel, Cleanup, View report.

Note: Lab reset/scenario currently lack remote HTTP in some deploy docs — Reality Simulator should ship an explicit authorized route rather than relying on in-process Lab helpers alone.

---

## 15. Performance boundaries

- Batch size + max events per job  
- Checkpoint / resume  
- Idempotent `simulated_event_id`  
- Rate limits + timeouts  
- Failure isolation per batch  
- No work on merchant-facing request threads  
- Preserve scheduler/API separation  
- After large runs: snapshot rebuild; do not force hot-path full-history recompute  

Scenario 20 (data growth) is the stress validation for these bounds.

---

## 16. Relationship to existing simulators

| Tool | Use for Reality Sim? |
|------|----------------------|
| Lab Scenario 1 | **Pattern to extend** (HTTP truth path) |
| Lab Reset | Pattern for demo gates; **insufficient** as run-scoped cleanup |
| `cartflow_simulation_report_v1` (`sim-store-*`) | **Anti-pattern** for merchant reality; keep for load tests only |
| `merchant_seed_v1` Decision cards | **Do not use** for Reality Sim |
| Admin failure load tests | Unrelated |

---

## 17. Implementation sequence (binding)

| Phase | Deliverable | Stop |
|-------|-------------|------|
| **1 — Design** | This doc + scenario registry + event matrix + unsupported list | **← YOU ARE HERE** |
| **2 — Core infra** | Run model, registry, clock, seed planner, accounting, safe provider, checkpoints, cleanup | Stop for review |
| **3 — Small validation** | 3 days, baseline + one hesitation; full reconciliation | Stop for review |
| **4 — Full scenario run** | 60 days, approved scenarios; reports | Stop after reports |
| **5 — Product review** | Findings only — **no automatic product fixes** | Stop |

---

## 18. Phase 1 open questions for reviewers

1. Approve **Timestamp Authority Adapter (Strategy A)** for Phase 2?  
2. Confirm cleanup may remove Lab-overlapping demo rows **only** when tagged with `simulation_run_id` (Lab fixtures without tag remain)?  
3. Confirm attribution language in reports uses platform levels (`assisted_recovery`) not spec phrase “Possible Influence”?  
4. Confirm storefront behavioral events remain **unsupported** (reported, not faked) until a real ingest contract exists?  
5. Confirm Knowledge Routing validation is limited to surfaces that already consume routing (Daily Brief first)?  
6. Should Phase 2 add new tables (`simulation_runs`, `simulation_event_ledger`) or reuse JSON provenance on existing rows only?

---

## 19. Explicit non-goals (Phase 1–5 of this program)

- Injecting final dashboard / Knowledge / recommendation / confidence values  
- Sending real messages or modifying non-demo stores  
- Bypassing Purchase Truth, movement, scheduling, or canonical product/cart models  
- Hiding reconciliation failures  
- Rewriting production logic to pass simulation  
- Declaring success because events were generated  

---

## 20. Phase 1 exit

Phase 1 is complete when reviewers have:

1. Architecture document (this file)  
2. Scenario registry  
3. Event compatibility matrix  
4. Unsupported-event list  

**No code execution. No migrations. No control surface yet.**

**STOP for review.**
