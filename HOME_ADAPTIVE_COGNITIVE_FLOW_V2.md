# Home Adaptive Cognitive Flow V2

**Document type:** Foundational Product Evolution — Merchant Cognition  
**Status:** **Proposed** — awaiting Product Review  
**Date (UTC):** 2026-07-18  
**Authority:** Adaptive merchant cognition for Home — supersedes the *linear* cognitive sequence in Home Wireflow V1  

**Supersedes (cognition sequencing only):** Fixed journey  
`Arrival → Orientation → Understanding → Focus → Confidence → Direction → Closure`  

**Does not supersede:** Wireflow node definitions · Inventory categories · Constitution · Surface Contract · IA layers as eligibility · UX Blueprint goals  

**Companion artifacts:**

| Artifact | File |
|----------|------|
| Cognitive Router | [`HOME_COGNITIVE_ROUTER_V1.md`](HOME_COGNITIVE_ROUTER_V1.md) |
| Adaptive scenarios | [`HOME_ADAPTIVE_SCENARIOS_V2.md`](HOME_ADAPTIVE_SCENARIOS_V2.md) |
| Traceability | [`HOME_ADAPTIVE_TRACEABILITY_V2.md`](HOME_ADAPTIVE_TRACEABILITY_V2.md) |
| Review | [`HOME_ADAPTIVE_REVIEW_V2.md`](HOME_ADAPTIVE_REVIEW_V2.md) |
| Stress findings addressed | [`HOME_COGNITIVE_STRESS_TEST_V1.md`](HOME_COGNITIVE_STRESS_TEST_V1.md) |

**Out of scope:** UI · Wireframe · visual design · implementation · routing code · governance edits · Home redesign  

---

## 1. Mission

Replace the fixed cognitive journey with an **Adaptive Cognitive Journey**.

Home chooses the appropriate cognition path from governed reality.

The merchant should never feel:

> I must pass through unnecessary steps.

---

## 2. Core Principle

**The merchant does not navigate Home.  
Home navigates the merchant.**

| Rule | Meaning |
|------|---------|
| Fixed entry | Every journey begins at Arrival |
| Adaptive continuation | Next mental state depends on governed reality |
| No invention | Router never invents information |
| Truth ownership | Router never creates, modifies, filters, or interprets business truth — sequencing only ([`HOME_COGNITIVE_ROUTER_V1.md`](HOME_COGNITIVE_ROUTER_V1.md)) |
| Session stability | Selected path locks for the cognition session until a governed re-evaluation trigger |
| Node optionality | Every node after Arrival must justify its presence |
| Act when ready | When Closure B is clear, Home must not force further briefing chapters |

---

## 3. Fixed Entry

### Arrival (always)

| Field | Value |
|-------|-------|
| **Node** | HOME-WF-00 (unchanged definition) |
| **Merchant Question** | Is my store okay? |
| **Output** | Exactly one Arrival outcome A–F (Wireflow) |
| **Next** | Cognitive Router selects Path A–F (or composed variant) |

After Arrival, the adaptive engine selects the next path.  
Arrival itself is never skipped.

---

## 4. Cognition Priority Model

The router evaluates cognition priority in this order:

```text
1. Immediate Safety          (store/platform limitation that blocks safe interpretation or action)
2. Merchant Action           (VIP / urgent attention requiring leave)
3. Platform Trust            (merchant-impacting operational health when it changes the act)
4. Business Understanding    (governed interpretation when eligible)
5. Business Direction        (governed trajectory when eligible)
6. Historical Perspective    (never on Home as exploration — only via route to owning surface)
```

| Priority | Typical Path | Merchant meaning |
|----------|--------------|------------------|
| 1 Immediate Safety | D | “Something in the platform limits me — know that first.” |
| 2 Merchant Action | B, C | “I must act / contact someone now.” |
| 3 Platform Trust | Confidence node (inline or Path D) | “Can I trust the system for this act?” |
| 4 Business Understanding | A, post-return on B/C/D | “What does CartFlow understand?” |
| 5 Business Direction | A, post-return | “Are we improving?” |
| 6 Historical Perspective | Route only | Not a Home cognition chapter |

---

## 5. Node Eligibility (every node optional after Arrival)

