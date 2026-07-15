# CartFlow Store Reality Simulator V1 — Phase 1 Report

**Status:** Phase 1 complete — **STOP for review**  
**Date (UTC):** 2026-07-15  
**Scope:** Design and compatibility mapping only  
**Explicitly out of scope for this commit:** Phase 2 implementation, migrations, production logic changes, execution runs

**Companion design docs (detail):**

- `docs/architecture/store_reality_simulator_v1_architecture.md`
- `docs/architecture/store_reality_simulator_v1_scenario_registry.md`
- `docs/architecture/store_reality_simulator_v1_event_compatibility_matrix.md`

---

## 1. Executive Summary

### 1.1 What was inspected

Phase 1 inspected the **actual CartFlow codebase** (not aspirational docs alone) for:

- Demo store identity (`store_slug=demo`) and Lab isolation
- Event ingestion HTTP paths and internal writers
- Cart lifecycle, recovery scheduling, WhatsApp send/mock paths
- Customer movement snapshots
- Purchase Truth and attribution
- Knowledge Layer / Decision / Routing
- Dashboard snapshot and Monthly Summary builders
- Existing simulators: Demo Lab Scenario 1, `sim-store-*` dry-run report, catalog seed
- Timestamp / backdating support on critical writers
- Admin/dev surfaces suitable for a restricted control plane

### 1.2 What Phase 1 confirmed

1. **A Reality Simulator is feasible** if it reuses the Lab Scenario 1 **HTTP truth path** (`cart-event` → `reason` → return → `conversion`) and lets existing pipelines derive truth.
2. **`sim-store-*` dry-run (`cartflow_simulation_report_v1`) is not merchant reality** — it uses direct inserts and mock sends for load verification and must remain separate.
3. **Core recovery / purchase / reason / schedule / attribution / KL report paths exist** and can be exercised without inventing a parallel product.
4. **Many storefront behavioral events in the brief have no durable ingest** today — they must be reported as unsupported, not faked.
5. **Historical backdating is a first-class gap:** primary HTTP and timeline writers stamp wall-clock `now`. Honest multi-day/60-day history requires a Phase 2 Timestamp Authority design decision.
6. **Knowledge, Decisions, Routing, dashboard totals, attribution levels must remain derived** — never injected by the simulator.
7. **Safety can be composed** from existing controls (demo gate, WA disabled, ops pause, `mock_sent`) but a dedicated simulation-safe provider adapter does not exist yet.

### 1.3 What remains uncertain

1. Whether reviewers approve **post-write Timestamp Authority** vs clock injection vs product writer changes for history.
2. Whether Phase 2 adds **new orchestration tables** (`simulation_runs`, event ledger) or provenance JSON on existing rows only.
3. Cleanup interaction with **untagged Lab fixtures** on `demo`.
4. How far Knowledge Routing / Home Attention can be validated given partial surface consumers.
5. How much product-level conversion insight is available without additional Product Foundation volume.
6. Whether simulated delivery webhooks (`webhook_delivered`) are in V1 scope or deferred.

---

## 2. Simulator Architecture

### 2.1 Proposed architecture

```
Admin/Dev Control (locked)
  Dry Run | Execute | Pause | Resume | Cancel | Cleanup | Report
            │
            ▼
Simulation Orchestrator
  run_id · scenario_id · seed · SimulationClock · checkpoints · accounting
            │
            ├─ Scenario Registry + product/customer profiles (planner only)
            │
            ▼
Ingress Adapters (prefer real boundaries)
  1) HTTP: /api/cart-event, /api/cartflow/reason, /api/conversion, return paths
  2) Internal services (documented): purchase ingest with purchase_time, movement, mock send
  3) Bootstrap DB only: run metadata, demo catalog if empty, provenance tags
  4) Timestamp Authority (pending approval): governed historical correction
            │
            ▼
Unchanged platform pipelines
  schedules · timeline · movement · Purchase Truth · attribution · KL · decisions · snapshots
            │
            ▼
Run Report + Truth Reconciliation (mismatches surfaced, never auto-hidden)
```

### 2.2 Main modules/services (proposed Phase 2 package)

| Module | Responsibility |
|--------|----------------|
| `store_reality_simulator` orchestrator | Modes, checkpoints, bounds, pause/resume |
| Scenario registry | S01–S20 governed plans |
| Seeded planner | Deterministic event plan from seed/date/days/scale |
| SimulationClock | Simulated “now” and chronological ordering |
| Ingress adapters | HTTP + internal + bootstrap |
| Timestamp Authority | Historical field correction (if approved) |
| Safe provider adapter | Block real Twilio/Meta; prefer `mock_sent` / suppress |
| Event ledger / accounting | Planned→terminal buckets + idempotency |
| Cleanup / archive | Run-scoped delete vs report archive |
| Report builder | Configuration, counts, reconciliation, KL validation |
| Control surface | Restricted admin/dev route only |

