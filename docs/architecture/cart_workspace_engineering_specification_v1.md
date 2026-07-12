# Cart Workspace Engineering Specification V1

**Status:** Implementation-ready engineering specification  
**Date (UTC):** 2026-07-12  
**Nature:** Exact module ownership, contracts, runtime truth flow P0→P4, migration, and tests.  
**Not:** implementation, Figma, CSS, database migration scripts, or Product Governance changes.

---

## Permanent principles

1. **Architecture translates Product Truth. Engineering translates Architecture exactly once.**  
2. **Every product rule compiles exactly once** — one owner for Ownership, one for Admission, one for Projection; Rendering has no business logic.  
3. **No duplicated decision logic** across API, scheduler, frontend, projection, renderer, or background jobs.  
4. **Deferred Product OQs remain hooks** — Engineering must not invent T4/T6/T12 policy (OQ-1, OQ-2, OQ-4).

---

## Authoritative inputs (read-only)

| # | Document |
|---|----------|
| 1 | [`cart_workspace_constitution_v2.md`](../product/cart_workspace_constitution_v2.md) |
| 2 | [`cart_workspace_constitutional_decisions_log_v1.md`](../product/cart_workspace_constitutional_decisions_log_v1.md) |
| 3 | [`cart_workspace_glossary_v1.md`](../product/cart_workspace_glossary_v1.md) |
| 4 | [`merchant_decision_and_ownership_map_v1.md`](../product/merchant_decision_and_ownership_map_v1.md) |
| 5 | [`decision_admission_matrix_v1.md`](../product/decision_admission_matrix_v1.md) |
| 6 | [`cart_workspace_ux_blueprint_v1.md`](../product/cart_workspace_ux_blueprint_v1.md) |
| 7 | [`cart_workspace_operational_behavior_blueprint_v1.md`](../product/cart_workspace_operational_behavior_blueprint_v1.md) |
| 8 | [`cart_workspace_architecture_review_v1.md`](cart_workspace_architecture_review_v1.md) |

---

## Deliverables index

| Deliverable | Part |
|-------------|------|
| Module responsibility map | 1, 18 |
| Canonical contracts | 2 |
| Decision identity | 3 |
| Ownership execution | 4 |
| Admission compiler | 5 |
| Workspace projection + grid/card | 6–7 |
| Merchant action + WhatsApp handoff | 8–9 |
| Live-update + failure | 10–11 |
| Performance + persistence | 12–13 |
| Migration plan | 14 |
| Test architecture | 15 |
| Observability + security | 16–17 |
| File/dependency map | 18 |
| Deferred Product hooks | 19 |
| Risk register + verdict | 20 |

---

# Plane boundaries (P0–P4)

| Plane | Implementation boundary | Must never |
|-------|-------------------------|------------|
| **P0 Truth** | Existing Lifecycle / Purchase / Provider / Recovery / Evidence peers | Know cards, zones, CSS, visual presentation |
| **P1 Ownership** | `services/cart_workspace/` ownership modules | Render UI; decide visual ordering |
| **P2 Admission** | Compiled Admit/Reject modules | Dynamic constitutional reasoning; frontend state; hot-path history scans |
| **P3 Projection** | Workspace projection modules | Alter ownership or admission |
| **P4 Rendering** | `static/cart_workspace_*` paint + dispatch | Infer Decision; classify ownership; recalculate Admit; invent Status; merge unrelated cases; derive truth from DOM |

**Relation to existing `merchant_decision_layer_v1`:** That module is a peer proof→decision helper for other surfaces. **Cart Workspace Admit/Reject (P2) is the sole authority** for whether a Decision consumes Workspace attention. Other layers may supply Proof inputs; they must not create Workspace cards or duplicate Admit.

---

# Part 1 — Module Inventory

Smallest structure that preserves ownership clarity. Prefer a package over growing `main.py`.

## 1.1 Proposed package

```text
services/cart_workspace/
  __init__.py
  contracts_v1.py
  ownership_v1.py
  admission_v1.py
  decision_identity_v1.py
  projection_v1.py
  commands_v1.py
  handoff_contract_v1.py
  live_update_v1.py
  observability_v1.py

routes/cart_workspace_v1.py

static/
  cart_workspace_render_controller_v1.js
  cart_workspace_api_v1.js
```

Feature flag (default **off**): `CARTFLOW_CART_WORKSPACE_V1`

## 1.2 Module responsibility map

