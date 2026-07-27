# Home Constitution V2

**Status:** AUTHORIZED — final design authority for Home  
**Date (UTC):** 2026-07-27  
**Traceability:** Executive Home Research V1 · Home Information Budget V1 · Executive Information Value Law · Home Sentence Audit V1 · Home Storyboard V1  

This document is the **only** normative law for implementing Home. No improvisation beyond it.

---

## 1. Nature of Home

Home is an **executive briefing**.

Home is **not** an analytics dashboard, reporting page, or operational page.

Every sentence on Home must have **executive value**.

---

## 2. Home question

Home answers exactly one question:

> ماذا يجب أن أعرف الآن عن متجري؟

This question appears **once**. No synonym headline restating the same job.

---

## 3. Executive Information Value Law

A piece of information may occupy Home space **only if it changes what the merchant does next**.

Not: “Is this correct?”  
Yes: “Will this change the next action (including deliberate non-action)?”

If NO → remove from Home; keep on the constitutional owner page.

---

## 4. Information budget (hard)

| Slot (max 5) | Content | Owner of depth |
|--------------|---------|----------------|
| 1 | Store Health | Workspace (or Settings if disconnected; Communication if contact-blocked is the health story) |
| 2 | Today’s Top Decision | Workspace |
| 3 | Product Highlights (optional if signal) | Products / Workspace |
| 4 | Cart Summary (optional if signal) | Carts |
| 5 | Communication Summary (optional if signal) | Communication |

- **Primary executive actions:** 1 (the Top Decision move).  
- **View Details:** ≤1 per painted slot; destination = owner above.  
- **Glance:** ≤5s · **Full brief:** ≤30s.  
- **Primary decisions:** 1.

---

## 5. Forbidden on Home

- Bare counts / headcounts (“172 carts”, “8 customers”, numeric badges)  
- Evidence, confidence, timelines, operational history, raw observations  
- Technical status, situation IDs, diagnostics, `simulation_run_id`  
- Tables, settings wizards, roadmap placeholders  
- Meta chrome: “ملخص تنفيذي”, “ملخص سريع فقط…”, ownership footer essays  
- Loading greetings, store name, date as Home content  
- Duplicate View Details on the same owner  
- Status tags with no executive value (“القرار الأهم”, “منتج”, “مكتمل اليوم”)

---

## 6. Allowed executive meanings (examples)

- Review checkout / conversion for a named subject  
- Named product needs attention  
- Customer communication is blocked  
- Recovery is operating normally / store is stable (authorizes calm)

---

## 7. 30-second storyboard (must hold)

| Time | Merchant mind |
|------|----------------|
| 0–5s | Store condition is clear |
| 5–10s | One attention thread wins |
| 10–15s | Kind of next step is clear |
| 15–20s | One stance formed (act / unblock / product / hold) |
| 20–30s | Next owner page feels inevitable |

Desktop and Mobile: **identical meaning**.

---

## 8. Owner destinations

| Home signal | View Details → |
|-------------|----------------|
| Top Decision | `#workspace` |
| Product Highlights | `#workspace` (decision) or `#products` when product-only signal |
| Cart Summary | `#carts` |
| Communication Summary | `#communication` |
| Health (disconnected) | `#settings` |
| Health (contact-blocked story) | `#communication` |
| Health (otherwise) | `#workspace` |

---

## 9. Silence

When healthy and no decision: paint Health (calm) and omit empty domain slots.  
Do not invent urgency. Calm is a valid executive outcome.

---

## 10. STOP / CEO Review

After implementation and production deploy: **review Home only**.  
No Workspace / Products / Carts / Communication / Settings work until **HOME APPROVED**.

---

*End of Home Constitution V2*
