# CartFlow Runtime Governance Rules V1

**Status:** Permanent runtime rule catalog — no implementation  
**Date (UTC):** 2026-07-08  
**Authority:** Subordinate to [`lifecycle_governance_engine_v1.md`](lifecycle_governance_engine_v1.md)  
**Applies to:** All LGE-governed interactive UI components (Story Cards, Timeline, Conversation Panel, Widget, Knowledge Cards, Admin Panels, future dashboard components)

> Rules are **policy** for the Lifecycle Governor. Controllers and clients **must not** reinterpret or override them ad hoc.

---

## 0. Rule notation

| Field | Meaning |
|-------|---------|
| **Rule ID** | Stable identifier (`LGE-R-{CATEGORY}-{nnn}`) |
| **Severity** | P0 block release · P1 certification fail · P2 warn · P3 advisory |
| **Owner** | Governor enforces · Controller complies · Client requests only |

---

## 1. Transition rules (`LGE-R-TR-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-TR-001** | Every lifecycle transition must be approved by the Governor before Controller execution | P0 |
| **LGE-R-TR-002** | Illegal state machine edges must be **rejected**, never silently coerced | P0 |
| **LGE-R-TR-003** | `EXPANDING` and `COLLAPSING` are exclusive — no concurrent expand and collapse | P0 |
| **LGE-R-TR-004** | `UPDATING` must complete or fail before a conflicting transition is approved | P1 |
| **LGE-R-TR-005** | `sync()` may not change lifecycle state enum — presentation reconcile only | P1 |
| **LGE-R-TR-006** | `refresh()` must evaluate policy and dispatch at most one primary sub-operation per lifecycleId per transaction | P1 |
| **LGE-R-TR-007** | Destroy from **EXPANDED** requires prior collapse **or** explicit force policy with audit reason | P0 |
| **LGE-R-TR-008** | Create on existing live identity must be **rejected** unless policy defines replace-in-place | P0 |

---

## 2. Ownership rules (`LGE-R-OWN-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-OWN-001** | One `lifecycleId` → one Controller instance at a time | P0 |
| **LGE-R-OWN-002** | One component type → one Governor policy bundle | P0 |
| **LGE-R-OWN-003** | Only Controller + DOM Adapter may mutate governed DOM | P0 |
| **LGE-R-OWN-004** | Workspace, pollers, MI, MIL, MPL are **never** lifecycle owners | P0 |
| **LGE-R-OWN-005** | Browser native state (`details.open`, `:open` pseudo) is **not** authoritative — Controller state is | P0 |
| **LGE-R-OWN-006** | DOM Adapter must not persist lifecycle state outside Controller | P1 |
| **LGE-R-OWN-007** | Each governed component type registers exactly one Controller factory | P1 |

---

## 3. Concurrency rules (`LGE-R-CON-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-CON-001** | Transition Lock: one approved transition per `lifecycleId` at a time | P0 |
| **LGE-R-CON-002** | Refresh requests during Refresh Lock are coalesced, not parallelized | P1 |
| **LGE-R-CON-003** | Expand/collapse during Animation Lock are deferred, not interleaved | P1 |
| **LGE-R-CON-004** | Cross-component locks must not create circular wait — defined lock ordering required | P0 |
| **LGE-R-CON-005** | Watchdog timeout on stuck transition emits `transition_failed` and releases locks | P1 |

---

## 4. Polling rules (`LGE-R-POL-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-POL-001** | Pollers emit `refresh()` only — never render or DOM mutate | P0 |
| **LGE-R-POL-002** | Polling **must not** trigger full rebuild of **EXPANDED** components unless structure key changed | P0 |
| **LGE-R-POL-003** | Token refresh, pending cart watcher, visibility resume are equivalent to poll refresh — same rules | P1 |
| **LGE-R-POL-004** | Poll refresh while VISIBLE may rebuild only if structure key changed | P1 |
| **LGE-R-POL-005** | Poll storms must coalesce via Refresh Lock within policy window | P2 |

