# Home Cognitive Router V1

**Document type:** Foundational Product Contract — Cognitive Sequencing Engine  
**Status:** **Proposed** — pre-production hardening (session stability + truth ownership)  
**Date (UTC):** 2026-07-18  
**Companion:** [`HOME_ADAPTIVE_COGNITIVE_FLOW_V2.md`](HOME_ADAPTIVE_COGNITIVE_FLOW_V2.md)  
**Implementation (validation lab only):** `services/home_cognitive_router_v1.py` · `/dev/adaptive-cognition-lab`  

**Role:** Governed selector of merchant cognition path after Arrival.  

**Out of scope:** Home redesign · Wireframe · UI chrome · inventing knowledge · changing Inventory/Constitution/Surface Contract · modifying Wireflow node meanings  

---

## 1. Mission

The Cognitive Router evaluates available **governed** knowledge and determines the most natural cognition sequence.

It does **not** execute workflows.  
It does **not** invent information.  
It only answers: *Which adaptive path should navigate this merchant now?*

---

## 2. Truth Ownership (Required Principle)

> **The Adaptive Cognitive Engine never creates, modifies, filters or interprets business truth.**  
> **It consumes governed truth and determines only the cognition sequence presented to the merchant.**

| Domain | Owner | Adaptive Cognition |
|--------|-------|--------------------|
| Business truth | Knowledge Platform / governed engines | **Consumes only** |
| Knowledge creation / modification | Knowledge owners | **Never** |
| Filtering what is true | Admission / Inventory / Platform | **Never** (may skip *presentation* of a hollow node, not alter truth) |
| Business interpretation | Business Reasoning (when accepted) | **Never** |
| Decision ownership | Merchant + Decision Workspace | **Never** |
| **Sequencing** | — | **Owns** |
| **Timing** | — | **Owns** |
| **Routing destination selection** | — | **Owns** (does not execute) |
| **Optional node skipping** | — | **Owns** (presentation order only) |
| **Session path lock** | — | **Owns** |

Skipping a hollow Understanding chapter is **not** filtering business truth; it is refusing to present an empty cognition stage.

---

## 3. Router Ownership Boundary

| Router may | Router must not |
|------------|-----------------|
| Select Path A–F | Create findings, alerts, or health states |
| Order / skip / defer nodes | Change confidence, conclusions, or VIP status |
| Choose Communication / Carts / DW / Settings as destination | Execute messaging, cart work, settings changes |
| Lock a cognition session | Continuously reshuffle while merchant reads |
| Re-evaluate on governed triggers only | Periodic background rerouting |

Business Truth ownership remains unchanged.  
Knowledge ownership remains unchanged.  
Decision ownership remains unchanged.

---

## 4. Session Lifecycle

```text
SESSION_START (governed)
  → evaluate route from governed truth snapshot
  → LOCK selected_path as active cognition session
  → merchant reads (view ticks) — path STABLE
  → optional governed RE-EVALUATION trigger
       → unlock → re-evaluate → LOCK new path
  → session ends on leave / new full entry
```

### Path locking

Once a path is selected (Healthy, VIP, Operational, Attention, Pending, Insufficient, etc.):

- That path is the **active cognition session**.
- The path **remains stable** unless a governed trigger occurs.
- The merchant must feel: *“I finished one conversation”* before another begins.

### No live reshuffling

Forbidden while reading:

- Periodic background rerouting  
- UI jumping of cognitive direction  
- Live cognitive reshuffling on scroll/hover/poll  

---

## 5. Governed Re-evaluation Triggers

Re-evaluation is **allowed only** after:

| Trigger ID | Meaning |
|------------|---------|
| `full_page_refresh` | Full page refresh |
| `return_from_surface` | Merchant returns from another CartFlow surface |
| `manual_refresh` | Manual refresh initiated by merchant |
| `significant_business_state_transition` | Significant governed business-state transition |
| `session_start` | Initial session creation only (not a mid-session re-eval) |