| Module | Path | Sole responsibility | Inputs | Outputs | Dependencies | Prohibited | Upstream | Downstream |
|--------|------|---------------------|--------|---------|--------------|------------|----------|------------|
| **Contracts** | `services/cart_workspace/contracts_v1.py` | Typed contracts / dataclasses / enums for all Part 2 shapes | — | Contract types + validators | stdlib only | Business rules; DB | Architecture contracts | All CW modules |
| **Ownership** | `services/cart_workspace/ownership_v1.py` | Dual-axis state + T1–T12 transitions + Override mode + anti-oscillation | Trigger + evidence refs + current ownership | New ownership state + transition audit | contracts; P0 truth readers (read-only) | Admit; projection; UI; invent T4/T6/T12 policy | Ownership Map | Admission (posture), Commands, Projection |
| **Admission** | `services/cart_workspace/admission_v1.py` | Compiled R01–R20 Admit/Reject + gates + audit fields | Proof bundle + ownership posture + fingerprint | `AdmissionResult` | contracts; ownership read; decision_identity | UI; ownership write except via explicit Admit→T1/T2 handoff API; history scan | Admission Matrix | Ownership (T1/T2 request), Decision persist, Projection |
| **Decision identity** | `services/cart_workspace/decision_identity_v1.py` | Stable `decision_id` / fingerprint rules; open-Decision uniqueness | store_slug, recovery_key, evidence_fingerprint, path | identity keys; duplicate detection | contracts | Ranking; rendering | AS-1 / AI-10 | Admission, Projection |
| **Projection** | `services/cart_workspace/projection_v1.py` | Build merchant WorkspaceProjection (zones A–E, cards, rollups, freshness metadata) | Open Decisions + ownership + rollups | `WorkspaceProjection` | contracts; ownership read; outcome rollups helpers in same module | Admit; ownership mutate; Status taxonomy | Architecture P3 | API, Live update, P4 |
| **Commands** | `services/cart_workspace/commands_v1.py` | Validate + execute Merchant Action Commands; emit expected transitions | `MerchantActionCommand` | Command result + side-effect intents | ownership; admission ledger read; handoff_contract | Rendering; inventing deferred OQ commands | Behavior Blueprint actions | Ownership T3; Projection rebuild; audit |
| **Handoff contract** | `services/cart_workspace/handoff_contract_v1.py` | Eligibility + automation suppression/resume contracts for WhatsApp path | Decision + store WhatsApp readiness + phone | `HandoffEligibility` / intents | P0 provider readiness readers; contracts | Provider-specific send implementation | Product handoff req | Commands |
| **Live update** | `services/cart_workspace/live_update_v1.py` | Envelope versioning, fingerprint compare, accept/reject reasons | Prior + candidate projection | Accept/Reject + reason | contracts; projection | Polling policy theater; business Admit | Architecture AR-4 | API + P4 |
| **Observability** | `services/cart_workspace/observability_v1.py` | Bounded correlation fields for logs/metrics hooks | Context ids | Structured log fields | contracts | Full OE framework | Architecture Part 16 intent | All writers |
| **HTTP routes** | `routes/cart_workspace_v1.py` | Authz, wire flag, call services, return contracts | HTTP | JSON of contracts | services only | Business logic copies | — | Frontend |
| **Render controller** | `static/cart_workspace_render_controller_v1.js` | P4 composition from projection + freshness; dispatch commands | Projection envelope | Render plan → presenters | api helper | Admit/ownership/zone membership invention | Architecture P4 | DOM presenters |
| **API client** | `static/cart_workspace_api_v1.js` | Fetch/post envelopes; idempotency keys | — | Network I/O | — | Truth derivation | — | Render controller |

**Consolidation note:** Zone projection + outcome rollups live **inside** `projection_v1.py` as internal functions — not separate files — unless size forces a split later. Same for admission audit helpers inside `admission_v1.py`.

**`main.py`:** Register router + feature flag wiring only. No Admit/Ownership/Projection logic.

---

# Part 2 — Canonical Data Contracts

**Contract version:** `cart_workspace_contracts_v1`  
All envelopes carry `contract_version: "v1"`.

## 2.1 Ownership State

| Field | Req | Notes |
|-------|-----|-------|
| `store_slug` | Y | Isolation |
| `recovery_key` | Y | Canonical subject |
| `execution_owner` | Y | `cartflow` \| `merchant` |
| `decision_owner` | Y | `cartflow` \| `merchant` |
| `override_mode` | Y | `inactive` \| `active` |
| `journey_phase` | Y | `active` \| `completed` \| `archived` |
| `updated_at` | Y | UTC ISO |
| `last_transition_id` | O | Audit link |
| `source_refs` | O | Evidence / policy ids |

**Invariants:** Exactly one owner per axis; Override is mode not owner; S1–S9 derived not stored as competing enum.

**Stable identity:** `(store_slug, recovery_key)`.

## 2.2 Admission Result