**Reuse (do not reinvent):** `demo_lab_scenario1_v1`, `demo_lab_reset_v1` gates, `demo_sandbox_catalog`, `purchase_truth`, `recovery_schedule_materialization_v1`, `customer_movement_snapshot_v1`, `knowledge_layer_v1`, `dashboard_snapshot_builder_v1`, `operational_control_v1`.

### 2.3 Data flow

1. Planner emits ordered `simulated_event` records with simulated timestamps and idempotency keys.  
2. DRY RUN stops after plan + unsupported inventory.  
3. EXECUTE processes batches through adapters.  
4. Platform services create operational rows and side effects.  
5. Derived layers (attribution, KL, decisions, snapshots) run via existing builders/APIs.  
6. Accounting reconciles planned vs outcomes.  
7. Report archives; cleanup optionally removes run-tagged rows only.

### 2.4 Execution boundaries

- Demo store only (`store_slug == "demo"`).
- Background/admin job only — **never** merchant-facing request path.
- Batch size + max events per job + timeouts + rate limits.
- Idempotent re-run of same `simulation_run_id` + `simulated_event_id`.
- Unsupported events terminate as `unsupported` (visible), never silently dropped.

### 2.5 Scheduler/API isolation

- Simulation orchestration must not run inside dashboard/API request handlers.
- Due-scanner / schedule claim may be exercised under **dry_run or mock dispatch**.
- Merchant hot paths continue to read snapshots; after execute, call `build_store_dashboard_snapshots` for `demo`.

### 2.6 Safe provider adapter

Compose (Phase 2):

1. Force `whatsapp_recovery_enabled=False` for execute prep on demo (Lab pattern), **or** ops pause (`platform_wa_paused` / store pause) with restore documented.  
2. Never call Twilio/Meta for simulation customers.  
3. Prefer `CartRecoveryLog` status `mock_sent` / governed skip statuses.  
4. Suppress VIP merchant alert outbound for simulation phones.  
5. Record accounting reason `provider_suppressed_simulation` when outbound blocked.

No dedicated adapter exists today — Phase 2 must add one wrapping existing mock/skip paths.

### 2.7 Checkpointing and resume

Proposed:

- Persist checkpoint: `(simulation_run_id, last_simulated_event_id, simulated_date, batch_index, status)`.
- Resume continues from next unprocessed planned event.
- Interrupt → status `paused` / `failed` with partial accounting.
- Re-execute same event id → `duplicate_suppressed` or `replayed` (explicit).

### 2.8 Cleanup boundaries

- Delete **only** rows tagged with `simulation_run_id` on `demo`.
- Never delete non-demo stores.
- Never delete untagged Lab/demo fixtures unless explicitly scoped.
- **Archive Run** keeps report/diagnostics; **Delete Run** removes tagged operational data after final reconciliation.
- Cleanup must be deterministic and auditable (counts deleted per model).

---

## 3. Existing Platform Paths

### 3.1 Event ingestion

| Path | Role |
|------|------|
| `POST /api/cart-event` (`main.py`) | Cart sync, abandon, return/passive return variants |
| `POST /api/cartflow/reason` (`routes/cartflow.py`) | Hesitation reason + phone / VIP phone capture; arms recovery |
| `POST /api/cart-recovery/reason` | Layer D reason API |
| `POST /api/conversion` | Purchase evidence → Purchase Truth |
| `POST /api/cartflow/assist-handoff` | Human support request |
| Platform `NormalizedPlatformEvent` | Partial Zid/order path |
| Meta/Twilio webhooks | Delivery + inbound reply |
| `POST /dev/purchase-truth-test` | Dev purchase probe |

### 3.2 Cart lifecycle

- Model: `AbandonedCart`, archive `MerchantCartLifecycleArchive`, closure `LifecycleClosureRecord`.
- Identity: `recovery_key` ≈ `{store_slug}:{cart_id|session_id}`.
- Transitions: abandon → schedule arm → send progression → purchase closure / archive/reopen (dashboard APIs).
- Services: `merchant_cart_lifecycle_archive_v1.py`, `customer_lifecycle_states_v1.py`, `purchase_lifecycle_closure.py`.

### 3.3 Widget

- Runtime: `static/cartflow_widget_runtime/`, bridge scripts.
- Reason tags (canonical): `price`, `shipping`, `warranty`, `thinking`, `quality`, `delivery`, `other` (`store_reason_templates.py`).
- Persist: `CartRecoveryReason`, `AbandonmentReasonLog`.
- Human support: assist-handoff + store `whatsapp_support_url`.

### 3.4 WhatsApp

- Schedule materialization: `recovery_schedule_materialization_v1.py`.
- Due scan: `recovery_db_due_scanner*.py`.
- Send: `whatsapp_send.py` / Meta paths → `sent_real` or `mock_sent`.
- Timeline: `recovery_truth_timeline_v1.py` status chain.
- Cancel on purchase: `cancel_durable_schedules_for_purchase` in `recovery_restart_survival.py`.
- Ops pause: `operational_control_v1.py`, `/admin/control`.