### Significant transition examples (governed)

- VIP resolved  
- Critical operational failure appears or clears  
- Business health changes enough to change cognition priority  
- Knowledge readiness materially changes  

### Explicitly forbidden triggers

| Trigger | Status |
|---------|--------|
| `periodic_poll` | **Rejected** |
| `background_timer` | **Rejected** |
| `ui_hover` / `scroll` | **Rejected** |
| `live_reshuffle` | **Rejected** |

---

## 6. Routing Stability Contract

| Guarantee | Behavior |
|-----------|----------|
| One path per session segment | Single `selected_path` while locked |
| View without trigger | `view_tick` increments; **no** re-evaluation |
| Trigger without material change | Re-eval may keep same path (still a governed re-lock) |
| Trigger with material change | Path may change; history records previous → new |

---

## 7. Router Governance Contract (inputs / outputs)

### 7.1 Inputs (only)

| Input | Source |
|-------|--------|
| Executive Summary | Inventory Cat 1 |
| Top Merchant Attention | Inventory Cat 2 |
| Business Understanding (availability, acceptance, freshness, sufficiency) | Inventory Cat 3 + dependency |
| VIP Alert | Inventory Cat 4 |
| Merchant Alert | Inventory Cat 5 |
| Store Change Summary (eligibility) | Inventory Cat 6 |
| Operational Health (merchant-impacting) | Inventory Cat 7 |
| Business Direction (availability / approval) | IA Layer 5 gated trend summaries — not a new category |
| Knowledge freshness | Surface Contract Freshness |
| Data sufficiency | Platform governed signals |
| Dependency readiness | `BUSINESS_REASONING_PRODUCT_ACCEPTANCE`, `GOVERNED_TREND_SUMMARY_PRODUCT_APPROVAL` |
| Arrival outcome A–F | HOME-WF-00 |
| Return context (if re-entry) | Context Handoff |
| Active session lock (if any) | Session lifecycle |

**Prohibited inputs:** Raw events, diagnostics, Decision Workspace / Carts / Communication / Settings as data providers, any new Inventory category.

### 7.2 Outputs

| Output | Meaning |
|--------|---------|
| `selected_path` | A \| B \| C \| D \| E \| F |
| `path_label` | Healthy / Attention / VIP / Operational / Insufficient / Pending |
| `active_nodes` | Ordered list for this segment |
| `skipped_nodes` | Nodes omitted this segment |
| `deferred_nodes` | Nodes postponed until after return |
| `interim_closure` | A \| B \| C |
| `route_destination` | None \| Decision Workspace \| Carts \| Communication \| Settings |
| `rationale_codes` | Deterministic reason codes |
| `ownership` | Explicit router vs truth ownership declaration |
| `session_id` / lock metadata | Session stability |

### 7.3 Deterministic behavior

Same governed input snapshot → same outputs.  
No randomness. No personalization models. No hidden heuristics.

### 7.4 Traceability

```text
inputs → precedence gate → path → lock → (view ticks stable)
       → governed trigger? → re-evaluate → lock
```

| Code | Meaning |
|------|---------|
| `R-SAFE-OPS` | Immediate Safety → Path D |
| `R-VIP` | VIP primary → Path C |
| `R-ACTION` | Urgent non-VIP attention → Path B |
| `R-INSUFFICIENT` | Insufficient / new store → Path E |
| `R-PENDING` | Understanding pending → Path F |
| `R-HEALTHY` | Default Path A |
| `R-SKIP-HOLLOW-BU` | Understanding skipped (empty/gated) |
| `R-SKIP-HOLLOW-DIR` | Direction skipped (empty/gated) |
| `R-DEFER-POST-RETURN` | Node deferred until return |
| `R-INLINE-TRUST` | Confidence before route because ops blocks act |
| `R-RETURN-CONTINUE` | Post-return continuation segment |

---

## 8. Failure Behavior