| Field | Req | Notes |
|-------|-----|-------|
| `outcome` | Y | `admit` \| `do_not_admit` |
| `matrix_row_id` | Y | e.g. `R07` |
| `governing_reason` | Y | AA-1 single reason |
| `failed_gate` | O | On reject |
| `admitting_gate` | O | On admit |
| `rejection_code` | O | RJ-* |
| `evidence_fingerprint` | Y | Stability key |
| `ownership_posture` | Y | Exec/Dec snapshot used |
| `human_gain_justification` | O | On admit / Override |
| `expected_merchant_action` | O | Exactly one if admit |
| `admission_id` | Y | Durable id |
| `evaluated_at` | Y | UTC |
| `override_path` | Y | bool |

**Invariant:** Binary only. Same fingerprint + governance → same outcome (AI-18).

## 2.3 Decision Record

One admitted human Decision. One identity → one visible card while open.

| Field | Req | Notes |
|-------|-----|-------|
| `decision_id` | Y | Stable UUID/ulid |
| `recovery_key` | Y | Subject |
| `store_slug` | Y | |
| `admission_id` | Y | Links ledger |
| `admission_rule_id` | Y | Matrix row |
| `governing_reason` | Y | |
| `execution_owner` | Y | At admit (usually cartflow) |
| `decision_owner` | Y | `merchant` while open |
| `override_mode` | Y | |
| `decision_class` | Y | `normal` \| `override` |
| `required_action` | Y | Single action id |
| `explanation` | Y | Object: why_here, cartflow_did, why_stopped, expected_after |
| `evidence_refs` | Y | List of evidence ids |
| `evidence_fingerprint` | Y | |
| `admitted_at` | Y | |
| `resolved_at` | O | Set on close |
| `status` | Y | `open` \| `resolving` \| `closed` |
| `projection_version` | O | Last projected |
| `order_key` | Y | Stable sort (`admitted_at` default) |

**Invariants:** AI-5 one Action; AS-1 one Admit per fingerprint while open; no Status taxonomy as class.

## 2.4 Workspace Projection

| Field | Req | Notes |
|-------|-----|-------|
| `store_slug` | Y | |
| `projection_id` | Y | Build id |
| `projection_version` | Y | Monotonic per store |
| `projection_fingerprint` | Y | Hash of entity set + order + rollup stamps |
| `built_at` | Y | |
| `freshness` | Y | `final` \| `revalidating` \| `uncertain` \| `degraded` |
| `workspace_phase` | Y | Derived WL-* code |
| `zone_a` | Y | DecisionCard[] |
| `zone_b` | Y | DecisionCard[] |
| `zone_c` | Y | ZoneSummary |
| `zone_d` | Y | CompletedOutcomeRollup |
| `zone_e` | Y | OperationalHealthException \| null |
| `attention_focus_decision_id` | O | |
| `quiet` | Y | bool — A and B empty |
| `last_good_retained` | O | bool |

## 2.5 Decision Card (projection shape)

Subset of Decision Record + merchant-safe fields only. Key = `decision_id`.

Must answer: why here; what CartFlow did; why stopped; what to decide; what after action.

## 2.6 Zone Summary (Zone C)

| Field | Req |
|-------|-----|
| `visible` | Y |
| `kind` | Y — `reassurance` only |
| `summary` | Y — calm copy key/text |
| `active_recovery_indicator` | O — aggregate bool/count bounded |

**Forbidden:** per-cart Status list.

## 2.7 Completed Outcome Rollup (Zone D)

| Field | Req |
|-------|-----|
| `window` | Y — e.g. recent N / 24h |
| `completed_count` | Y |
| `recent_items` | Y — bounded list (cap ≤ 5 conceptual) |
| `rollup_version` | Y |
| `updated_at` | Y |

**Forbidden:** unbounded history browser.

## 2.8 Operational Health Exception (Zone E)

| Field | Req |
|-------|-----|
| `exception_id` | Y |
| `merchant_actionable` | Y — must be true to surface |
| `summary` | Y |
| `severity` | Y — bounded enum |
| `created_at` | Y |

Default projection: `zone_e = null`.

## 2.9 Live Update Envelope

| Field | Req |
|-------|-----|
| `envelope_id` | Y |
| `store_slug` | Y |
| `projection_version` | Y |
| `projection_fingerprint` | Y |
| `payload` | Y — WorkspaceProjection |
| `supersedes_version` | O |
| `emitted_at` | Y |

## 2.10 Merchant Action Command

| Field | Req |
|-------|-----|
| `command_id` | Y — idempotency key |
| `command_type` | Y |
| `store_slug` | Y |
| `decision_id` | Y |
| `recovery_key` | Y |
| `actor_merchant_user_id` | Y |
| `payload` | O — command-specific |
| `client_viewport` | O — telemetry only; **not** truth |
| `issued_at` | Y |