### 3.5 Customer movement

- Model: `MovementSnapshot` (`passive_return_visit_count`, `returned_at`, `movement_active`, …).
- Writer: `apply_movement_event(..., event_at=Optional)` in `customer_movement_snapshot_v1.py`.
- Hooked from timeline / purchase / return paths.
- Dashboard hot-path consumption still limited (partial).

### 3.6 Purchase Truth

- `ingest_purchase_truth` / `ingest_purchase_truth_payload` / `record_purchase`.
- HTTP `/api/conversion` does **not** currently pass `purchase_time`.
- Internal API accepts `purchase_time`.
- Side effects: lifecycle closure, schedule cancel, product purchase mapping, attribution.

Attribution levels (`purchase_attribution_v1.py`):

- `confirmed_recovery`
- `likely_recovery`
- `assisted_recovery` (closest to spec “possible influence”)
- `organic_or_unknown`
- `not_attributed`

### 3.7 Knowledge

- Metrics → insights: `knowledge_metrics_v1.py`, `knowledge_insights_v1.py`, `knowledge_layer_v1.py`.
- Confidence thresholds: e.g. `MIN_HESITATION_SAMPLE = 3`.
- Producer metadata: `knowledge_producer_metadata_v1.py`.
- Routing: `knowledge_routing_v1.py` (Daily Brief consumer via Composer V2).
- Decisions: `merchant_decision_layer_v1.py` (derived; do not use shadow seed for reality).
- **No** `knowledge_candidate_created` ingest event — Knowledge is computed.

### 3.8 Dashboard and Monthly Summary

- Snapshot types include `summary`, `normal_carts`, `monthly_summary`, etc. (`dashboard_snapshot_v1.py`).
- Builder: `build_store_dashboard_snapshots`, loop `dashboard_snapshot_loop_v1.py`.
- Repair/parity: `GET /dev/dashboard-builder-parity?repair=1`.
- Hot path must read precomputed snapshots — after simulation, rebuild for `demo` is mandatory.

---

## 4. Event Compatibility Matrix

Legend: **Supported** · **Partial** · **Unsupported** · **Internal-only** · **Derived**

