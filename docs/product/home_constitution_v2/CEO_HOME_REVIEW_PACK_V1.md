# Home Constitution V2 — CEO Home Review Pack

**Status:** Production deployed · Home-only CEO Review  
**Date (UTC):** 2026-07-27  
**Commit:** `e2585f7` (+ follow-up evidence commit)  
**Store:** Living Store review · `demo` · `cf.living.store.review@smartreplyai.net`  
**Verdict (automated):** `PASS_HOME_CONSTITUTION_V2`  
**Evidence:** `prod_home_ceo_review.json` · `prod_desktop_home.png` · `prod_mobile_home.png`

---

## Scope

Review **Home only** (`/dashboard#home`).

Do **not** review Workspace / Products / Carts / Communication / Settings until **HOME APPROVED**.

---

## What Home must answer

> ماذا يجب أن أعرف الآن عن متجري؟

(Once — in the page purpose / hero. Not duplicated as HES chrome.)

---

## Painted slots (Living Store at capture)

| Slot | Present | Owner (View Details) |
|------|---------|----------------------|
| حالة المتجر | ✓ | `#communication` (contact-blocked health story) |
| أهم قرار اليوم | ✓ | `#workspace` |
| أبرز المنتجات | ✓ | `#workspace` |
| السلال | omitted (no ops signal) | — |
| التواصل | ✓ | `#communication` |

Desktop and Mobile: **identical section meaning**.

---

## Automated checks (all green)

- No bare count badges  
- No eyebrow / lede / ownership footer  
- No duplicate situation-item View Details  
- No forbidden status tags (`القرار الأهم` / `منتج` / `مكتمل اليوم`)  
- No count-first summaries  
- ≤5 View Details  
- Health href ∈ `{#workspace,#communication,#settings}`

---

## STOP

Await explicit **HOME APPROVED** before any further Dashboard work.