---

# Part 3 — Decision Identity Specification

## 3.1 Canonical identity

```text
decision_id          = durable id minted at Admit
evidence_fingerprint = hash(store_slug, recovery_key, proof_class, material_evidence_ids, matrix_path)
open_uniqueness      = at most one open Decision per (store_slug, recovery_key, evidence_fingerprint)
                       and AI-10: no second Admit while Decision Owner already Merchant for same Decision
```

**DOM / cart-row ids are never canonical.**

## 3.2 Lifecycle answers

| Question | Rule |
|----------|------|
| **When created?** | Admission `admit` via T1 or T2 only |
| **When updated?** | Open Decision: explanation material only (AS-3); same `decision_id` |
| **When resolved?** | T3 (Action), or T4/T5 when Product policy defined; status → closed; `resolved_at` set |
| **When may reappear?** | Only new Evidence fingerprint + full Admit pipeline after return to CartFlow (AS-4); or T12 reopen then pipeline — **not** same fingerprint |
| **New evidence required?** | Yes for re-Admit after close; refresh/poll/duplicate observe insufficient (AI-16) |
| **Duplicate webhooks / repeated observations?** | Idempotent; RJ-DUPLICATE / no transition (OS-3) |

## 3.3 Stability across surfaces

Same `decision_id` set for: API refresh, mobile/desktop, polling, projection rebuild, service restart (persisted Decision records — Part 13).

---

# Part 4 — Ownership Engineering

## 4.1 Sole writer

`ownership_v1.apply_transition(...)` is the **only** mutator of Execution Owner, Decision Owner, Override mode, and journey phase for Workspace subjects.

## 4.2 Legal transition table representation

Compile Ownership Map T1–T12 as a frozen table:

```text
TransitionSpec {
  id: T1…T12
  axis: decision | execution | override_mode | journey_phase
  from_predicate
  to_values
  required_evidence_refs
  idempotent: bool
}
```

Runtime: match trigger → validate predicate → write → append transition audit. No free-form mutation.

## 4.3 Trigger inputs (non-exhaustive, Product-aligned)

| Trigger class | May fire | Must not |
|---------------|----------|----------|
| Admit success | T1 / T2 | UI open |
| Action command success | T3 | |
| Completion / purchase truth | T5 / T10 | |
| Archive policy | T11 | |
| Override eligibility detect | T8 | Decision transfer alone |
| Override clear | T9 | Oscillate on dup VIP |
| **Deferred** expiry/return/supersede | T4 | **Invent timers** |
| **Deferred** manual exec handoff | T6 / T7 | **Invent scope** |
| **Deferred** reopen evidence | T12 | **Invent reopen** |

## 4.4 Idempotency & anti-oscillation

- Same transition id + same evidence → no-op success  
- T8 while `override_mode=active` → no-op (OS-4)  
- Duplicate fingerprint Admit → reject (OS-3)  
- T3 then immediate T1 without new Evidence → forbidden (OS-1, OE-5)

## 4.5 Audit

Every transition records: `transition_id`, axis, from, to, gate, evidence/policy ids, `at`, `correlation_id`.

## 4.6 VIP Override

T8 arms mode; T2 Admit creates Override Decision; Execution remains CartFlow unless deferred T6.

## 4.7 Merchant → CartFlow return

Primary implemented path: **T3** via Action Command. T4/T5 hooks reserved (Part 19).

---

# Part 5 — Admission Engineering

## 5.1 Representation of R01–R20

Frozen compiled ruleset in `admission_v1.py`:

```text
AdmissionRule {
  id: R01…R20
  predicates: ordered gate checks
  outcome: admit | do_not_admit
  destination_hint: S1|S2|S4|S7|S8|S9|unchanged
  rejection_code?: RJ-*
  expected_action?: action_id
}
```

No markdown load. No live AE/OE scoring.

## 5.2 Ordered evaluation (compiled shape)

Align to Matrix Part 8 conceptual compile:

1. completed/archived → reject  
2. duplicate fingerprint / open Decision → reject  
3. override eligible + override rules → admit T2  
4. insufficient proof → reject  
5. automation capable → reject  
6. human_gain ≤ attention_cost → reject  
7. normal admission rules → admit T1  
8. else unclassified → reject  

## 5.3 Outputs

Only `AdmissionResult` (Part 2.2). On Admit, caller invokes Ownership T1/T2 **through ownership module**, then persists Decision Record.

## 5.4 Rejection stability

Rejected remains rejected until new evidence / Override / policy trigger (AI-16). Scheduler ticks alone must not flip outcomes.

## 5.5 Testability