| Requested event | Canonical equivalent | Status | Service / endpoint | Required adaptation | Bypass risk |
|-----------------|---------------------|--------|--------------------|---------------------|-------------|
| `session_started` | — | Unsupported | — | Mark unsupported | Fake session analytics |
| `page_viewed` | — | Unsupported | — | Mark unsupported | Fake traffic |
| `product_viewed` | Lab step name only | Unsupported | — | Proxy via cart lines; report unsupported as event | Fake product analytics |
| `category_viewed` | — | Unsupported | — | Mark unsupported | Fake category analytics |
| `scroll_depth_reached` | — | Unsupported | — | Mark unsupported | Fake engagement |
| `dwell_time_recorded` | Client timer only | Unsupported | — | Mark unsupported | Fake dwell |
| `product_revisited` | — | Unsupported | — | Multi-session sync proxy; report | Fake revisit metric |
| `checkout_started` | `NormalizedPlatformEvent.checkout_started` / cart progress | Partial | Platform webhook partial; cart-event sync | Prefer sync near checkout; else partial | Skip abandon arming |
| `checkout_step_viewed` | — | Unsupported | — | Mark unsupported | N/A |
| `session_ended` | — | Unsupported | — | Mark unsupported | N/A |
| `customer_returned` | return / passive return payloads | Partial | `POST /api/cart-event` | HTTP return paths | Skip movement hooks |
| `cart_created` | `AbandonedCart` via sync/abandon | Partial | `/api/cart-event` | HTTP sync/abandon | Skip identity/schedules |
| `item_added` | `cart_state_sync` reason `add` | Partial | `/api/cart-event` | HTTP sync with lines | Skip line snapshots |
| `item_removed` | cart_state_sync | Partial | `/api/cart-event` | HTTP sync | Same |
| `item_quantity_changed` | cart_state_sync | Partial | `/api/cart-event` | HTTP sync | Same |
| `cart_value_changed` | cart total on `AbandonedCart` | Partial | sync/abandon | HTTP | VIP threshold wrong |
| `cart_abandoned` | `event=cart_abandoned` | Supported | `/api/cart-event` | HTTP | Skip recovery arming |
| `cart_reopened` | merchant reopen | Partial | `/api/dashboard/cart-lifecycle/reopen` | Only for archive UX scenarios | Wrong merchant semantics |
| `cart_archived` | merchant archive | Partial | `/api/dashboard/cart-lifecycle/archive` | Optional | Same |
| `cart_completed` | lifecycle closure via purchase | Derived | Purchase Truth path | Via conversion/ingest | Orphan completed flags |
| `widget_eligible` | client heuristics | Unsupported | — | Mark unsupported | Fake eligibility |
| `widget_shown` | widget health / client | Partial | Not durable API | Plan marker only; no fake DB event | Fake widget truth |
| `widget_opened` | — | Unsupported | — | Model as no reason yet | Invented opens |
| `widget_ignored` | — | Unsupported | — | Absence of reason POST | Invented ignore rows |
| `widget_closed` | — | Unsupported | — | Mark unsupported | N/A |
| `hesitation_reason_selected` | reason capture | Supported | `/api/cartflow/reason` | Map spec reasons → platform tags | Skip schedule/templates |
| `phone_submitted` | phone / `vip_phone_capture` | Supported | `/api/cartflow/reason` | HTTP | VIP/no-phone facet wrong |
| `human_support_requested` | assist handoff | Supported | `/api/cartflow/assist-handoff` | HTTP | Skip support path |
| `widget_suppressed` | suppression gates | Partial | widget/runtime gates | Exercise where code exists | Fake suppression |
| `whatsapp_eligible` | store flags + gates | Partial | Internal gates | Assert eligibility; no fake event | Skip gates |
| `whatsapp_scheduled` | `RecoverySchedule` + timeline `scheduled` | Internal-only | materialization from reason/abandon | Real materialization + sim-safe send | Skip due scanner |
| `whatsapp_sent` | `mock_sent` / `sent_real` + `provider_sent` | Internal-only | due scanner / send | **mock_sent only** | Fake delivery / real send |
| `whatsapp_delivered` | `WhatsAppDeliveryTruth` / `webhook_delivered` | Partial | webhooks | Defer or isolated sim webhook | Fake delivery |
| `whatsapp_failed` | `whatsapp_failed` / provider failure | Internal-only | failure paths | Sim-safe failure adapter | Mislabel as hesitation |
| `whatsapp_ignored` | inferred | Unsupported | — | Infer in report | Fake ignore event |
| `whatsapp_replied` | timeline `customer_reply` | Internal-only | inbound webhooks | Sim-safe reply injector | Skip movement/attention |
| `merchant_followup_required` | VIP/attention composition | Partial | derived | Observe only | Fake attention |
| `whatsapp_suppressed` | skip statuses / ops pause | Partial | send gates | Exercise + account | Silent skip |
| `passive_return` | `EVENT_PASSIVE_RETURN` | Supported/Partial | cart-event + movement | HTTP | Count drift |
| `continuation_started` | timeline/movement status | Internal-only | continuation writers | Real continuation path | Skip snapshot |
| `returned_to_site` | movement + return cart-event | Supported/Partial | return paths | HTTP | Skip snapshot |
| `repeated_revisit` | `passive_return_visit_count` | Partial | passive return | Multi returns | Inflated SQL counts |
| `purchase_detected` | movement `purchase_detected` | Internal-only | purchase hooks | Via Purchase Truth | Orphan movement |
| `purchase_created` | conversion / purchase evidence | Supported | `/api/conversion` + ingest | HTTP + internal `purchase_time` for history | Skip cancel/closure |
| `purchase_truth_persisted` | `PurchaseTruthRecord` | Derived | ingest | Assert after ingest | Direct insert skips lifecycle |
| `purchase_mapped_to_cart` | mapping services | Partial | post-truth | Via truth | Orphan mapping |
| `schedules_cancelled` | cancel durable schedules | Derived | purchase lifecycle | Via truth | Leftover dues |
| `recovery_classified` | attribution levels | Derived | `purchase_attribution_v1` | Via truth | Fake ROI |
| `purchase_unattributed` | `not_attributed` / `organic_or_unknown` | Derived | attribution | Via truth | Mislabel recovery |
| `provider_failure` | `log_provider_failure` | Internal-only | provider paths | Sim-safe adapter | Silent loss |
| `retry_scheduled` | retry/reschedule | Partial | internal | Only where implemented | Fake retries |
| `retry_exhausted` | exhausted statuses | Partial | internal | Only where implemented | Same |
| `data_insufficient` | KL insufficient confidence | Derived | `knowledge_insights_v1` | Tiny sample; read KL | Injected insight |
| `evidence_threshold_reached` | sample thresholds | Derived | KL | Observe after volume | Fake threshold event |
| `knowledge_candidate_created` | — | Unsupported | — | Never ingest; KL computes | Parallel knowledge pipeline |
| `knowledge_routed` | `knowledge_routing_v1` | Derived | Daily Brief path | Observe routed items | Fake routing |
| `recommendation_suppressed` | decision suppression | Derived | decision layer | Observe | Fake suppression rows |

**Platform timeline statuses (use these; do not invent parallel vocabulary):**  
`scheduled` → `delay_started` → `before_send` → `provider_queued` → `provider_sent` → `webhook_delivered` → `customer_reply` → `continuation_started`

---

## 5. Unsupported or Missing Events

