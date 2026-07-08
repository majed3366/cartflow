# CartFlow Lifecycle Governance Engine (LGE) V1

**Status:** Architectural foundation — no implementation, no runtime change, no product change  
**Date (UTC):** 2026-07-08  
**Domain:** Interactive UI lifecycle governance (browser runtime)  
**Precedence:** Subordinate to [`engineering_constitution_v1.md`](engineering_constitution_v1.md) (One Source of Truth Per Question); peer to Dashboard Read Model Governance and Proof of Value Governance for **presentation-runtime** authority.

> This document defines **WHO may approve lifecycle transitions** and **WHO may execute them** for every interactive UI component in CartFlow. Story Cards are the **first planned consumer**, not the scope of this engine.

**Related documents:**

| Document | Role |
|----------|------|
| [`runtime_governance_rules_v1.md`](runtime_governance_rules_v1.md) | Permanent runtime rule catalog |
| [`runtime_lifecycle_certification_v1.md`](runtime_lifecycle_certification_v1.md) | Certification checklist for governed components |
| Story Card Ownership Audit (conversation artifact) | Baseline violation inventory |
| [`merchant_experience_foundation_v1.md`](merchant_experience_foundation_v1.md) | Experience consumes; never owns lifecycle |

---

## 0. Mission

CartFlow interactive surfaces today allow **distributed lifecycle ownership**: workspace orchestrators, poll ingress, string renderers, browser primitives, and presentation sync mutators can all create, replace, or destroy the same DOM. That violates **One Source of Truth Per Question**.

**Lifecycle Governance Engine (LGE) V1** establishes a **permanent runtime governance architecture** so that:

- Every interactive component has **One Lifecycle · One Governor · One Controller**
- **Policy never executes**
- **Controller never decides**
- **DOM never owns state**
- **Browser is never authority**
- **Only the Governor may approve lifecycle transitions**

LGE is **reusable** for Story Cards, Timeline, Conversation Panel, Widget, Knowledge Cards, Admin Panels, and future dashboard components.

---

## 1. Vision — target stack

### Today (violations)

```
Request → Controller-ish code → DOM (direct innerHTML, details.open, preview remove)
                ↑
         Multiple co-owners
```

### Target architecture

```
Request
   ↓
Lifecycle Registry        (lookup only — no execution)
   ↓
Lifecycle Governor        (policy — approve / deny / defer)
   ↓
Lifecycle Controller      (execution — state + adapter invocation)
   ↓
DOM Adapter               (HTML, classes, listeners, animations)
   ↓
Browser                   (events → Request, never authority)
```

---

## 2. Design principle — Policy separated from Execution

| Layer | Decides | Executes |
|-------|---------|----------|
| **Governor** | Yes — transitions, locks, conflicts, defer/reject | Never |
| **Controller** | Never | Yes — approved ops only |
| **DOM Adapter** | Never | Yes — DOM mutations only |
| **Registry** | Never | Never — registration + routing |
| **Clients** (workspace, pollers, browser) | Never | Never — submit requests only |

---

## 3. Core components

### 3.1 Lifecycle Registry

**Module (future):** `ui_lifecycle_registry_v1.js`

**Responsibilities:**

- Register component types (`story-card`, `timeline-row`, `conversation-panel`, `widget-shell`, `knowledge-card`, …)
- Map `componentType` → `GovernorFactory` + `ControllerFactory`
- Resolve `lifecycleId` → active controller instance
- Issue new `lifecycleId` on create (deterministic or UUID — policy per component)
- Expose read-only introspection for certification and devtools

**Forbidden:**

- DOM access
- Transition approval
- State mutation
- Rendering

**Public surface (conceptual):**

```typescript
register(componentType, { governorFactory, controllerFactory, policyBundle })
lookup(componentType): RegisteredComponent
resolve(lifecycleId): { componentType, controllerRef } | null
request(componentType, intent: LifecycleIntent): Promise<GovernanceResult>
```

---

### 3.2 Lifecycle Governor

**Module (future):** `ui_lifecycle_governor_v1.js` (+ per-component policy bundles)

**Responsibilities:**