| Node | Why needed? | Can skip? | Can delay? | Alternate that can satisfy |
|------|-------------|-----------|------------|----------------------------|
| Arrival | Entry orientation class | **Never** | No | — |
| Orientation | Picture of “what is happening” | Yes if Arrival+Focus already carry enough for action-first paths | Yes (after return on B/C) | Brief Arrival deepening; post-return Orientation |
| Understanding | Business interpretation | Yes if gated/empty/H/G/E or action-first | Yes (after return on B/C) | Deferred; never hollow stage |
| Focus / VIP Focus | One primary concern | Yes if no action (Path A) | No when action exists — must be early | — |
| Confidence | Platform trust when merchant-impacting | Yes when healthy (silent) | Yes after return unless it blocks the act | Inline trust note before route if blocks act |
| Direction | Trajectory | Yes if gated/empty or action-first | Yes after return | Omit entirely when unavailable |
| Closure | Exit meaning A/B/C | **Never omit meaning** — may be immediate after Focus | No | — |
| Route / Return | Execution ownership | Only when Closure A/C | — | — |

**Hollow-stage rule:** A node with nothing merchant-worthy to say is **skipped**, not shown empty.

---

## 6. Primary Adaptive Paths

### PATH A — Healthy Store

```text
Arrival → Orientation → Understanding → Confidence → Direction → Closure
```

| Field | Value |
|-------|-------|
| **Entry conditions** | Arrival **A** Stable; no eligible VIP; no Top Merchant Attention requiring action; no merchant-impacting Operational Health; data sufficient for Orientation |
| **Priority** | Default when no higher priority path matches |
| **Required information** | Executive Summary; optional Store Change; optional BU if accepted; Confidence silent if healthy; optional Direction if approved |
| **Skipped nodes** | Focus (no action) |
| **Deferred nodes** | None |
| **Re-entry** | Full Path A recompute; not a “restart” if same visit context — fresh Arrival |
| **Closure** | **A** (no action required), or **C** if Understanding/Direction still forming without urgency |

**Merchant model**

| Dimension | Value |
|-----------|-------|
| Question | Is everything under control, and what should I know? |
| Emotion | Calm → Curious → Reassured → Confident |
| Goal | Briefing without work |
| Exit | Closure A (or C if still forming) |

---

### PATH B — Urgent Merchant Attention

```text
Arrival → Focus → Route → Return → Understanding → Confidence → Direction → Closure
```

| Field | Value |
|-------|-------|
| **Entry conditions** | Arrival **B**; primary concern is non-VIP (or VIP handled by Path C); eligible Top Merchant Attention or Merchant Alert requiring action |
| **Priority** | Merchant Action (2), below Immediate Safety (1) and VIP Path C when VIP wins |
| **Required information** | Primary Focus inputs; handoff context; post-return BU/ops/direction if eligible |
| **Skipped nodes** | Pre-route Orientation (optional micro-deepen inside Arrival only); pre-route Understanding; pre-route Direction |
| **Deferred nodes** | Orientation (light, on return if needed), Understanding, Confidence (unless blocks act — see Router), Direction |
| **Re-entry** | Restore context → lifecycle recompute → continue deferred nodes → Closure |
| **Closure** | Pre-route interim intent is **B**; final Closure A/B/C after return |

**Merchant model**

| Dimension | Value |
|-----------|-------|
| Question | What needs me now — and where do I go? |
| Emotion | Concerned → Determined → (return) Curious → Calm |
| Goal | Act first, understand later |
| Exit | Clear route; after return, Closure A if resolved else next Focus or Closure |

---

### PATH C — VIP

```text
Arrival → VIP Focus → Communication → Return → Confidence → Direction → Closure
```

| Field | Value |
|-------|-------|
| **Entry conditions** | Active eligible VIP is primary under priority model |
| **Priority** | Merchant Action (2) — VIP tie-break prefers Path C over Path B |
| **Required information** | VIP Alert; handoff (identity, phone if any, reason, freshness) |
| **Skipped nodes** | Pre-route Understanding (mandatory skip); pre-route Orientation chapter; pre-route Direction |
| **Deferred nodes** | Understanding (optional after return only if merchant-worthy — never forced); Confidence; Direction |
| **Re-entry** | “I came back” — VIP gone if resolved; then Confidence → Direction → Closure |
| **Closure** | Interim **B** → Communication; final A/B/C after return |

