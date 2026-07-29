# Visual Evidence Capture Plan V1

**Status:** Governed capture plan — **not** screenshot selection or execution.  
**Date (UTC):** 2026-07-29  
**Parent:** Landing Page Evidence Readiness V1  

This plan defines what must later be captured and under what conditions. Completing this document does **not** authorise capture.

---

## Capture governance (binding)

Every future capture must:

- Use current approved product UI  
- Use demo or synthetic merchant data only  
- Contain **no** real personal customer data (phones, names, addresses)  
- Reflect a reproducible scenario  
- Match the claim beside it  
- Preserve readable Arabic  
- Avoid misleading cropping  
- Avoid fake overlays / invented notifications  
- Avoid numbers inserted in Figma  
- Avoid combining unrelated states into one false screen  
- State **illustrative** when a composed scenario is not a natural single-screen state  

### Screenshot eligibility

**Eligible only if:** UI current · data truthful · state understandable · behaviour reproducible · supports one claim · no sensitive data · no misleading explanation required.

**Ineligible if:** stale UI · developer tools · test-only routes · fake metrics · deceptive state mashups · commercially unready capability · bug/temporary state · empty knowledge as proven intelligence · unverified platform state · needs heavy 3D to be understandable.

### Sensitive data rules

| Must scrub / avoid | Allowed |
|--------------------|---------|
| Real customer phones | Synthetic Lab phones |
| Real names / addresses | Demo catalog names |
| Real merchant secrets | Living Store / demo store |
| Production PII exports | Screenshots from demo/Living Store only |

---

## Capture candidates

### CAP-01 — Hero restrained product preview

| Field | Value |
|-------|-------|
| **Target Section** | LP-02 |
| **Evidence Objective** | Optional recognition support — not Hero dependency |
| **Required Product State** | Calm Home or Workspace primary — no empty-as-intelligence |
| **Required Scenario** | Living Store / demo with at least one clear attention object |
| **Required Environment** | Production UI against demo store |
| **Desktop or Mobile** | Desktop preferred; mobile optional |
| **Sensitive Data Rules** | Demo only |
| **UI Freshness** | Post–Workspace Simplification / Home V2 faces |
| **Truth Checks** | No fake KPIs; no CIP caption |
| **Must Be Visible** | Merchant-recognisable operating clarity |
| **Must Be Hidden** | Dev tools, flags, internal IDs, admin chrome |
| **Allowed Annotation** | None or single calm outcome caption later |
| **Prohibited Decoration** | 3D cages, glow frames, fake badges |
| **Retake Conditions** | Face changes; empty state; PII leak |
| **Approval Owner** | Product + Design |
| **Plan status** | **Optional** — Hero may ship without |

---

### CAP-02 — In-store tool — mobile storefront

| Field | Value |
|-------|-------|
| **Target Section** | LP-06 |
| **Evidence Objective** | Prove tool appears in customer storefront (not settings) |
| **Required Product State** | Widget eligible to show; V2 runtime |
| **Required Scenario** | Demo or Zid test storefront with cart/hesitation path |
| **Required Environment** | Real storefront embed (demo store acceptable if production widget) |
| **Desktop or Mobile** | **Mobile primary** |
| **Sensitive Data Rules** | No real customer phone |
| **UI Freshness** | Current V2 UI |
| **Truth Checks** | Not settings; not legacy harness unless labeled |
| **Must Be Visible** | In-store tool chrome on storefront |
| **Must Be Hidden** | Partner admin, CartFlow merchant dashboard |
| **Allowed Annotation** | None |
| **Prohibited Decoration** | Invented store theme overlays |
| **Retake Conditions** | UI redesign; wrong surface |
| **Approval Owner** | Product + Engineering |
| **Plan status** | **Required** for LP-06 publish |

---

### CAP-03 — Hesitation reason interaction

| Field | Value |
|-------|-------|
| **Target Section** | LP-06 |
| **Evidence Objective** | Real hesitation choices / reason selection |
| **Required Product State** | Reason UI open |
| **Required Scenario** | Customer selects a real configured reason |
| **Required Environment** | Same as CAP-02 |
| **Desktop or Mobile** | Mobile primary |
| **Sensitive Data Rules** | Demo |
| **UI Freshness** | Current |
| **Truth Checks** | Choices are real product reasons |
| **Must Be Visible** | Reason list / selection |
| **Must Be Hidden** | Settings editor |
| **Allowed Annotation** | None |
| **Prohibited Decstyles** | Fake % on reasons |
| **Retake Conditions** | Reason set changes materially |
| **Approval Owner** | Product |
| **Plan status** | **Required** with CAP-02 |

---

### CAP-04 — WhatsApp continuation journey