- Validate requested transition against state machine
- Detect conflicts (expand during rebuild, destroy while expanded, duplicate identity)
- Manage lifecycle locks (see §6)
- Apply transition policy (rebuild, update, defer, refresh coalescing)
- Enforce permissions (who may request which op)
- Emit governance events
- Return **ApprovalToken** or **Rejection** or **Deferral**

**Forbidden:**

- DOM mutation
- HTML composition
- Listener binding
- Calling MI/MIL/MPL renderers directly

**Inputs:**

- Current `LifecycleState`
- Active locks
- `LifecycleIntent` (op, source, reason, viewModelRef, context)
- Component policy bundle

**Outputs:**

- `ApprovedTransition { token, from, to, op, constraints }`
- `DeniedTransition { reason, violationCode }`
- `DeferredTransition { retryAfterMs, reason }`

---

### 3.3 Lifecycle Controller

**Module (future):** `ui_lifecycle_controller_v1.js` (base) + `{component}_lifecycle_controller_v1.js`

**Responsibilities:**

- Hold **authoritative lifecycle state** for one `lifecycleId`
- Accept only Governor-approved operations (requires `ApprovalToken`)
- Invoke DOM Adapter for approved CREATE / UPDATE / EXPAND / COLLAPSE / DESTROY / SYNC
- Report completion or failure to Registry/Governor
- Maintain binding generation counter (invalidate stale listeners after destroy)

**Forbidden:**

- Policy decisions (rebuild vs patch, defer vs reject)
- Bypassing Governor
- Direct exposure of DOM Adapter to clients

**State owned:**

- `LifecycleState` enum
- Expand/collapse intent (not `details.open` as authority)
- Cached view model snapshot
- Adapter binding generation
- Optional presentation cache (`_summaryPreviewHtml` equivalent — internal)

---

### 3.4 DOM Adapter

**Module (future):** `{component}_dom_adapter_v1.js`

**Responsibilities:**

- Mount/unmount HTML
- Apply CSS classes
- Attach/detach event listeners (translate browser events → Lifecycle Requests)
- Run animations (never change ownership)
- Read DOM for adapter-internal reconciliation only

**Forbidden:**

- Lifecycle state decisions
- Calling pollers or workspace
- Composing business meaning (MI/MIL/MPL)

---

## 4. Lifecycle clients (request-only)

| Client | Today (violations) | LGE role |
|--------|------------------|----------|
| `renderMiCartsV1Workspace` | Orchestrator + rebuild | **Lifecycle Client** → `refresh()` request |
| Poll / refresh watchers | Trigger full render | **Refresh Client** → `refresh(source: poll)` |
| Browser / user | Sets `details.open` | **Interaction Client** → `expand()` / `collapse()` |
| MI module | `innerHTML` render | **View-model producer** only |
| MIL / MPL | Adjacent hosts | **Presentation** — separate lifecycle or read-only |
| Conversation Panel | Parallel innerHTML | **Separate governed component** |

---

## 5. Formal state machine

### 5.1 States

| State | Meaning |
|-------|---------|
| **CREATED** | Identity allocated; DOM mount in progress or not yet visible |
| **VISIBLE** | Mounted, collapsed presentation |
| **EXPANDING** | Expand approved; animation/adapter transition in progress |
| **EXPANDED** | Open presentation stable |
| **UPDATING** | Content patch in progress (may be expanded-safe or full rebuild scheduled) |
| **COLLAPSING** | Collapse approved; animation/adapter transition in progress |
| **DESTROYED** | Unmounted; identity may be retired or recycled per policy |

### 5.2 Primary flow

```
CREATED → VISIBLE → EXPANDING → EXPANDED → UPDATING → EXPANDED
                ↑                                    │
                └──────── COLLAPSING ←───────────────┘
                ↑
              VISIBLE → DESTROYED
```

Any state → **DESTROYED** (if Governor approves; see rules for EXPANDED + destroy).

### 5.3 Transition tables

#### Allowed (Governor may approve)