| Failure | Router behavior |
|---------|-----------------|
| One input owner missing | Evaluate remaining inputs; never blank path |
| Arrival unresolved | Prefer Path F or E over Path A; never invent Stable |
| Conflicting VIP vs Attention scores | Prefer VIP (Path C) when equal; else follow platform primary |
| Destination unavailable | Keep path; set route with “destination unavailable” awareness — do not execute locally |
| Stale snapshot | May select path using last-good with freshness caveat; must not claim current if unverifiable |
| Ungoverned re-eval trigger | **Reject**; keep existing lock |
| Session not found on view/reeval | Error; do not invent a path silently mid-read |

---

## 9. Recovery Behavior

| Situation | Recovery |
|-----------|----------|
| After rejected ungoverned trigger | Continue locked session unchanged |
| After failed input owner | Degraded path via fallback ladder; session still locks |
| After return with resolved VIP | Re-eval on `return_from_surface` or significant transition → typically Path A |
| After critical ops appears mid-session | Only on governed trigger (refresh / return / significant transition) — **not** via background poll |
| Corrupt / missing session | New `session_start` on next full entry |

### Fallback ladder

```text
If precedence cannot match B–F safely
  → Path A with maximum hollow-skips
If Path A Orientation also insufficient
  → Path E
If even Orientation fails
  → Arrival + Closure C (minimum viable cognition)
```

---

## 10. Evaluation Algorithm (normative)

### Step 0 — Segment

| Segment | When |
|---------|------|
| `ENTRY` | Session start, full refresh, manual refresh (without return context) |
| `RETURN` | Merchant returns with handoff context |

### Step 1 — Resolve Arrival (ENTRY)

Compute Arrival A–F per Wireflow HOME-WF-00.  
On RETURN, do not re-play Arrival as first discovery; recompute quietly for lifecycle.

### Step 2 — Immediate Safety

If merchant-impacting Operational Health limits understanding or execution  
→ Path D (`R-SAFE-OPS`).

Inline trust: if Path C/B act blocked by ops → Path D **or** `R-INLINE-TRUST` before Route.

### Step 3 — Merchant Action

Else VIP primary → Path C.  
Else urgent Focus → Path B.

### Step 4 — Data / pending

Else Arrival D/F or insufficient → Path E.  
Else Arrival C or pending → Path F.

### Step 5 — Healthy default → Path A

### Step 6 — Hollow skips

Remove Understanding / Direction / Focus / Confidence per Adaptive Flow V2 rules.

### Step 7 — Emit + **LOCK** session path

### Step 8 — RETURN segment

Restore path context → drop resolved → activate deferred → Closure (`R-RETURN-CONTINUE`).

---

## 11. Path → Node Plans

Unchanged from Adaptive Cognitive Flow V2 (Paths A–F).  
See [`HOME_ADAPTIVE_COGNITIVE_FLOW_V2.md`](HOME_ADAPTIVE_COGNITIVE_FLOW_V2.md) §6.

---

## 12. Priority Model

```text
Immediate Safety
  → Merchant Action
    → Platform Trust (when it changes the act)
      → Business Understanding
        → Business Direction
          → Historical Perspective (route only)
```

---

## 13. Production Validation Lab

| Item | Value |
|------|-------|
| URL path | `/dev/adaptive-cognition-lab` |
| Purpose | Prove path selection, stability, governed re-eval |
| Home wiring | **Not performed** |
| Nav | **Not linked** |

Evidence operations:

1. Start session with fixture → path locked  
2. View tick × N → path unchanged  
3. Governed trigger → re-eval allowed  
4. `periodic_poll` → rejected  

---

## 14. Decision & STOP

| Item | Value |
|------|-------|
| Document | `HOME_COGNITIVE_ROUTER_V1.md` |
| Status | **Proposed** — hardened for Product Review |
| Home Wireframe | **Blocked** |
| Merchant Home wiring | **Not authorized by this lab alone** |

**STOP.** After production validation of the lab, await Product Review.  
Do not begin Wireframe.