---

## 5. Refresh rules (`LGE-R-REF-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-REF-001** | `refresh()` is evaluation-only at client boundary — Governor dispatches create/update/sync/destroy/noop | P0 |
| **LGE-R-REF-002** | Refresh must preserve expand intent when structure unchanged | P0 |
| **LGE-R-REF-003** | Refresh must preserve selection when attachment key changes only | P1 |
| **LGE-R-REF-004** | Refresh noop when view model + keys unchanged | P2 |
| **LGE-R-REF-005** | Memory rerender (`rerenderFromMemory`) is a refresh source — not exempt from rules | P1 |

---

## 6. Animation rules (`LGE-R-ANI-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-ANI-001** | Animation must never transfer lifecycle ownership | P0 |
| **LGE-R-ANI-002** | Animation Lock covers EXPANDING and COLLAPSING states | P1 |
| **LGE-R-ANI-003** | CSS animation end is adapter signal — not browser authority for state | P1 |
| **LGE-R-ANI-004** | Multiple competing animations on same node require single animation owner in adapter | P2 |
| **LGE-R-ANI-005** | Animation duration exceeding lock timeout is certification failure | P2 |

---

## 7. Rebuild rules (`LGE-R-RBL-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-RBL-001** | Only **structure key** change may authorize full recreate | P0 |
| **LGE-R-RBL-002** | Attachment key change authorizes patch update, not full recreate, when expanded | P0 |
| **LGE-R-RBL-003** | Row count / queue membership alone must not change structure key | P0 |
| **LGE-R-RBL-004** | Full root `innerHTML` replace is rebuild — governed as destroy+create | P0 |
| **LGE-R-RBL-005** | Rebuild while expanded requires collapse-first or expanded-safe adapter transaction | P0 |

---

## 8. Visibility rules (`LGE-R-VIS-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-VIS-001** | CREATED → VISIBLE commit must complete before expand is allowed | P1 |
| **LGE-R-VIS-002** | DESTROYED components are not visible and not expandable | P0 |
| **LGE-R-VIS-003** | Hidden/offscreen components follow same lifecycle rules as visible | P1 |
| **LGE-R-VIS-004** | aria-live regions on governed roots must not bypass lifecycle transactions | P2 |

---

## 9. Selection rules (`LGE-R-SEL-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-SEL-001** | Selection state is attachment metadata — not lifecycle state | P1 |
| **LGE-R-SEL-002** | Selection must survive attachment-only refresh | P1 |
| **LGE-R-SEL-003** | Selection Lock prevents patch from clearing selected queue item | P1 |
| **LGE-R-SEL-004** | Changing selection must not destroy story card lifecycle | P1 |
| **LGE-R-SEL-005** | Conversation Panel selection is separate component lifecycle | P2 |

---

## 10. Interaction rules (`LGE-R-INT-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-INT-001** | User click → Interaction Client → `expand()` / `collapse()` request only | P0 |
| **LGE-R-INT-002** | Native toggle handlers must not set `details.open` directly — adapter applies after approval | P0 |
| **LGE-R-INT-003** | mousedown intent capture is Controller-internal, not client-writable | P1 |
| **LGE-R-INT-004** | Queue item click inside expanded body requests selection refresh — not card rebuild | P1 |
| **LGE-R-INT-005** | Keyboard accessibility follows same request path as pointer | P2 |

---

## 11. Recovery rules (`LGE-R-REC-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-REC-001** | Failed transition must roll back to last committed state or proceed to DESTROYED — no orphan DOM | P0 |
| **LGE-R-REC-002** | Controller violation triggers certification event in dev/staging | P1 |
| **LGE-R-REC-003** | Lost identity refresh must reject with `LGE-ID-002`, not recreate silently | P1 |
| **LGE-R-REC-004** | Partial adapter failure releases all locks for lifecycleId | P0 |
| **LGE-R-REC-005** | Page navigation destroy-all is explicit bulk `destroy` policy | P1 |