| From | Op / Event | To | Notes |
|------|------------|-----|-------|
| — | `create` | CREATED → VISIBLE | Initial mount |
| VISIBLE | `expand` | EXPANDING → EXPANDED | User or programmatic |
| EXPANDED | `collapse` | COLLAPSING → VISIBLE | |
| VISIBLE | `update` | UPDATING → VISIBLE | Structure unchanged |
| EXPANDED | `update` | UPDATING → EXPANDED | Attachment-only patch |
| VISIBLE / EXPANDED | `sync` | same | Presentation reconcile |
| * | `destroy` | DESTROYED | Subject to EXPANDED destroy rule |
| * | `refresh` | (dispatches) | Evaluates → create/update/sync/destroy/noop |

#### Forbidden (Governor must reject)

| Attempt | Violation code |
|---------|----------------|
| `expand` from DESTROYED | `LGE-TR-001` |
| `update` during EXPANDING/COLLAPSING without defer | `LGE-TR-002` |
| Direct DOM mutation outside Controller | `LGE-OWN-001` |
| `destroy` on EXPANDED without force policy | `LGE-TR-003` |
| Duplicate `lifecycleId` create | `LGE-ID-001` |
| Controller op without ApprovalToken | `LGE-GOV-001` |
| Second Governor for same component | `LGE-OWN-002` |

#### Deferred (Governor queues / retries)

| Condition | Defer reason |
|-----------|--------------|
| Animation lock held | `defer:animation_in_progress` |
| Refresh lock held | `defer:refresh_coalescing` |
| UPDATING in progress | `defer:update_in_flight` |
| Expand requested during scheduled rebuild | `defer:rebuild_pending` |

#### Queued

- Multiple `refresh()` while Refresh Lock held → coalesce to single refresh evaluation
- Rapid expand/collapse → Transition Lock serializes

#### Rejected

- Illegal state transition
- Policy violation (e.g. poll-triggered full rebuild while EXPANDED)
- Missing view model for update
- Identity conflict

---

## 6. Lock system

| Lock | Purpose | Created by | Released by | Timeout |
|------|---------|------------|-------------|---------|
| **ExpandLock** | Serialize expand/collapse | Governor on EXPANDING/COLLAPSING | Controller on commit | 500ms default; cert fail if exceeded |
| **AnimationLock** | Block conflicting updates during CSS animation | Governor entering EXPANDING/COLLAPSING | Adapter animation end event | animation duration + 50ms buffer |
| **RefreshLock** | Coalesce poll refresh storms | Governor on refresh eval | End of refresh transaction | 100ms coalesce window |
| **SelectionLock** | Preserve queue selection across patch | Governor on attachment update | Controller after selection restore | transaction-scoped |
| **TransitionLock** | One state transition at a time per lifecycleId | Governor | Transition completed event | 2s watchdog |
| **IdentityLock** | Prevent duplicate mount for same id | Governor on create | destroy commit | until DESTROYED |

**Deadlock prevention:**

- Lock ordering: `IdentityLock` → `TransitionLock` → `AnimationLock` → `RefreshLock`
- Governor never waits on Controller; Controller never waits on Governor across different lifecycleIds
- Watchdog releases with `transition_failed` event + certification violation in dev

---

## 7. Public contract (platform-wide)

All lifecycle changes **must** be expressed as requests to the Registry:

| Operation | Requester | Governor decides | Controller executes |
|-----------|-----------|------------------|---------------------|
| `create(viewModel, context)` | Workspace | mount policy | DOM Adapter mount |
| `update(viewModel, context)` | Workspace / refresh | patch vs rebuild | Adapter patch or remount |
| `expand(lifecycleId, context)` | Interaction client | allow/defer | Adapter expand presentation |
| `collapse(lifecycleId, context)` | Interaction client | allow/defer | Adapter collapse presentation |
| `destroy(lifecycleId, reason)` | Workspace / navigation | allow/deny if expanded | Adapter unmount |
| `sync(lifecycleId, context)` | Refresh / post-commit | allow | Adapter reconcile |
| `refresh(dataRef, context)` | Pollers | dispatch sub-op | none directly |

**Forbidden globally (outside Controller+Adapter after approval):**

- `element.innerHTML =` on governed roots
- `details.open =` on governed details
- Preview remove/restore helpers callable from clients
- Card destroy via workspace string render
- Listener binding from workspace or pollers