Golden vectors per R01–R20 + OST/AS cases; pure function over fixtures; no frontend; no full DB history required for unit gate tests.

## 5.6 Hot path

Admission runs on **Evidence-change / candidate evaluation** paths — not on every Workspace GET. GET reads open Decisions + projection only.

---

# Part 6 — Workspace Projection Specification

## 6.1 Build triggers

| Trigger | Behavior |
|---------|----------|
| Decision opened/closed/explanation patched | Rebuild or patch projection |
| Rollup update (completion) | Patch Zone D |
| Exceptional health assert/clear | Patch Zone E |
| Merchant GET Workspace | Read current projection / rebuild from open set if missing; **no** Admit |
| Soft revalidate | Refresh from source; keep last-good if uncertain |

## 6.2 Zone rules

| Zone | Content | Bound |
|------|---------|-------|
| **A** | Override DecisionCards only; dynamic; absent if empty | All open override Decisions (Attention Budget implies small) |
| **B** | Normal admitted DecisionCards only | Same |
| **C** | Reassurance summary — not cart queue | Single summary |
| **D** | Compact rollup | Cap recent_items (≤5); windowed counts |
| **E** | Rare merchant-actionable exception or null | 0–1 |

Status-based filters from current `#carts` **do not** define Workspace structure.

## 6.3 Ordering

1. All Zone A before Zone B  
2. Within zone: stable `order_key` (default `admitted_at` ascending); no reshuffle on refresh  
3. Optional governed ranker later — must not thrash (Architecture)

## 6.4 Freshness / version / last-good

- `projection_version` monotonic per `store_slug`  
- `projection_fingerprint` over decision ids + statuses + order + rollup_version + zone_e id  
- Last-good retained on uncertain/degraded when prior `final` exists  
- Empty A+B with `quiet=true` is success — not “no data”

## 6.5 Pagination

No unbounded pagination of Decisions. Open set is the page. Zone D bounded. Archive remains outside L2.

## 6.6 Degraded projection

May omit Zone C/D/E under pressure; **must not** omit known open Decisions; **must not** fabricate Quiet by dropping cards.

---

# Part 7 — Grid and Card Engineering Contract

**Grid-first** (behavior, not CSS).

## 7.1 VIP / Override surface

- Dedicated dynamic surface (Zone A), outside normal Decision grid  
- Immediate notification path remains P0/notify config (not P4)  
- Manual intervention via one clear `required_action`  
- CartFlow keeps Execution Ownership  

## 7.2 Decision Grid (Zone B)

- Responsive layout owned by P4 only  
- Bounded primary cards = open normal Decisions  
- Stable ordering; no unexpected movement  
- One card = one Decision = one primary action  
- Expandable details = explanation fields only when merchant expands (P4); content from P3  

## 7.3 Card contract fields (required)

| Merchant question | Field |
|-------------------|-------|
| Why is this here? | `explanation.why_here` ← governing_reason |
| What did CartFlow already do? | `explanation.cartflow_did` |
| Why did automation stop? | `explanation.why_stopped` |
| What must merchant decide? | `required_action` + label |
| What happens after? | `explanation.expected_after` |

---

# Part 8 — Merchant Action Commands

P4 dispatches; `commands_v1` owns validation/execution intents.

## 8.1 Command catalogue (v1 implementable)

| `command_type` | Allowed ownership | Expected transition | Decision resolution |
|----------------|-------------------|---------------------|---------------------|
| `approve_discount` | Dec=merchant; open Decision | T3 on success | close |
| `reject_exception` | same | T3 | close |
| `provide_information` | same | T3 | close |
| `fix_channel_configuration` | same | T3 | close |
| `take_over_conversation` | same; handoff eligible | T3 (+ automation suppress intent) | close or remain per handoff policy below |
| `dismiss_with_reason` | same | T3 (return) | close |
| `return_to_cartflow` | same | T3 | close |

**Note:** `take_over_conversation` must use Handoff contract (Part 9). It does **not** invent T6 Execution Ownership unless Product closes OQ-2; default: Decision resolves / automation suppressed for channel while Exec remains CartFlow observing.

## 8.2 Per-command engineering fields

Every command implements:

- `command_type` identity  
- allowed ownership state check  
- authz: merchant owns `store_slug`  
- `command_id` idempotency  
- payload validation  
- expected ownership transition  
- expected Decision resolution  
- failure: explicit error; no silent success  
- audit evidence via observability  

## 8.3 Explicitly deferred (do not implement triggers)

| Deferred | Reason |
|----------|--------|
| Policy auto-expiry commands | OQ-1 / T4 |
| Scoped manual execution handoff commands | OQ-2 / T6 |
| Archive reopen → Decision commands | OQ-4 / T12 |

