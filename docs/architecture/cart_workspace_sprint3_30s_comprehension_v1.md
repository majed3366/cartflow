# Cart Workspace Sprint 3 — 30-Second Comprehension Report V1

**Date (UTC):** 2026-07-12  
**Method:** Structured walkthrough of `#workspace` after `POST /api/cart-workspace/v1/demo-seed` (flag ON, internal).  
**Participants (roles):** Product owner · Developer · Unfamiliar reviewer *(fill names on live session)*

---

## Protocol

1. Enable `CARTFLOW_CART_WORKSPACE_V1=true` for internal session only.  
2. Open dashboard → **مساحة القرار**.  
3. Click **تجهيز أمثلة للفهم**.  
4. Do **not** coach. Ask the five questions. Cap ~30 seconds observation before answering.

---

## Questions & expected answers

| # | Question | Expected natural answer |
|---|----------|-------------------------|
| 1 | ما الذي يحتاج انتباهك؟ | بطاقة VIP و/أو بطاقة الخصم — ليس قائمة سلال |
| 2 | لماذا؟ | لأن الأتمتة توقفت وتحتاج حكماً / VIP |
| 3 | ماذا يفعل CartFlow؟ | يعمل الآن / يتابع الاسترداد (Zone C) |
| 4 | ماذا يحدث بعد أن تتصرف؟ | تعود المتابعة لـ CartFlow (نص البطاقة + هدوء بعد الزر) |
| 5 | ماذا يمكنك تجاهله بأمان؟ | ما ليس بطاقة قرار؛ الردود التي يجيبها النظام؛ النتائج المكتملة كملخص فقط |

---

## Session record

| Participant | Q1 | Q2 | Q3 | Q4 | Q5 | Understood in ≤30s? |
|-------------|----|----|----|----|----|---------------------|
| Product owner | _ | _ | _ | _ | _ | ☐ |
| Developer | _ | _ | _ | _ | _ | ☐ |
| Unfamiliar | _ | _ | _ | _ | _ | ☐ |

**Pass criterion:** Majority answers match expected meaning without training; quote success:

> «فهمت ما الذي يحتاج قراري، وفهمت أن CartFlow يتولى الباقي.»

**Fail if:** «أين السلال؟ وأين أبدأ؟»

---

## Engineering self-check (pre-session)

Seeded projection includes Zone A + Zone B + Zone C reassurance + Zone D count — verified by `test_seed_comprehension_set_zones`.

---

**Status:** Template ready — record live session answers before closing Sprint 3 Product gate.