---

## 8. Runtime events

| Event | Emitter | Payload |
|-------|---------|---------|
| `transition_requested` | Registry | intent, lifecycleId, source |
| `transition_allowed` | Governor | token, from, to, op |
| `transition_denied` | Governor | reason, violationCode |
| `transition_deferred` | Governor | retryAfterMs, reason |
| `transition_completed` | Controller | lifecycleId, state, action |
| `transition_failed` | Controller | lifecycleId, error, rollbackState |
| `controller_violation` | Certification harness | direct DOM mutation detected |
| `policy_violation` | Governor | ruleId, context |

---

## 9. Runtime violations

| Code | Name | Description |
|------|------|-------------|
| `LGE-OWN-001` | Direct DOM mutation | Client mutated governed DOM without approval |
| `LGE-OWN-002` | Double owner | Two controllers for same lifecycleId |
| `LGE-GOV-001` | Controller bypass | Controller executed without ApprovalToken |
| `LGE-GOV-002` | Governor bypass | Client skipped Registry/Governor |
| `LGE-TR-001` | Unauthorized transition | Illegal state machine edge |
| `LGE-TR-002` | Transition during animation | Update/destroy during EXPANDING/COLLAPSING |
| `LGE-TR-003` | Destroy while expanded | Destroy without collapse or force policy |
| `LGE-REF-001` | Illegal rebuild | Full rebuild while EXPANDED without structure change exception |
| `LGE-ID-001` | Duplicate lifecycle | create when identity already live |
| `LGE-ID-002` | Lost identity | refresh references unknown lifecycleId |
| `LGE-SYNC-001` | State drift | DOM open state ≠ Controller state |

---

## 10. Component registration model

Each component registers:

```typescript
{
  componentType: 'story-card',
  policyBundle: StoryCardPolicyV1,      // Governor rules
  controllerFactory: StoryCardControllerV1,
  domAdapterFactory: StoryCardDomAdapterV1,
  identityScheme: (vm) => `story:${vm.storyId}`,
  structureKey: (vm) => ...,           // rebuild boundary
  attachmentKey: (vm) => ...,           // patch boundary
}
```

**First consumer:** `story-card` — reference policy bundle documents Story Card rules from Ownership Audit.

**Future consumers:** same envelope; different policy bundles and adapters.

---

## 11. Relationship to existing layers

| Layer | LGE relationship |
|-------|------------------|
| **MI** | Produces view models; never touches lifecycle |
| **MIL** | Meaning only; no lifecycle |
| **MPL** | Presentation on separate hosts; not story-card lifecycle owner |
| **Merchant Experience** | Surfaces are lifecycle clients or separate governed components |
| **Snapshot / API** | Data ingress only; triggers `refresh()` |

---

## 12. Migration plan (documentation only — no code in V1)

| Phase | Scope | Outcome |
|-------|-------|---------|
| **0** | LGE architecture docs + certification | This deliverable |
| **1** | Story Card — Registry + Governor + Controller (shadow) | Reference implementation |
| **2** | Timeline | Reuse LGE core |
| **3** | Conversation Panel | Separate component type |
| **4** | Knowledge Cards | KL card lifecycle |
| **5** | Widget | Storefront shell |
| **6** | Admin + dashboard components | Platform-wide enforcement |

See [`runtime_lifecycle_certification_v1.md`](runtime_lifecycle_certification_v1.md) for pass criteria per phase.

---

## 13. Success criteria

LGE V1 architecture is complete when:

1. Governor / Controller / Adapter responsibilities are unambiguous
2. State machine and transition tables are formal
3. Lock system and violation catalog exist
4. Runtime rules and certification are documented
5. Story Cards are documented as **first consumer**, not special case
6. Platform no longer relies on developer discipline alone

**Not in scope for this document:** implementation, code migration, product changes.

---

## 14. Permanent architectural rule (proposed)

> **No interactive UI component may mutate its own lifecycle DOM outside an LGE-approved Controller execution.**

Ratification target: institutional memory + engineering constitution amendment when Phase 1 ships.