| Field | Value |
|-------|-------|
| **Target Section** | LP-07 |
| **Evidence Objective** | Continuation after storefront — not settings |
| **Required Product State** | Recovery message scheduled/sent state visible to merchant |
| **Required Scenario** | Demo cart abandoned → recovery step |
| **Required Environment** | Ops-capable demo; disclose provider |
| **Desktop or Mobile** | Desktop or mobile merchant |
| **Sensitive Data Rules** | Mask phone to synthetic pattern |
| **UI Freshness** | Current communication/messages |
| **Truth Checks** | Not Meta brand theatre; not bulk blast UI |
| **Must Be Visible** | Journey/step or message state |
| **Must Be Hidden** | API keys, webhook raw JSON, admin ops |
| **Allowed Annotation** | Illustrative if composed |
| **Prohibited Decstyles** | Fake “Delivered 100%” |
| **Retake Conditions** | Provider stack change |
| **Approval Owner** | Product + Ops |
| **Plan status** | **Required** for LP-07 journey claim |

---

### CAP-05 — Customer response / merchant follow-up

| Field | Value |
|-------|-------|
| **Target Section** | LP-07 |
| **Evidence Objective** | Reply becomes merchant-visible follow-up |
| **Required Product State** | Inbound reply reflected in merchant UI |
| **Required Scenario** | Demo reply on recovery thread |
| **Required Environment** | Provider-capable demo |
| **Desktop or Mobile** | Either |
| **Sensitive Data Rules** | Mask content if personal |
| **UI Freshness** | Current |
| **Truth Checks** | Do not imply guaranteed replies |
| **Must Be Visible** | Reply / follow-up state |
| **Must Be Hidden** | Raw provider payloads |
| **Allowed Annotation** | None |
| **Prohibited Decstyles** | Fake unread counts |
| **Retake Conditions** | Reply pipeline change |
| **Approval Owner** | Product + Ops |
| **Plan status** | **Required** if reply claim published |

---

### CAP-06 — Purchase closure / suppression

| Field | Value |
|-------|-------|
| **Target Section** | LP-07, LP-12 |
| **Evidence Objective** | Purchase stops unnecessary recovery |
| **Required Product State** | Purchased / stopped state on carts or proof |
| **Required Scenario** | Demo conversion after recovery |
| **Required Environment** | Demo |
| **Desktop or Mobile** | Either |
| **Sensitive Data Rules** | Demo |
| **UI Freshness** | Current |
| **Truth Checks** | Matches Purchase Truth |
| **Must Be Visible** | Purchased / stopped (or equivalent merchant Arabic) |
| **Must Be Hidden** | Internal stop codes |
| **Allowed Annotation** | None |
| **Prohibited Decstyles** | Fake savings amounts |
| **Retake Conditions** | Lifecycle label change |
| **Approval Owner** | Product |
| **Plan status** | **Strongly recommended** |

---

### CAP-07 — Home or merchant dashboard

| Field | Value |
|-------|-------|
| **Target Section** | LP-08 |
| **Evidence Objective** | Current merchant operating surface |
| **Required Product State** | Home with truthful non-misleading content |
| **Required Scenario** | Living Store after admission/materialisation |
| **Required Environment** | Production UI / Living Store |
| **Desktop or Mobile** | Desktop + consider CAP-15 |
| **Sensitive Data Rules** | Demo store |
| **UI Freshness** | Home Constitution V2 era or newer |
| **Truth Checks** | No empty-as-proof; no stale May landing look |
| **Must Be Visible** | Executive Home clarity |
| **Must Be Hidden** | Perf flags, `?home_perf`, internal markers |
| **Allowed Annotation** | Outcome caption later |
| **Prohibited Decstyles** | 3D dashboard frames |
| **Retake Conditions** | Home face change |
| **Approval Owner** | Product |
| **Plan status** | **Required** for LP-08 |

---

### CAP-08 — Attention state

| Field | Value |
|-------|-------|
| **Target Section** | LP-08, LP-10 |
| **Evidence Objective** | What needs attention now |
| **Required Product State** | Top Decision / primary attention visible |
| **Required Scenario** | Living Store with Active primary |
| **Required Environment** | Same as CAP-07 |
| **Desktop or Mobile** | Desktop |
| **UI Freshness** | Current Simplification / Home |
| **Truth Checks** | Attention is real product state |
| **Must Be Visible** | Priority / attention object |
| **Must Be Hidden** | Multiple competing primaries |
| **Approval Owner** | Product |
| **Plan status** | **Required** |

---

### CAP-09 — Customer returned to store