---

## 12. Identity rules (`LGE-R-ID-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-ID-001** | `lifecycleId` is stable for component instance lifetime | P0 |
| **LGE-R-ID-002** | Identity scheme is deterministic from view model primary key | P1 |
| **LGE-R-ID-003** | Duplicate identity registration is rejected | P0 |
| **LGE-R-ID-004** | Destroy retires identity until explicit recreate | P1 |
| **LGE-R-ID-005** | Registry is authoritative map lifecycleId → controller | P0 |

---

## 13. State integrity rules (`LGE-R-ST-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-ST-001** | Controller state enum is sole authority for lifecycle phase | P0 |
| **LGE-R-ST-002** | DOM must be reconciled to Controller state on every commit | P0 |
| **LGE-R-ST-003** | State drift detection (`LGE-SYNC-001`) fails certification | P0 |
| **LGE-R-ST-004** | External module-scoped maps (e.g. openGroupState) migrate into Controller | P1 |
| **LGE-R-ST-005** | Post-commit hooks run only after DOM reconcile succeeds | P1 |

---

## 14. Synchronization rules (`LGE-R-SYN-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-SYN-001** | `sync()` removes duplicate presentation layers while EXPANDED | P1 |
| **LGE-R-SYN-002** | sync after poll skip is idempotent | P2 |
| **LGE-R-SYN-003** | sync must not restore collapsed preview while EXPANDED | P0 |
| **LGE-R-SYN-004** | sync must restore collapsed preview while VISIBLE if cached | P1 |
| **LGE-R-SYN-005** | Double sync in same frame is allowed; triple policy-defined max | P3 |

---

## 15. Isolation rules (`LGE-R-ISO-*`)

| ID | Rule | Severity |
|----|------|----------|
| **LGE-R-ISO-001** | MPL host lifecycle is isolated from Story Card lifecycle | P0 |
| **LGE-R-ISO-002** | Conversation Panel lifecycle is isolated from Story Card lifecycle | P0 |
| **LGE-R-ISO-003** | MI view-model builders have zero DOM imports | P0 |
| **LGE-R-ISO-004** | Admin panel lifecycle does not mutate merchant story roots | P1 |
| **LGE-R-ISO-005** | Widget lifecycle is isolated from dashboard merchant lifecycle | P1 |

---

## 16. Story Card policy bundle (first consumer — reference)

These instantiate generic rules for `componentType: story-card`:

| Rule | Story Card instantiation |
|------|-------------------------|
| LGE-R-RBL-001 | Structure key = story sig (ids, affected_carts, priority) — **not** `rows.length` |
| LGE-R-RBL-002 | Attachment key = queue row membership + selection |
| LGE-R-POL-002 | Poll skip path = sync-only when structure unchanged |
| LGE-R-REF-002 | `openGroupState` becomes Controller expand intent store |
| LGE-R-ISO-001 | `#ma-carts-product-language-v1` never writes `#ma-carts-groups-v2` |
| LGE-R-ISO-002 | `#ma-carts-panel-v2` is separate `conversation-panel` type |

---

## 17. Enforcement ladder (future)

| Level | Mechanism |
|-------|-----------|
| L0 | Documentation + review |
| L1 | Dev-only assertion hooks |
| L2 | CI grep + certification tests |
| L3 | Runtime violation telemetry |
| L4 | Production block on P0 violation rate threshold |

**V1 deliverable:** L0 only.

---

## 18. Amendment

New rules require:

1. Rule ID assignment in this catalog
2. Governor policy bundle update
3. Certification checklist update
4. Entry in `docs/institutional_memory/decision_registry.md` when ratified

No rule may weaken P0 ownership or transition rules without constitution-level review.