| Event / gap | Why unsupported / missing | Required for V1? | Recommended treatment |
|-------------|---------------------------|------------------|------------------------|
| `session_started` | No durable ingest | No | **mark unsupported** |
| `page_viewed` | No durable ingest | No | **mark unsupported** |
| `product_viewed` | No durable analytics event | Nice-to-have | **simulate through** cart lines / product ids on sync; mark event unsupported |
| `category_viewed` | No durable ingest | No | **mark unsupported** / **defer** |
| `scroll_depth_reached` | No durable ingest | No | **mark unsupported** / **defer** |
| `dwell_time_recorded` | Client-only | No | **mark unsupported** / **defer** |
| `product_revisited` | No named event | Partial scenarios | **simulate through** multi-session sync; mark named event unsupported |
| `checkout_step_viewed` | No durable ingest | No | **mark unsupported** |
| `session_ended` | No durable ingest | No | **mark unsupported** |
| `widget_eligible` | Client heuristics | No | **mark unsupported** |
| `widget_opened` | No durable ingest | S09 honesty | **mark unsupported**; model journey without reason POST |
| `widget_ignored` | No named event | S09 | **simulate through** absence of reason; mark unsupported as event |
| `widget_closed` | No durable ingest | No | **mark unsupported** |
| `whatsapp_ignored` | Inference only | S05/S11 | **simulate through** no reply + no purchase; mark unsupported as event |
| `knowledge_candidate_created` | KL is computed | No as ingest | **mark unsupported**; observe KL outputs |
| Spec reasons: comparing/trust/payment | No platform tags | S10 | **simulate through** mapped tags (`thinking`/`quality`/`other`); document mapping |
| Historical HTTP timestamps | Writers use wall-clock | **Yes for multi-day honesty** | Phase 2 Timestamp Authority (decision required) — not “fake events” |
| Simulation provider adapter | Missing dedicated wrapper | **Yes for safety** | **implement** Phase 2 adapter over mock/skip |
| Run-scoped cleanup model | Lab reset is identity purge | **Yes** | **implement** Phase 2 run tagging + cleanup |
| Remote Reality control surface | Lab HTTP incomplete in some deploys | Yes for ops | **implement** locked admin/dev route in Phase 2 |

---

## 6. Direct Insert / Bypass Risks

### 6.1 Cannot currently be created “as history” through normal HTTP alone

| Need | Gap | Implication |
|------|-----|-------------|
| Backdated `AbandonedCart.first_seen_at` / `last_seen_at` | cart-event stamps now | Timestamp Authority or writer extension |
| Backdated reason logs | reason API stamps now | Same |
| Backdated timeline `created_at` | `record_recovery_truth_event` hardcodes now | Same |
| Backdated schedule `due_at` relative to abandon | armed as now+delay | Recompute after historical abandon time |
| Conversion with historical `purchase_time` | HTTP ignores `purchase_time` | Call `ingest_purchase_truth(..., purchase_time=)` internally |
| Storefront page/scroll/dwell rows | No ingest | Do not invent |

### 6.2 Derived tables / artifacts — never write directly

| Artifact | Why |
|----------|-----|
| Knowledge insights / report rows (if any cache) | Computed by KL |
| Merchant Decision / Pulse / shadow Decision seed cards | Would fake intelligence |
| Dashboard snapshot totals / monthly snapshot bodies | Built by snapshot builder |
| Attribution level as static label without truth+evidence | Computed by attribution |
| `sent_real` delivery truth for sim customers | Contaminates provider truth |
| Commerce Signals as stored fake events | Derived, not a write API |

### 6.3 Unavoidable bootstrap records (justified)

| Bootstrap | Justification |
|-----------|---------------|
| Ensure `Store(zid_store_id="demo")` exists | Lab already soft-provisions |
| Seed demo catalog JSON if empty | `cartflow_demo_catalog_seed` / `demo_sandbox_catalog` |
| Simulation run / checkpoint / report archive rows (Phase 2 models or equivalent) | Orchestration metadata — not merchant truth |
| Provenance envelope on context/JSON columns (`simulation_run_id`, …) | Traceability + cleanup scope |

### 6.4 Proposed direct inserts with exact justification

| Proposed write | Allowed? | Justification |
|----------------|----------|---------------|
| Simulation run metadata | Yes | Orchestration only |
| Provenance tags on created operational rows | Yes | Isolation/cleanup/idempotency |
| Timestamp Authority field corrections on run-tagged rows | **Only if approved** | Platform lacks historical HTTP clocks; must be explicit, audited, accounted |
| Direct `RecoverySchedule` / timeline / log inserts as primary truth | **No** | Bypasses materialization, gates, movement hooks (anti-pattern of `sim-store-*` report) |
| Direct `PurchaseTruthRecord` without ingest | **No** | Skips cancel/closure/attribution |
| Direct KL/Decision/dashboard values | **No** | Violates core principle |

---

## 7. Identity and Traceability Design