Extension points: `ownership_v1` transition table entries marked `product_deferred=true`.

---

# Part 9 — WhatsApp Handoff (contracts only)

## 9.1 Eligibility contract

```text
HandoffEligibility {
  eligible: bool
  reasons: []          # why not, if false
  store_whatsapp_available: bool
  phone_available: bool
  provider_source: str   # from Provider Gateway readiness — no false delivery claim
  decision_id
  recovery_key
}
```

## 9.2 Runtime intents (not provider impl)

| Intent | Meaning |
|--------|---------|
| `suppress_automation_messaging` | Prevent duplicate auto+manual sends for subject |
| `observe_continues` | CartFlow Execution remains observer |
| `handoff_audit` | Record actor, time, channel target class |
| `resume_automation` | Only via explicit command/policy later |

## 9.3 Rules

- No false claim of provider delivery  
- No duplicated automated and manual communication  
- Provider-specific send lives behind existing Provider Gateway — this module only emits eligibility + intents  
- CS optional notify remains Override config (not Decision Owner)

---

# Part 10 — Live Update and Consistency

## 10.1 One contract for desktop and mobile

Same `WorkspaceProjection` entity set. Viewport may change layout only (P4). **No viewport-specific business truth.**

## 10.2 Version compare

```text
if incoming.version < local.version → reject STALE_OLDER
if incoming.version == local.version and fingerprint != local → reject CONFLICT_SAME_VERSION
if incoming.version > local.version → accept; replace; retain as last-good if freshness=final
if freshness in {uncertain, degraded} and last-good exists → keep showing last-good Decisions; badge freshness only
```

## 10.3 Accepted / rejected reasons (enum)

`ACCEPT` | `STALE_OLDER` | `CONFLICT_SAME_VERSION` | `FINGERPRINT_MISMATCH_POLICY` | `UNAUTHORIZED` | `FLAG_OFF`

## 10.4 Refresh triggers

- After successful Action Command  
- Explicit merchant refresh (read-only)  
- Server push/poll of **projection envelope** only  

**Do not** “solve freshness” by lengthening poll intervals as product behavior. Polling is transport; truth remains versioned projection.

## 10.5 Forbidden drifts

No independent Hero/count/card truth; no hidden stale cache that disagrees with `projection_version`; no blank repaint when last-good exists; no oscillation from duplicate envelopes.

---

# Part 11 — Failure and Degradation

| Failure | Behavior |
|---------|----------|
| Projection unavailable | Serve last-good if safe; else explicit degraded empty **without** claiming Quiet success if open Decisions unknown |
| Stale projection | Reject older envelopes; revalidate |
| Partial truth | Prefer open Decisions integrity over C/D/E completeness |
| Provider outage | P0 retries; no Decision unless Admit R13; no Status theater |
| Duplicate event | Idempotent no-op |
| Delayed ownership transition | Action remains pending/failed explicit; do not pretend T3 |
| Admission compiler failure | Fail closed — Do Not Admit; alert ops via logs |
| Action command failure | Persist attempt audit; retry safe if idempotent; else explicit fail — **never silently lose** |
| DB pressure | Shed Zone C/D/E; keep open Decision reads; degrade freshness |
| Service restart | Reload from persisted Ownership + Decision records; rebuild projection |

**Rules:** Fail closed for new merchant Decisions; never fabricate calm; never fabricate work.

---

# Part 12 — Performance and Data Growth

## 12.1 Hot-path dependencies (allowed)

- Active / open Decision records for `store_slug`  
- Current ownership rows for those subjects  
- Bounded WorkspaceProjection  
- Compact Zone D rollups  

## 12.2 Forbidden on Workspace GET / Action

- Full timeline scans  
- All historical carts  
- Unbounded event tables  
- Complete message histories  
- Long scheduler history  

## 12.3 Budgets (engineering targets)

| Path | Budget |
|------|--------|
| GET projection (warm) | p95 ≤ 300 ms app-side target (exclude network) |
| Open Decision query | Indexed by `(store_slug, status=open)` |
| Projection size | Dominated by open cards; warn if > 50 open (Attention Budget smell) |
| Zone D recent_items | ≤ 5 |
| Admission eval | Fingerprint short-circuit; no full history |

## 12.4 Indexing requirements (logical)

- Open Decisions by store + status  
- Decision by `decision_id`  
- Fingerprint uniqueness for open rows  
- Ownership by `(store_slug, recovery_key)`  
- Rollups by store + window  

## 12.5 Archive boundary

Archived journeys outside open Decision queries; history surfaces separate.

---

# Part 13 — Persistence Decision Table