| Field | Value |
|-------|-------|
| **Target Section** | LP-08, LP-07 |
| **Evidence Objective** | Return distinguishable in merchant UI |
| **Required Product State** | Return signal visible on carts/journey |
| **Required Scenario** | Demo return after message |
| **Required Environment** | Demo |
| **Truth Checks** | Language matches actual signal (verify before claim) |
| **Plan status** | **Conditional** — only if return claim published |
| **Approval Owner** | Product |

---

### CAP-10 — Confirmed purchase

| Field | Value |
|-------|-------|
| **Target Section** | LP-08, LP-07 |
| **Evidence Objective** | Purchase distinguishable from return |
| **Required Product State** | Purchased state |
| **Required Scenario** | Demo purchase |
| **Plan status** | **Recommended** with CAP-06 |
| **Approval Owner** | Product |

---

### CAP-11 — Knowledge card with sufficient evidence

| Field | Value |
|-------|-------|
| **Target Section** | LP-09 |
| **Evidence Objective** | Pattern + evidence linkage visible |
| **Required Product State** | Materialised finding/knowledge with evidence state |
| **Required Scenario** | ORV/Living Store with findings painted |
| **Required Environment** | Production UI demo store |
| **Truth Checks** | Not fabricated; evidence visible; not empty theatre |
| **Must Be Visible** | Knowledge/finding + evidence cue |
| **Must Be Hidden** | Internal registry IDs |
| **Allowed Annotation** | **Illustrative** if not natural single-merchant claim |
| **Plan status** | **Required** for pattern publish |
| **Approval Owner** | Product |

---

### CAP-12 — Insufficient evidence state

| Field | Value |
|-------|-------|
| **Target Section** | LP-09, LP-12 |
| **Evidence Objective** | Honesty when evidence insufficient |
| **Required Product State** | NEEDS_MORE_EVIDENCE / wait / insufficient merchant language |
| **Required Scenario** | Workspace or Home insufficient state |
| **Truth Checks** | Reads as honesty, not product failure |
| **Plan status** | **Required** if Knowledge section ships |
| **Approval Owner** | Product |

---

### CAP-13 — Conflicting evidence state

| Field | Value |
|-------|-------|
| **Target Section** | LP-09 |
| **Evidence Objective** | Conflict not hidden |
| **Required Product State** | Conflicting signals shown if product supports |
| **Plan status** | **Reject if unsupported** — do not invent |
| **Approval Owner** | Product |

---

### CAP-14 — Decision-support surface

| Field | Value |
|-------|-------|
| **Target Section** | LP-10 |
| **Evidence Objective** | Decision support without replacing merchant |
| **Required Product State** | Workspace Simplification face: Priority → Evidence → Decision → Action/wait |
| **Required Scenario** | Living Store primary decision |
| **UI Freshness** | Post-Simplification V1 |
| **Plan status** | **Required** for LP-10 visual |
| **Approval Owner** | Product |

---

### CAP-15 — Mobile merchant experience

| Field | Value |
|-------|-------|
| **Target Section** | LP-08, LP-10 |
| **Evidence Objective** | Mobile-first constitution compliance |
| **Required Product State** | Same as CAP-07/14 on mobile viewport |
| **Desktop or Mobile** | **Mobile** |
| **Plan status** | **Required** (at least one mobile merchant shot) |
| **Approval Owner** | Product + Design |

---

### CAP-16 — Integration readiness representation

| Field | Value |
|-------|-------|
| **Target Section** | LP-13 |
| **Evidence Objective** | Truthful status — not logo wall |
| **Required Product State** | Text list or connection UI showing Zid without false Salla/Shopify live |
| **Truth Checks** | Ops-gated Zid disclosed; Planned others |
| **Allowed Annotation** | Status labels only |
| **Prohibited Decstyles** | Unsupported logos |
| **Plan status** | **Text preferred**; UI optional |
| **Approval Owner** | Product |

---

## Capture candidate decisions summary

| Capture ID | Decision |
|------------|----------|
| CAP-01 | Optional |
| CAP-02 | **Required** for LP-06 |
| CAP-03 | **Required** for LP-06 |
| CAP-04 | **Required** for LP-07 journey |
| CAP-05 | Required if reply claim |
| CAP-06 | Strongly recommended |
| CAP-07 | **Required** for LP-08 |
| CAP-08 | **Required** |
| CAP-09 | Conditional |
| CAP-10 | Recommended |
| CAP-11 | **Required** for pattern claims |
| CAP-12 | **Required** with Knowledge section |
| CAP-13 | Reject if unsupported |
| CAP-14 | **Required** for LP-10 visual |
| CAP-15 | **Required** |
| CAP-16 | Text preferred |

**Rejected sources for future capture substitution:** `static/img/landing/widget_settings.png`, `whatsapp_settings.png`, and other May 2026 landing ops crops as stand-ins for current faces or journeys.