| Identifier | Design |
|------------|--------|
| `simulation_run_id` | UUID/ulid per execute; cleanup/archive key; required on every generated record’s provenance |
| `simulation_scenario_id` | Registry key e.g. `S03_shipping_cost_hesitation` |
| `simulation_customer_id` | Stable within run; drives repeat-visit identity |
| `simulation_session_id` | Per visit/session |
| `simulation_cart_id` | Cart fragment for recovery identity |
| `simulation_product_id` | Maps to demo catalog `id` (`demo_{key}`) |
| `simulated_event_id` | Deterministic from seed+plan index; idempotency key |

**Proposed recovery_key:**

```text
demo:srs_{run_short}_{customer_short}_{cart_short}
```

First segment must remain `demo` for existing parsers/dashboard attach.

**Provenance envelope (JSON on allowed context columns):**

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

**Idempotency:**

- Natural HTTP paths today lack client `Idempotency-Key` headers.
- Simulator ledger enforces idempotency on `simulation_run_id + simulated_event_id`.
- Purchase re-ingest is mostly no-op via `has_purchase(recovery_key)`; reason logs may append — ledger must prevent duplicate reason spam on resume.

**Demo isolation:**

- Hard reject non-`demo`.
- No writes to production merchant stores.
- Distinct from `sim-store-*` namespace (load tests).

---

## 8. Historical Time Design

### 8.1 Deterministic clock

- `SimulationClock` advances per planned event.
- Same `(scenarios, start_date, duration_days, seed, scale)` → same plan timestamps and outcomes.

### 8.2 Backdated timestamp handling (current platform)

| Writer | Historical support today |
|--------|--------------------------|
| `/api/cart-event` | No |
| `/api/cartflow/reason` | No |
| `/api/conversion` | Does not pass `purchase_time` |
| `ingest_purchase_truth(..., purchase_time=)` | Yes (internal) |
| `record_recovery_truth_event` | No (`created_at=_utc_now()`) |
| `apply_movement_event(..., event_at=)` | Partial (`event_at` accepted; row created_at still now; monotonic guard) |

### 8.3 Chronological processing

- Plan sorted by simulated timestamp.
- Execute in that order within batches.
- Midnight crossings, multi-day returns, monthly windows must be real for KL/monthly snapshots.

### 8.4 Scheduler behavior with historical dates

- If schedules are armed at wall-clock now, `due_at` will be wrong for history.
- Phase 2 must set `due_at` / `scheduled_at` relative to **simulated abandon time**, then progress send/cancel according to simulated timeline (under mock/safe adapter).
- Must not flood the live due scanner with thousands of immediately-due historical rows on a shared worker without bounds/isolation.

### 8.5 Purchase and return timing

- Attribution windows depend on gaps between send and purchase — requires honest historical timestamps.
- Returns must update movement with simulated ordering; platform field names: `returned_at`, `passive_return_visit_count`.

### 8.6 Risks of using current runtime time

- Dashboard/KL/monthly windows collapse to “today”.
- Attribution over-confirms or under-confirms incorrectly.
- Scenario 20 (60 days) becomes a load test, not historical merchant reality.
- Reconciliation “purchases vs monthly totals” becomes meaningless.

**Recommended Phase 2 direction (pending approval):** Timestamp Authority Adapter after real ingress, with explicit accounting flag `timestamp_authority_applied`.

---

## 9. Safety Design

| Control | Design |
|---------|--------|
| No real WhatsApp sends | Safe provider adapter + WA disabled / ops pause + `mock_sent` only |
| No real provider API calls | Adapter blocks Twilio/Meta for sim customers |
| No merchant alerts | Suppress VIP merchant alert path for simulation |
| No billing impact | No plan/subscription mutations |
| No non-demo data changes | Hard store gate |
| No hidden global feature flags | Process/run-local config only |
| Cleanup isolation | `simulation_run_id` only; audited deletes |
| No silent event loss | Accounting buckets reconcile |

---

## 10. Observability and Accounting

### 10.1 Buckets

| Bucket | Meaning |
|--------|---------|
| `planned` | In deterministic plan |
| `persisted` | Operational/bootstrap row written |
| `processed` | Platform pipeline side effects completed |
| `rejected` | Gate rejected with explicit reason |
| `unsupported` | No platform capability; reported |
| `failed` | Error during execute |
| `replayed` | Intentional re-process after interrupt policy |
| `duplicate_suppressed` | Idempotent skip of already-handled event |

### 10.2 Reconciliation approach

Identity:

```text
planned = persisted + rejected + unsupported + failed (+ in-flight if paused)
```

Additional surfaced checks (never auto-hide):

- Planned purchases vs Purchase Truth  
- Purchases vs closed/completed carts  
- Purchased carts vs cancelled schedules  
- Returns vs movement snapshots  
- Widget reasons vs persisted tags  
- WA replies vs attention  
- Knowledge claims vs evidence sample sizes  
- Dashboard/monthly totals vs canonical (after snapshot rebuild)  
- No-phone / VIP counts vs row semantics  
- Simulation events vs timeline events (where applicable)