**Hard rule:** Do not force Business Understanding before VIP action.

**Merchant model**

| Dimension | Value |
|-----------|-------|
| Question | Who needs my personal outreach now? |
| Emotion | Concerned → Purposeful → (return) Reassured |
| Goal | Manual contact; never auto-send implication |
| Exit | Communication; then calm closure |

---

### PATH D — Operational Limitation

```text
Arrival → Operational Confidence → Settings → Return → Understanding → Closure
```

| Field | Value |
|-------|-------|
| **Entry conditions** | Arrival **E**, or merchant-impacting Operational Health that limits understanding/execution (integration down, recovery paused blocking outcomes, communication unavailable when it changes what merchant can do) |
| **Priority** | Immediate Safety (1) — highest |
| **Required information** | Operational Health (merchant language only) |
| **Skipped nodes** | Pre-route Understanding; pre-route Direction; Focus unless a separate action remains after ops |
| **Deferred nodes** | Understanding (after return); Direction (after return if eligible); Focus if still needed |
| **Re-entry** | Restore → if ops restored, continue Understanding → Closure; if not, Closure B may return to Settings |
| **Closure** | Interim **B** → Settings; final A/B/C after return |

**Hard rule:** Platform limitation precedes business interpretation.

**Merchant model**

| Dimension | Value |
|-----------|-------|
| Question | What is blocking CartFlow from working for my store? |
| Emotion | Concerned (platform) — not “business is declining” |
| Goal | Restore platform readiness |
| Exit | Settings; then safe Understanding if any |

---

### PATH E — Insufficient Data

```text
Arrival → Orientation → Closure
```

| Field | Value |
|-------|-------|
| **Entry conditions** | Arrival **D** or **F** (New Store / Insufficient Data); no urgent Focus; no merchant-impacting ops requiring Path D |
| **Priority** | Below action/safety paths |
| **Required information** | Executive Summary day-zero / insufficient framing only |
| **Skipped nodes** | Understanding (no fake); Focus; Confidence (unless Path D); Direction |
| **Deferred nodes** | All interpretation until evidence exists |
| **Re-entry** | New Arrival when merchant returns later |
| **Closure** | **C** Understanding still forming (or **B**→Settings if integration incomplete elevates to Path D) |

**Hard rule:** No fake understanding. No empty reasoning stage.

**Merchant model**

| Dimension | Value |
|-----------|-------|
| Question | Is it normal that there is little to know yet? |
| Emotion | Calm / Curious |
| Goal | Honest empty state |
| Exit | Closure C |

---

### PATH F — Understanding Pending

```text
Arrival → Orientation → Pending Understanding → Closure
```

| Field | Value |
|-------|-------|
| **Entry conditions** | Arrival **C**; data exists; safe Understanding not available; no Path B/C/D winner |
| **Priority** | Below action/safety |
| **Required information** | Orientation; explicit pending state (not hollow “Understanding” chapter with no content) |
| **Skipped nodes** | Full Understanding claims; Focus if none; Direction if none |
| **Deferred nodes** | Full Understanding until ready |
| **Re-entry** | Recompute; escape if pending repeats (see Dead Ends) |
| **Closure** | **C** |

**Pending Understanding** is a **named honest state**, not Business Understanding content. It must not look like a failed Reasoning panel.

**Merchant model**

| Dimension | Value |
|-----------|-------|
| Question | Is CartFlow still forming a safe view? |
| Emotion | Calm / Curious |
| Goal | No unsafe conclusion |
| Exit | Closure C |

---

## 7. Path Selection Precedence

When multiple paths could match, apply **first match**:

| Order | Path | Gate |
|------:|------|------|
| 1 | **D** Operational Limitation | Immediate Safety true |
| 2 | **C** VIP | VIP is primary Focus |
| 3 | **B** Urgent Attention | Arrival B / eligible non-VIP primary action |
| 4 | **E** Insufficient Data | Arrival D or F (and not D/C/B) |
| 5 | **F** Understanding Pending | Arrival C (and not D/C/B/E) |
| 6 | **A** Healthy Store | Default |

Composition rules:

| Situation | Behavior |
|-----------|----------|
| VIP + Communication unavailable | Path D first (or Confidence inline before Communication): merchant must know outreach is blocked, then VIP Focus when channel allows; never imply auto-send |
| VIP + other attention | Path C; other concerns deferred after return |
| Ops limited + no Settings-needed (info-only) | Confidence node without route if no configuration ownership; Closure may be A/C with caveat |
| Healthy + Direction gated | Path A with Direction skipped (hollow-stage rule) |

---

## 8. Cognitive Shortcuts (legitimate)

| Shortcut | Sequence | Allowed when |
|----------|----------|--------------|
| VIP express | Arrival → VIP Focus → Communication → Return → … | Path C |
| Action express | Arrival → Focus → Route → Return → … | Path B |
| Ops express | Arrival → Confidence → Settings → Return → … | Path D |
| Empty express | Arrival → Orientation → Closure C | Path E |
| Pending express | Arrival → Orientation → Pending → Closure C | Path F |
| Healthy silent Focus | Path A omits Focus | No action |
| Healthy silent Confidence | Confidence absent when healthy | Ops A |
| Skip empty Understanding | Never show State H/G as a chapter | Dependency / unavailable |
| Skip empty Direction | Never show gated Direction as a chapter | Trend not approved |

---

## 9. Return Flow

Returning from another surface must **never restart cognition**.

```text
Return
  → Restore prior path context (who I was, what I left to do)
  → Lifecycle recompute (resolved items leave)
  → Continue deferred nodes for that path
  → Closure
```

| Merchant should feel | Must not feel |
|----------------------|---------------|
| “I came back.” | “I started over.” |
| “That issue is done / still open.” | “Why am I seeing this again?” (if resolved) |

Handoff fields remain those in Wireflow Context Handoff Contract (unchanged).

---

## 10. Cognitive Dead Ends and Escapes

| Dead end | Escape |
|----------|--------|
| Repeated Pending Understanding (Path F) across visits with no change | After N visits (Product sets N; default proposal **3**), Closure C plus calm “still forming — no action needed”; never loop Understanding claims |
| Repeated unavailable Reasoning (State H/G) | Skip forever until Product Acceptance / availability; never re-teach the empty stage each visit |
| Repeated stale knowledge | Show last-good once with not-current; then prefer Orientation-only + Closure C until fresh; do not oscillate stale/fresh claims |
| Repeated routing to same unresolved item | Allow re-route with same identity; after return if unchanged, Closure may stay B with same destination — but Home must not re-animate full Arrival drama as if first discovery |
| Archive failure / item won’t leave | Remove from Home awareness per Wireflow; ops incident outside cognition; merchant must not be trapped reviewing a ghost |

---

## 11. Relationship to Wireflow V1

| Wireflow V1 element | Adaptive V2 treatment |
|---------------------|----------------------|
| Node field model (HOME-WF-00…06, VIP) | **Retained** as node definitions |
| Linear sequence | **Superseded** by Paths A–F + Router |
| Navigation / handoff / lifecycle / admission | **Retained** |
| Inventory / Constitution / Surface Contract | **Unchanged** (no governance edit in this task) |
| IA layer order | Remains **eligibility / meaning** order — not mandatory visit order |
| UX Blueprint goals | Retained; journey becomes adaptive |

---

## 12. Stress-Test Resolution Map

| Stress finding | Adaptive resolution |
|----------------|---------------------|
| Mental jump: Understanding before Focus on Arrival B | Path B/C — Focus first |
| Delayed routing after action-ready Focus | Path B/C — Route immediately after Focus |
| Hollow Understanding stage (H/G) | Skip; Path E/F or silent omit |
| Confidence oscillation (trust after urgency) | Confidence deferred to return unless it blocks the act; Path D when ops is the urgency |
| Direction after VIP | Deferred to return; skip if empty |
| Arrival ≈ Orientation double | Action paths skip Orientation chapter; healthy path deepens only |

---

## 13. Decision & STOP

| Item | Value |
|------|-------|
| Document | `HOME_ADAPTIVE_COGNITIVE_FLOW_V2.md` |
| Status | **Proposed** |
| Wireframe / UI / implementation | **Blocked** |
| Governance modified | **No** |

**STOP.** Await Product Review of Adaptive Cognitive Flow V2 suite.  
Do not begin Wireframe.
