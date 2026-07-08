# CartFlow Runtime Lifecycle Certification V1

**Status:** Certification framework — no implementation  
**Date (UTC):** 2026-07-08  
**Authority:** [`lifecycle_governance_engine_v1.md`](lifecycle_governance_engine_v1.md) · [`runtime_governance_rules_v1.md`](runtime_governance_rules_v1.md)

> Certification proves a component **implements LGE architecture**, not that product visuals are correct. Story Cards are the **reference certification target** for Phase 1.

---

## 0. Purpose

Runtime Lifecycle Certification answers:

- Is there exactly **one Governor** and **one Controller** per governed component?
- Are lifecycle transitions **approved before execution**?
- Is governed DOM **free of client-side direct mutation**?
- Do pollers and workspace act as **request-only clients**?

Certification is required before a component is considered **LGE-compliant**.

---

## 1. Certification levels

| Level | Name | Meaning |
|-------|------|---------|
| **L0** | Un governed | Legacy distributed ownership (current baseline for Story Cards) |
| **L1** | Documented | Policy bundle + ownership map approved |
| **L2** | Shadow | LGE runs parallel to legacy; diffs logged |
| **L3** | Enforced | Production path uses LGE only; CI gates active |
| **L4** | Certified | L3 + production telemetry clean for 7 days |

**LGE V1 deliverable:** L1 for platform architecture; Story Cards remain L0 until Phase 1 implementation.

---

## 2. Universal certification checklist

Every governed component must pass **all** items before L3.

### 2.1 One owner

| # | Criterion | Pass condition |
|---|-----------|----------------|
| C-OWN-01 | Single Controller per `lifecycleId` | Registry resolves one controller |
| C-OWN-02 | Single Governor policy bundle per component type | No duplicate policy registration |
| C-OWN-03 | No client direct DOM mutation | Static analysis + runtime harness zero P0 violations |
| C-OWN-04 | Controller state is authority | No `details.open` / CSS `:open` as source of truth |

### 2.2 One governor

| # | Criterion | Pass condition |
|---|-----------|----------------|
| C-GOV-01 | All ops go through Registry request | No exported bypass API |
| C-GOV-02 | Controller rejects ops without ApprovalToken | Unit tests |
| C-GOV-03 | Illegal transitions rejected | State machine test matrix 100% |
| C-GOV-04 | Governor never touches DOM | Code ownership boundary |

### 2.3 One controller

| # | Criterion | Pass condition |
|---|-----------|----------------|
| C-CTL-01 | Controller never decides rebuild vs patch | Policy tests delegate to Governor |
| C-CTL-02 | DOM Adapter is only DOM mutator | Adapter isolation audit |
| C-CTL-03 | Destroy releases listeners | No leak after 100 create/destroy cycles |
| C-CTL-04 | Commit is atomic | No partial visible state after failed update |

### 2.4 No direct DOM mutation

| # | Criterion | Pass condition |
|---|-----------|----------------|
| C-DOM-01 | No `innerHTML` on governed root outside Adapter | CI grep |
| C-DOM-02 | No preview remove/restore outside Adapter | CI grep |
| C-DOM-03 | No direct `details.open` outside Adapter | CI grep |
| C-DOM-04 | Dev harness: MutationObserver zero unapproved mutations | Integration test |

### 2.5 No duplicate lifecycle

| # | Criterion | Pass condition |
|---|-----------|----------------|
| C-ID-01 | Duplicate create rejected | Test `LGE-ID-001` |
| C-ID-02 | Identity stable across attachment refresh | Test |
| C-ID-03 | Destroy retires identity | Test |

### 2.6 No illegal transitions

| # | Criterion | Pass condition |
|---|-----------|----------------|
| C-TR-01 | Full transition table tested | Allowed/forbidden/deferred |
| C-TR-02 | EXPANDED destroy rule enforced | Test `LGE-R-TR-007` |
| C-TR-03 | Animation lock defers conflicting ops | Test |

### 2.7 No ownership conflicts