Structured logs must include `simulation_run_id` (not console-only).

---

## 11. Open Questions

### Q1 — Timestamp Authority strategy

- **Question:** How should Phase 2 implement historical timestamps?
- **Why needed:** Without this, multi-day/60-day runs are not honest merchant history.
- **Options:**  
  A) Post-write Timestamp Authority on run-tagged rows  
  B) Process-local clock injection  
  C) Extend production writers with optional `event_at` (product change)
- **Recommended:** **A**
- **Risks:** A — must be careful and audited; B — unsafe with concurrent workers; C — expands production surface beyond simulator program
- **Blocks Phase 2?** **Yes** for any historical execute design (DRY RUN planner can proceed without it)

### Q2 — Orchestration persistence model

- **Question:** New tables (`simulation_runs`, event ledger) vs provenance JSON only?
- **Why needed:** Cleanup, resume, accounting, report archive.
- **Options:** New tables · JSON-only · hybrid (run table + JSON on ops rows)
- **Recommended:** **Hybrid**
- **Risks:** Tables = migration; JSON-only = weak resume/cleanup queries
- **Blocks Phase 2?** **Yes** (schema/approach)

### Q3 — Cleanup vs Lab fixtures

- **Question:** May cleanup delete only `simulation_run_id`-tagged rows, leaving untagged Lab fixtures?
- **Why needed:** Avoid destroying Lab Scenario identity accidentally.
- **Options:** Tagged-only · tagged + explicit Lab reset opt-in · full demo purge
- **Recommended:** **Tagged-only** (Lab reset remains separate)
- **Risks:** Tagged-only may leave orphans if tagging fails; full purge is destructive
- **Blocks Phase 2?** **Yes** for cleanup module

### Q4 — Attribution language in reports

- **Question:** Use platform levels or spec phrase “Possible Influence”?
- **Why needed:** Avoid inventing parallel vocabulary.
- **Options:** Platform levels only · dual-label mapping table in reports
- **Recommended:** Platform levels + mapping footnote (`assisted_recovery` ≈ possible influence)
- **Risks:** Dual labels confuse; platform-only may confuse readers of the brief
- **Blocks Phase 2?** No (report wording)

### Q5 — Storefront behavioral events

- **Question:** Keep unsupported until real ingest exists?
- **Why needed:** Prevent fake analytics that KL/dashboard cannot honestly use.
- **Options:** Unsupported · implement canonical ingest (product work) · proxy-only with clear labels
- **Recommended:** **Unsupported + limited proxies** (cart lines / multi-session) without durable fake events
- **Risks:** Product ingest is out of simulator scope; proxies may be over-read
- **Blocks Phase 2?** No

### Q6 — Knowledge Routing validation scope

- **Question:** Validate only Daily Brief consumer first?
- **Why needed:** Other surfaces partially migrated.
- **Options:** Brief-only · all surfaces · skip routing validation in V1
- **Recommended:** **Brief-only** + note gaps
- **Risks:** Incomplete UX review; overclaiming routing coverage
- **Blocks Phase 2?** No

### Q7 — Delivery webhook simulation

- **Question:** Include `whatsapp_delivered` / `webhook_delivered` in V1?
- **Why needed:** Delivery truth ≠ sent; fake webhooks can mislead.
- **Options:** Defer · isolated sim webhook injector · never
- **Recommended:** **Defer** for Phase 2 core; optional later under isolation
- **Risks:** Defer limits delivery-truth scenarios; injector risks fake delivery
- **Blocks Phase 2?** No

### Q8 — Ops pause vs store WA flag during execute

- **Question:** How to guarantee no real sends without affecting other demo use?
- **Why needed:** Safety non-negotiable.
- **Options:** Store flag flip with restore · platform ops pause · adapter-only block
- **Recommended:** **Adapter-only block + store WA off for execute prep**, restore documented; avoid global ops pause unless necessary
- **Risks:** Flag flip races with human demo use; global pause affects broader platform
- **Blocks Phase 2?** **Yes** for safe provider adapter

---

## 12. Recommended Phase 2 Scope

### 12.1 Build first

1. Simulation run model + event ledger + checkpoints (per Q2).  
2. Demo hard gates + provenance tagging.  
3. Seeded deterministic planner (DRY RUN complete).  
4. Safe provider adapter (per Q8).  
5. Ingress adapters for Supported/Partial HTTP+internal paths (Lab Scenario 1 pattern).  
6. Timestamp Authority (per Q1 approval).  
7. Event accounting + structured logging.  
8. Cleanup/archive boundaries (per Q3).  
9. Restricted admin/dev control surface (Dry Run / Execute / Pause / Resume / Cancel / Cleanup / Report).  
10. Unit/integration tests for determinism, isolation, no outbound, accounting, idempotency, resume, cleanup.

### 12.2 Remain deferred

