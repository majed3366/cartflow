# Scenario Execution Plan V1

**Status:** Governed scenarios for landing evidence capture.  
**Date (UTC):** 2026-07-29  
**Rule:** No manual editing of screenshots to fabricate missing behaviour.

---

## SCN-HOME-01 — Living Store Home attention

| Field | Definition |
|-------|------------|
| **Business Story** | Merchant opens Home and sees what needs attention now. |
| **Starting State** | Living Store / demo with materialised Home content |
| **Required Events** | Dashboard load; Home Constitution V2 / Simplification-era face |
| **Expected Product Behaviour** | Executive Home paints; attention/top decision visible when evidence exists |
| **Expected Merchant Surface** | `#home` |
| **Expected Customer Surface** | N/A |
| **Failure Conditions** | Empty Home presented as intelligence; stale face; PII |
| **Recovery Procedure** | Run admission/materialisation; use known Living Store seed |
| **Capture Point** | Desktop + mobile Home after paint stable |
| **Approval Owner** | Product |
| **Assets** | EV-001, EV-010, EV-011, EV-015 |

---

## SCN-DEC-01 — Workspace decision face

| Field | Definition |
|-------|------------|
| **Business Story** | Merchant opens Workspace and sees Priority → Evidence → Decision → Action/wait. |
| **Starting State** | Same store as SCN-HOME-01 with Workspace primary |
| **Required Events** | Navigate `#workspace`; Simplification face |
| **Expected Product Behaviour** | One primary decision; wait copy when NEEDS_MORE_EVIDENCE |
| **Expected Merchant Surface** | `#workspace` |
| **Expected Customer Surface** | N/A |
| **Failure Conditions** | Engine IDs visible; KPI landscape; dual primaries |
| **Recovery Procedure** | Confirm Simplification flag/face; Living Store rebuild |
| **Capture Point** | Desktop (+ optional mobile) Workspace |
| **Approval Owner** | Product |
| **Assets** | EV-014 |

---

## SCN-WIDGET-01 — In-store tool appears

| Field | Definition |
|-------|------------|
| **Business Story** | Customer on storefront sees calm in-store assistance surface. |
| **Starting State** | Demo or Zid test store with V2 widget loaded |
| **Required Events** | Page load; widget eligibility; open/show |
| **Expected Product Behaviour** | V2 runtime UI on storefront — not merchant settings |
| **Expected Merchant Surface** | N/A |
| **Expected Customer Surface** | Storefront + widget |
| **Failure Conditions** | Settings page; legacy harness unlabeled; real PII |
| **Recovery Procedure** | Confirm `widget_loader` V2 path; demo store |
| **Capture Point** | Widget visible on storefront (mobile primary) |
| **Approval Owner** | Product + Eng |
| **Assets** | EV-002 |

---

## SCN-WIDGET-02 — Hesitation interaction

| Field | Definition |
|-------|------------|
| **Business Story** | Customer engages hesitation choice (e.g. yes/no path). |
| **Starting State** | SCN-WIDGET-01 open |
| **Required Events** | Trigger → hesitation UI |
| **Expected Product Behaviour** | Real choice UI |
| **Expected Merchant Surface** | N/A |
| **Expected Customer Surface** | Widget hesitation |
| **Failure Conditions** | Invented choices; mind-reading captions burned in |
| **Recovery Procedure** | Replay visual-gate / demo lab scenario |
| **Capture Point** | Hesitation step |
| **Approval Owner** | Product |
| **Assets** | EV-003, EV-016 |

---

## SCN-WIDGET-03 — Reason selection

| Field | Definition |
|-------|------------|
| **Business Story** | Customer selects a hesitation reason. |
| **Starting State** | After hesitation path |
| **Required Events** | Reason UI; optional `POST /api/cartflow/reason` |
| **Expected Product Behaviour** | Real configured reasons |
| **Expected Merchant Surface** | Later visible in merchant reasons (not required in same shot) |
| **Expected Customer Surface** | Reason list/selection |
| **Failure Conditions** | Fake % on reasons; settings editor |
| **Recovery Procedure** | Demo reason set |
| **Capture Point** | Reason UI with readable Arabic |
| **Approval Owner** | Product |
| **Assets** | EV-004 |

---

## SCN-WA-01 — WhatsApp continuation

| Field | Definition |
|-------|------------|
| **Business Story** | After abandon, recovery continues via WhatsApp with visible state. |
| **Starting State** | Demo cart abandoned; recovery scheduled/sent |
| **Required Events** | Schedule/send; merchant-visible message state |
| **Expected Product Behaviour** | Continuation layer — not blast UI |
| **Expected Merchant Surface** | Communication/messages |
| **Expected Customer Surface** | Optional phone thread if capturable without PII |
| **Failure Conditions** | Settings-only; Meta theatre; guaranteed delivery graphics |
| **Recovery Procedure** | Ops-capable Twilio/demo path; disclose gates |
| **Capture Point** | Journey/state visible |
| **Approval Owner** | Product + Ops |
| **Assets** | EV-005 |