| Concern | Persist | Derive | Cache | Rebuildable | Retention |
|---------|---------|--------|-------|-------------|-----------|
| Ownership state | **Yes** | S1–S9 labels | Optional read cache | From audit+current | Active + audit |
| Decision records | **Yes** (open + closed) | Card view | Projection cache | From Decision table | Closed: audit retention policy |
| Admission ledger | **Yes** (admit + reject samples needed for AS-1) | — | — | No silent drop of fingerprints | Bounded; rejects may TTL later under Data Growth governance |
| Projection snapshot | **Optional cache** | Always from open set + rollups | Yes | **Yes** | Ephemeral |
| Action-command audit | **Yes** | — | — | No | Audit retention |
| Completed outcome rollups | **Yes** (compact) or incremental counters | Display | Yes | From completion events | Windowed |
| WL phase / zone membership | No | **Derive** | In projection | Yes | — |
| T4/T6/T12 policy timers | **Deferred** | — | — | — | Product OQ |

**No new tables in this document’s implementation phase without a separate migration governance task.** Spec mandates *what* must persist; schema design is a follow-on Engineering Migration Spec under existing Data Growth rules.

---

# Part 14 — Migration from Current Carts Page

Feature flag: `CARTFLOW_CART_WORKSPACE_V1=0` default.

| Stage | Name | Exit criteria |
|-------|------|---------------|
| **M0** | Inventory current `#carts` sources, RSC, APIs | Dependency map documented |
| **M1** | Shadow ownership + admission compile | Logs only; no UI; parity fixtures |
| **M2** | Shadow Workspace projection | Compare entity counts vs expected Quiet/Admit scenarios |
| **M3** | Contract tests + parity | Desktop/mobile same entity set |
| **M4** | New renderer behind flag | Flag on for internal only |
| **M5** | Internal/demo production validation | Scenario checklist pass |
| **M6** | Merchant rollout | Gradual; monitor Quiet/Admit metrics |
| **M7** | Retire obsolete status-driven surface | **Only after explicit approval** |

**Requirements:** Build beside current page; current cart truth remains authoritative during shadow; no destructive DB migration; no archive/history loss; rollback = flag off; mobile-first validation; production scenario validation.

**Do not implement in this task.**

---

# Part 15 — Test Architecture

| Layer | Proves |
|-------|--------|
| Constitutional contract tests | Planes / forbidden imports / one-owner rules |
| Ownership transition tests | T1–T3, T5, T8–T11; deferred T4/T6/T12 hooks no-op/reject invent |
| Admission matrix tests | R01–R20 golden vectors |
| Decision identity / idempotency | Fingerprint; duplicate webhook; refresh |
| Projection tests | Zone membership; Quiet; ordering stability |
| Card-contract tests | Five explanation fields + one Action |
| Live-update parity | Desktop/mobile same entities; version reject |
| Action-command tests | Authz; idempotency; T3; failure explicit |
| Handoff eligibility tests | Phone/WhatsApp/provider honesty |
| Failure/degradation | Last-good; fail closed Admit |
| Performance/query-bound | No history scan on GET (query assert / explain) |
| Migration/rollback | Flag off restores old surface |
| Production scenario tests | Quiet, Override Admit, discount Admit, purchase completion |

Screenshots optional for visual approval; **not** sole proof of rules.

---

# Part 16 — Observability Contract

Bounded fields on every Admit / Transition / Command / Projection build:

| Field | Required |
|-------|----------|
| `correlation_id` | Y |
| `store_slug` | Y |
| `recovery_key` | When subject-scoped |
| `decision_id` | When Decision-scoped |
| `ownership_transition_id` | On transition |
| `admission_rule_id` / `governing_reason` | On Admit/Reject |
| `projection_version` | On projection I/O |
| `command_type` / `command_id` | On action |
| `first_divergence_stage` | On parity/shadow mismatch |
| `timestamps` | Y |

Not the Operational Excellence implementation — diagnosability only.

---

# Part 17 — Security and Authorization

| Rule | Spec |
|------|------|
| Merchant isolation | All queries scoped by authenticated merchant’s `store_slug` |
| Cross-store | Impossible by construction |
| Action authz | Actor must own store; Decision must be open for that store |
| Unauthenticated mutation | Reject |
| VIP notify recipients | Existing merchant notification config; not Workspace authz bypass |
| CS optional | Notify-only; no Decision/Execution ownership (I11) |
| Manual takeover audit | Required on `take_over_conversation` |
| Projection GET | Authn required; no public Decision leak |

---

# Part 18 — File and Dependency Map

## 18.1 Allowed dependency direction