- Implementing new storefront behavioral ingest (`page_viewed`, scroll, dwell, …) as product features  
- AI recommendations  
- Production writer API redesign beyond approved Timestamp Authority  
- Using `sim-store-*` report as merchant reality  
- Injecting KL/Decision/dashboard values  
- Full 60-day execute (Phase 4)  
- Product defect fixes discovered by simulation (Phase 5 review only)  
- Delivery webhook simulation (unless later approved)

### 12.3 Proposed acceptance criteria (Phase 2 exit)

- DRY RUN produces complete plan with unsupported inventory and ETA  
- EXECUTE on demo-only with zero real provider calls (test-proven)  
- Every event lands in an accounting bucket; totals reconcile  
- Idempotent re-run does not duplicate  
- Resume after interrupt works  
- Cleanup removes only selected run  
- Timestamp strategy matches approved Q1 decision and is auditable  
- No non-demo mutations  
- Control surface locked to admin/dev  
- **STOP for review** before Phase 3 small validation run

### 12.4 Proposed stop condition

Phase 2 stops when core infrastructure + DRY RUN + safety proofs exist and reviewers approve proceeding to Phase 3 (3-day small validation). No Phase 3/4 execution without that review.

---

## 13. Evidence Appendix

### 13.1 Relevant files inspected

| Area | Paths |
|------|-------|
| Lab | `services/demo_lab_scenario1_v1.py`, `services/demo_lab_reset_v1.py` |
| Catalog | `services/demo_sandbox_catalog.py`, `services/cartflow_demo_catalog_seed.py` |
| Anti-pattern sim | `services/cartflow_simulation_report_v1.py` |
| Purchase | `services/purchase_truth.py`, `services/cartflow_purchase_truth.py`, `services/purchase_attribution_v1.py`, `services/knowledge_purchase_attribution_v1.py` |
| Timeline | `services/recovery_truth_timeline_v1.py` |
| Movement | `services/customer_movement_snapshot_v1.py` |
| Reasons | `services/store_reason_templates.py`, `routes/cartflow.py` |
| Knowledge | `services/knowledge_layer_v1.py`, `knowledge_insights_v1.py`, `knowledge_types_v1.py`, `knowledge_routing_v1.py` |
| VIP | `services/vip_cart.py`, `services/vip_abandoned_cart_phone.py` |
| Snapshots | `services/dashboard_snapshot_builder_v1.py`, `dashboard_snapshot_v1.py` |
| Ops | `services/operational_control_v1.py` |
| Design outputs | `docs/architecture/store_reality_simulator_v1_*.md` |
| Summary | `docs/SYSTEM_SUMMARY.md` §10 entry 2026-07-15 |

### 13.2 Important signatures / references

```python
# services/purchase_truth.py
def ingest_purchase_truth(..., purchase_time: Optional[datetime] = None, ...) -> bool

# services/recovery_truth_timeline_v1.py
def record_recovery_truth_event(*, recovery_key, status, source, ...) -> bool
# created_at=_utc_now() — no override

# services/customer_movement_snapshot_v1.py
def apply_movement_event(*, recovery_key, event_type, event_at: Optional[datetime] = None, ...) -> bool

# services/store_reason_templates.py
_REASON_TAGS = frozenset({"price", "shipping", "warranty", "thinking", "quality", "delivery", "other"})

# services/purchase_attribution_v1.py
# LEVEL_CONFIRMED / LEVEL_LIKELY / LEVEL_ASSISTED / LEVEL_ORGANIC / LEVEL_NOT_ATTRIBUTED

# services/knowledge_types_v1.py
MIN_HESITATION_SAMPLE = 3
```

Lab Scenario 1 truth path (gold template): HTTP orchestration in `services/demo_lab_scenario1_v1.py` (`SCENARIO_ID = "lab_v1_recovery_to_purchase"`).

### 13.3 Probe failures

| Failure | Detail | Affected conclusions? |
|---------|--------|------------------------|
| Shell `rg --head-limit` | Windows/local `rg` rejected `--head-limit` (exit code 2) during a parallel probe | **No** — partial output still returned purchase ingest signatures; conclusions confirmed via Read/Grep/explore agents |

### 13.4 Capability readiness (rollup)

| Layer | Status |
|-------|--------|
| Demo isolation | Fully |
| Widget reason / phone / handoff | Fully |
| Cart abandon/sync | Fully |
| Schedules + cancel on purchase | Fully |
| Purchase Truth + attribution | Fully |
| KL report (derived) | Fully |
| Movement writers | Partial |
| Knowledge Routing consumers | Partial |
| Attention/Home | Partial |
| Time Machine | **Missing integration** |
| Run-scoped simulator infra | **Missing** |
| Safe provider adapter | **Missing** (composable from mock/flags) |

---

## STOP

Phase 1 report complete.

**Do not start Phase 2 until open questions Q1, Q2, Q3, and Q8 are decided.**

No implementation, migrations, or production logic changes are included in this Phase 1 report deliverable beyond documentation.
