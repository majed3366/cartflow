# CartFlow Carts Workspace Experience V1

**Status:** Implemented — Product Excellence Sprint 1  
**Date (UTC):** 2026-07-06  
**Scope:** Presentation-only upgrade of normal-carts row detail (`#page-carts`)  
**Authority:** [`merchant_experience_patterns_v1.md`](merchant_experience_patterns_v1.md), [`merchant_experience_design_language_v1.md`](merchant_experience_design_language_v1.md)

---

## Executive summary

The Carts Workspace row detail now reads as a **conversation with CartFlow**, not an operational audit block. Governed knowledge from `cart_detail_projection_v1` / `merchant_explanation_v1` is composed into certified Merchant Experience Patterns — with no routing, decision, API, or lifecycle changes.

**Before:** Label-heavy paragraph walls (`ماذا حدث؟`, `ماذا فعل CartFlow؟`, …) with proof and follow-up inline.  
**After:** Fixed visual hierarchy — Recovery Story → Suggested Action → Timeline (collapsed) → secondary lifecycle controls.

---

## Pattern certification

| Pattern | Implementation | Status |
|---------|----------------|--------|
| **MXP-1 Achievement** | `ma-cart-achievement-v1` from `merchant_cart_fact_v1` | PASS |
| **MXP-3 Waiting** | `ma-cart-waiting-band` on beat 3 when `!action_required` | PASS |
| **MXP-4 Recovery Story** | `ma-cart-recovery-story-v1` — what → did → next → action | PASS |
| **MXP-5 Timeline** | `<details class="ma-cart-timeline-v1">` — proof, follow-up, movement | PASS |
| **MXP-9 Suggested Action** | `ma-cart-action-primary` from routed `suggested_action` + contact | PASS |

---

## Files changed

| File | Change |
|------|--------|
| `static/merchant_dashboard_lazy.js` | `merchantCartWorkspaceFromParts`, story/action/timeline composers; `cartRowFull` / `cartRowHome` unified workspace |
| `static/merchant_app.css` | Whisper-styled `.ma-cart-*` pattern family |
| `tests/test_merchant_carts_workspace_experience_v1.py` | Pattern composition certification |
| `scripts/_carts_workspace_v1_fixture.html` | Before/after fixture |
| `scripts/_carts_workspace_v1_screenshots.py` | Screenshot capture |

---

## Reading flow (merchant path)

```
Scan table row (amount, reason, status, next line)
        ↓
Achievement beat (if cart fact exists)
        ↓
Recovery story headline + four beats
        ↓
Primary suggested action (one control)
        ↓
Optional «التفاصيل» timeline expand
        ↓
Secondary archive/reopen (when routed)
```

---

## Before / After

Screenshots: `scripts/_carts_workspace_v1_out/`

| Asset | Description |
|-------|-------------|
| `01_carts_workspace_before.png` | Legacy paragraph-wall labels |
| `02_carts_workspace_after.png` | MXP-composed workspace |
| `03_carts_workspace_comparison.png` | Side-by-side fixture |
| `04_carts_workspace_after_mobile.png` | Mobile viewport after state |

Regenerate: `python scripts/_carts_workspace_v1_screenshots.py`

---

## Product Excellence review

### What improved

1. **Reading effort reduced** — beats replace repeated question labels; status is the headline.
2. **Paragraph walls removed** — hierarchy is structural, not textual.
3. **Important fact first** — achievement + status headline before proof/history.
4. **Whisper principle** — timeline and proof collapsed; neutral waiting band instead of alert styling.
5. **Action clarity** — one primary affordance; lifecycle controls demoted to secondary.

### What did not change

- No business logic, lifecycle, routing, or knowledge production changes.
- Same payload fields consumed; presentation composition only.
- Table columns, filters, and tab routing unchanged.

### Residual cohesion notes (out of sprint scope)

- Carts **list** remains table-first (Cohesion Program Phase 1 target).
- Home mini-cart rows now share workspace composer for consistency.

---

## Success criteria check

| Criterion | Result |
|-----------|--------|
| Merchant understands what happened | Story beat 1 + headline |
| What CartFlow did | Story beat 2 + achievement |
| What happens next | Waiting band / beat 3 |
| Whether they need to act | Beat 4 + primary action |
| Feels like CartFlow, not ops console | PASS (detail region) |

**Verdict:** Sprint 1 PASS for cart row detail experience.