```text
P0 truth readers
    ↑
ownership_v1 ← admission_v1 ← decision_identity_v1
    ↑                ↑
commands_v1      projection_v1 ← live_update_v1
    ↑
handoff_contract_v1 (readiness readers only)
    ↑
routes/cart_workspace_v1.py
    ↑
static render/api (HTTP only)
```

## 18.2 Prohibited imports

| Module | Must not import |
|--------|-----------------|
| `projection_v1` | admission write APIs; command executors |
| `admission_v1` | projection; static; routes |
| `ownership_v1` | projection; render |
| Render JS | Any reimplementation of R0x / T* |
| `main.py` | Copy of matrix/transition logic |

## 18.3 Public functions (conceptual)

| Module | Public API |
|--------|------------|
| `ownership_v1` | `get_ownership`, `apply_transition` |
| `admission_v1` | `evaluate_admission` |
| `decision_identity_v1` | `build_fingerprint`, `allocate_decision_id`, `find_open_duplicate` |
| `projection_v1` | `build_workspace_projection`, `get_workspace_projection` |
| `commands_v1` | `execute_command` |
| `handoff_contract_v1` | `evaluate_handoff_eligibility` |
| `live_update_v1` | `compare_envelope` |
| Routes | `GET /api/cart-workspace/v1/projection`, `POST /api/cart-workspace/v1/commands` |
| Render | `applyProjection(envelope)`, `dispatchCommand(...)` |

## 18.4 Feature flag ownership

`CARTFLOW_CART_WORKSPACE_V1` read in routes + dashboard shell wiring; services may run shadow under separate `CARTFLOW_CART_WORKSPACE_SHADOW_V1` if needed (default off).

## 18.5 Tests location

`tests/test_cart_workspace_ownership_v1.py`  
`tests/test_cart_workspace_admission_v1.py`  
`tests/test_cart_workspace_projection_v1.py`  
`tests/test_cart_workspace_commands_v1.py`  
`tests/test_cart_workspace_live_update_v1.py`  
`tests/test_cart_workspace_identity_v1.py`

---

# Part 19 — Deferred Product Hooks

| Hook | Product OQ | Engineering requirement |
|------|------------|-------------------------|
| T4 expiry/return/supersede | OQ-1 | Transition id reserved; `product_deferred=true`; no timers invented |
| T6/T7 manual execution scope | OQ-2 | Reserved; handoff default does not transfer Execution |
| T12 reopen evidence | OQ-4 | Reserved; archive browse never Admits |

When Product closes an OQ, Engineering adds compiled predicates only — **no** Architecture/Product rewrite required if hooks preserved.

These do **not** block implementing: Quiet projection, T1/T2 Admit, T3 Action, T5/T10 completion path, T8/T9 mode, Zones A–E, live update, migration shadow.

---

# Part 20 — Risk Register and Verdict

## 20.1 Engineering risk register

| ID | Risk | Mitigation |
|----|------|------------|
| **ER-1** | Duplicate Admit logic in `merchant_decision_layer_v1` vs P2 | Document sole Workspace Admit owner; other layers input-only |
| **ER-2** | Legacy RSC/`#carts` Status IA leaks into Workspace renderer | Separate render controller; flag isolation |
| **ER-3** | Projection cache diverges from Decision table | Version+fingerprint; rebuildable from open set |
| **ER-4** | Action lost on failure | Persist command audit; idempotent retry; explicit fail |
| **ER-5** | Hot-path history scan regresses | Query-bound tests; indexed open set |
| **ER-6** | Inventing OQ policy under schedule pressure | Deferred hooks + review gate |
| **ER-7** | Handoff claims false delivery | Eligibility uses readiness truth only |
| **ER-8** | main.py absorbs logic | Router wiring only; CI ownership tests |

## 20.2 Readiness checklist

| Criterion | Met? |
|-----------|------|
| One owner per rule | Yes — Part 1 |
| No duplicated business logic | Yes — plane + import bans |
| Complete contracts | Yes — Part 2 |
| Safe migration plan | Yes — Part 14 |
| Testable behavior | Yes — Part 15 |
| Bounded hot paths | Yes — Part 12 |
| No unresolved engineering invention | Yes — OQs isolated Part 19 |
| Deferred Product hooks explicit | Yes |

---

## Final Engineering Readiness Verdict

# Verdict A — Engineering Specification Ready

Engineering may proceed to implementation under this specification without making Product decisions, provided deferred OQ hooks remain non-invented and feature flag defaults off.

---

## Change log

| Version | Change |
|---------|--------|
| **V1** | Full engineering spec: modules, contracts, identity, ownership, admission, projection, grid/card, commands, handoff, live update, failure, performance, persistence, migration M0–M7, tests, observability, security, file map, deferred hooks, risks; **Verdict A**. |

---

**End of Cart Workspace Engineering Specification V1.**
