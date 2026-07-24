# Priority Rule Documentation V1

**Engine:** Decision Composition Engine V1  
**Authority:** Deterministic rules — not AI.

---

## Formula

```text
priority_score =
    scale(0–30)
  + impact(0–25)
  + urgency(0–20)
  + actionability(0–15)
  + evidence(0–10)
  − automation_discount(0–20)

Clamped to 0–100.
```

### Scale (affected carts/customers)

| Count | Points |
|------:|-------:|
| 1 | 4 |
| 2–4 | 8 |
| 5–9 | 12 |
| 10–19 | 18 |
| 20–39 | 24 |
| ≥40 | 30 |

### Impact (decision type)

| Type | Points |
|------|-------:|
| recoverability_gap | 25 |
| verified_existing_finding | 20 |
| waiting_recovery_work | 12 |

### Urgency

Base by type (recoverability 18, finding 14, waiting 10) +2 if `why_now` contains «الآن»/«اليوم» (cap 20).

### Actionability

15 if first_step present and not automation-resolvable; 2 if automation can resolve; else 5.

### Evidence (confidence)

high=10, medium=6, low=3.

### Automation discount

−20 when the condition is normally handled by CartFlow without merchant action.

---

## Bands

| Score / condition | Band | Merchant meaning |
|-------------------|------|------------------|
| ≥55 | `needs_action_now` | يحتاج إجراء الآن |
| 30–54 | `monitor` | راقب |
| <30 or empty publish set | `no_decision_supported` | لا قرار مدعوم حالياً |

**Priority ≠ raw count.** A small recoverability gap can outrank a large automated wait.