| # | Criterion | Pass condition |
|---|-----------|----------------|
| C-CON-01 | Poll refresh does not rebuild expanded without structure change | Test |
| C-CON-02 | Workspace is client only | No DOM in lazy workspace functions |
| C-CON-03 | MI/MIL/MPL isolated | Import boundary audit |

### 2.8 No controller bypass

| # | Criterion | Pass condition |
|---|-----------|----------------|
| C-BYP-01 | Public MI exports do not include DOM binders | API audit |
| C-BYP-02 | Legacy sync helpers not callable from lazy.js | Deprecation + grep |
| C-BYP-03 | Browser events route to Registry | Interaction adapter test |

---

## 3. Story Card reference certification (Phase 1 target)

When Story Card LGE ships, additionally verify:

| # | Scenario | Expected |
|---|----------|----------|
| SC-01 | Expand story | Governor: VISIBLE→EXPANDED; summary preview removed once |
| SC-02 | Collapse story | EXPANDED→VISIBLE; preview restored once |
| SC-03 | Poll refresh, structure unchanged, expanded | refresh→sync or noop; **no innerHTML** on `#ma-carts-groups-v2` |
| SC-04 | Poll refresh, structure changed, expanded | defer collapse OR expanded-safe transaction per policy |
| SC-05 | Row count change only | attachment update; **no** full rebuild |
| SC-06 | Select queue item while expanded | selection update; panel separate lifecycle |
| SC-07 | Rapid double click expand | Transition Lock serializes |
| SC-08 | Animation in progress + update | deferred |
| SC-09 | Page leave | bulk destroy all story lifecycleIds |

---

## 4. Component certification matrix (future phases)

| Component | Type key | Phase | Depends on |
|-----------|----------|-------|------------|
| Story Card | `story-card` | 1 | LGE core |
| Timeline row | `timeline-row` | 2 | LGE core |
| Conversation Panel | `conversation-panel` | 3 | LGE core |
| Knowledge Card | `knowledge-card` | 4 | LGE core |
| Widget shell | `widget-shell` | 5 | LGE core |
| Admin panel block | `admin-panel-block` | 6 | LGE core |

Each row reuses **universal checklist** + component-specific scenario pack.

---

## 5. Certification artifacts

| Artifact | Location (future) |
|----------|-------------------|
| Policy bundle | `story_card_policy_v1.js` |
| Scenario tests | `tests/test_lge_story_card_v1.py` / JS harness |
| CI gate | `.github/workflows/lifecycle_certification_gate.yml` |
| Violation report | `lifecycle:violation` event stream |
| Certification record | `docs/institutional_memory/decision_registry.md` |

**V1:** documentation only — no artifacts implemented.

---

## 6. Baseline audit — Story Cards today (L0)

| Criterion | Current status |
|-----------|----------------|
| C-OWN-01 Single Controller | **FAIL** — renderStories + sync + browser |
| C-GOV-01 Governor | **FAIL** — not implemented |
| C-DOM-01 No direct innerHTML | **FAIL** — `renderStories`, pending render |
| C-CON-01 Poll rebuild while expanded | **FAIL** — wsKey includes rows.length |
| C-ISO-01 MPL isolated | **PASS** — separate host |
| C-ISO-02 Panel isolated | **PARTIAL** — separate DOM but parallel narrative |

This baseline is the **certification delta** for Phase 1.

---

## 7. Sign-off criteria (L3 Certified)

A component is **L3 Certified** when:

1. Universal checklist: 100% pass
2. Component scenario pack: 100% pass
3. CI certification gate: green on main
4. No P0 violations in 7-day staging soak
5. Ownership audit reopened — all FAIL items resolved

---

## 8. Non-goals

- Visual regression testing (PDS / MPL)
- Business truth correctness (MI / LT-C1)
- Performance benchmarks (separate governance)
- Product copy certification

---

## 9. Relationship to Engineering Constitution

Certification implements constitution rule:

> **One Source of Truth Per Question**

For interactive UI lifecycle, the question *"What is the expanded/collapsed/destroyed state of this component?"* has **one answer: the LGE Controller state after Governor approval.**

Presentation layers (MPL), meaning layers (MIL), and truth layers (MI) remain separate certified domains.
