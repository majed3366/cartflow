# Executive Compression — Examples Before / After V1

**Status:** Architecture only — illustrative compression.  
**Date (UTC):** 2026-07-28  
**Authority:** Examples under [`EXECUTIVE_COMPRESSION_CONSTITUTION_V1.md`](./EXECUTIVE_COMPRESSION_CONSTITUTION_V1.md).  
**Non-goals:** Not production copy. Not UI. Not implementation.

Examples show **shape of compression**, not final merchant wording.

---

## Example A — Shipping (playbook READY)

### Before (over-explain / system voice)

> Our diagnostic pipeline observed elevated leave-after-shipping signals on carts in the SAR 120–150 band (n=…). Confidence is 87% after ORV correlation with shipping_cost_first_shown. Playbook validation passed PBL-001 questions 1–7. Publication metadata requires Minimum Confidence 85% and READY. You should review shipping configuration on your commerce platform because conversion may improve if shipping friction is reduced. Evidence expansion ticket E-… remains open for secondary causes.

### After (compressed)

> **What:** Open shipping settings and review shipping cost for orders below SAR 150.  
> **Why:** Customers leave after shipping is shown in that band.  
> **Act now:** Yes.  
> **Where:** Commerce platform — shipping settings.

---

## Example B — Diagnosis only (playbook suppressed)

### Before

> We detected possible checkout friction. Confidence is moderate. Playbook validation failed the Consistency Test. Please investigate checkout fields and gather more evidence while we continue collecting.

### After

> **What is happening:** Customers drop at checkout; CartFlow does not yet have a single executable action.  
> **Why:** Evidence is not yet consistent enough for a playbook.  
> **Act now:** No — wait while CartFlow strengthens the diagnosis.  
> **Where:** — (omitted)

---

## Example C — Recovery message (CartFlow locus)

### Before

> Message template R1 shows open rate OK but return-to-checkout is weak. EM Type A. Routing will send you to Carts/Communication. Avoid changing unrelated templates. Reality validation class = higher recovery. Review cadence monthly.

### After

> **What:** Revise the first recovery message (offer/CTA clarity).  
> **Why:** Customers open it but rarely return to complete checkout.  
> **Act now:** Yes.  
> **Where:** CartFlow — recovery message.

---

## Example D — Home teaser vs Workspace commit

### Before (Home dumps Workspace)

> Full diagnosis, three evidence bullets, confidence, methodology how/avoid/verify, and two alternative actions on Home.

### After

| Surface | Compressed |
|---------|------------|
| **Home** | Shipping cost below SAR 150 is pushing customers away — act on platform shipping settings now. |
| **Workspace** | Same decision: What / Why / Act now / Where (+ expected result if load-bearing). No evidence museum. |

---

## Example E — Notification

### Before

> CartFlow Executive Compression / Decision Playbook Engine notification: PF-SHIPPING instance validated. Confidence 85%+. Tap to see evidence chain and publication metadata.

### After

> Shipping costs below SAR 150 need your decision today — open shipping settings.

---

## Quality check on After examples

| Test | A | B | C | D | E |
|------|---|---|---|---|---|
| ≤15 seconds | Yes | Yes | Yes | Yes | Yes |
| Scroll to understand | No | No | No | No | No |
| Business question immediate | Yes | Yes | Yes | Yes | Yes |
| Sentences load-bearing | Yes | Yes | Yes | Yes | Yes |
| System explaining itself | No | No | No | No | No |

---

## STOP

Examples are architectural illustration only.

**No production copy. No UI. No implementation.**