---

## SCN-WA-02 — Customer reply

| Field | Definition |
|-------|------------|
| **Business Story** | Customer replies; merchant sees follow-up state. |
| **Starting State** | After outbound recovery |
| **Required Events** | Inbound reply recorded |
| **Expected Product Behaviour** | Reply reflected in merchant UI |
| **Failure Conditions** | Fabricated unread counts |
| **Capture Point** | Reply visible |
| **Approval Owner** | Product + Ops |
| **Assets** | EV-006 |

---

## SCN-WA-03 — Merchant follow-up

| Field | Definition |
|-------|------------|
| **Business Story** | Merchant sees follow-up / communication status after reply. |
| **Starting State** | SCN-WA-02 |
| **Expected Merchant Surface** | `#communication` |
| **Capture Point** | Follow-up state |
| **Approval Owner** | Product + Ops |
| **Assets** | EV-007 |

---

## SCN-PUR-01 — Purchase stop

| Field | Definition |
|-------|------------|
| **Business Story** | Customer purchases; unnecessary recovery stops. |
| **Starting State** | Active recovery; then conversion |
| **Required Events** | `POST /api/conversion` / Purchase Truth |
| **Expected Product Behaviour** | Purchased + stopped further messages |
| **Expected Merchant Surface** | Carts / proof |
| **Failure Conditions** | Messages continue; fake savings |
| **Capture Point** | Purchased/stopped Arabic labels |
| **Approval Owner** | Product |
| **Assets** | EV-008 |

---

## SCN-RET-01 — Customer return

| Field | Definition |
|-------|------------|
| **Business Story** | Customer returns to store after message; merchant sees return. |
| **Starting State** | After recovery touch |
| **Required Events** | Return signal |
| **Expected Product Behaviour** | Return distinguishable in UI |
| **Failure Conditions** | Claim language ≠ actual signal |
| **Capture Point** | Return state |
| **Approval Owner** | Product |
| **Assets** | EV-009 |

---

## SCN-KNOW-01 — Knowledge with evidence

| Field | Definition |
|-------|------------|
| **Business Story** | Merchant sees a governed finding/knowledge object with evidence cue. |
| **Starting State** | Materialised findings (ORV/Living Store) |
| **Required Events** | Knowledge/findings paint |
| **Expected Product Behaviour** | Evidence-linked; not fabricated |
| **Failure Conditions** | Empty theatre; theme claims without RV |
| **Capture Point** | Card + evidence state |
| **Approval Owner** | Product |
| **Assets** | EV-012 |

---

## SCN-KNOW-02 — Insufficient evidence honesty

| Field | Definition |
|-------|------------|
| **Business Story** | Merchant sees that evidence is insufficient / wait. |
| **Starting State** | Weak/empty evidence store or Workspace wait |
| **Expected Product Behaviour** | Honest Arabic — not product-broken look |
| **Capture Point** | Insufficient/wait/empty Home as honesty |
| **Approval Owner** | Product |
| **Assets** | EV-013 |

---

## SCN-CTA-01 / SCN-CTA-02 — Signup / Login

| Field | Definition |
|-------|------------|
| **Business Story** | Merchant can create account / log in. |
| **Starting State** | Logged out |
| **Required Events** | Open `/signup` or `/login` |
| **Expected Product Behaviour** | Forms render; Arabic UI |
| **Failure Conditions** | Demo CTA invented; fake social proof |
| **Capture Point** | Full public form (no secrets filled) |
| **Approval Owner** | Product |
| **Assets** | EV-017, EV-018 |

---

## SCN-INT-01 — Integration text truth

| Field | Definition |
|-------|------------|
| **Business Story** | Honest platform readiness. |
| **Starting State** | N/A (documentation/ops truth) |
| **Expected Product Behaviour** | Zid supported ops-gated; Salla/Shopify planned |
| **Failure Conditions** | Logo wall; “all platforms” |
| **Capture Point** | Text asset only |
| **Approval Owner** | Product |
| **Assets** | EV-019 |

---

## SCN-LEG-01…03 — Contact / Privacy / Terms

| Field | Definition |
|-------|------------|
| **SCN-LEG-01** | Contact mailto exists → EV-020 |
| **SCN-LEG-02** | Privacy page must exist before EV-021 |
| **SCN-LEG-03** | Terms page must exist before EV-022 |
| **Approval Owner** | Legal + Product |
