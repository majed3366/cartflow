# Home Executive Question Registry V2

**Document type:** Constitutional merchant question registry for Home  
**Status:** **Approved / Locked — Constitutional**  
**Date (UTC):** 2026-07-19  
**Ratified (UTC):** 2026-07-19 — [`HOME_EXECUTIVE_CONSTITUTION_V1.md`](HOME_EXECUTIVE_CONSTITUTION_V1.md)  
**Sits above:** [`COMMERCIAL_QUESTION_REGISTRY_V1.md`](COMMERCIAL_QUESTION_REGISTRY_V1.md) (CQ-* = platform answers; EQ-* = Home understanding jobs)

**STOP:** No implementation until Executive Home Implementation V1 is opened. No Commercial Knowledge Expansion.

---

## 1. Law

Home admits content only to answer an **EQ-*** question (or to disclose under one).  
CQ-* answers are fuel. They do not each become a Home section.

---

## 2. Primary executive questions (bands)

| ID | Merchant question | Band | Owns action? |
|----|-------------------|------|--------------|
| EQ-01 | Is my business healthy today? | E1 Business Health Today | No |
| EQ-02 | What decision should I make today? | E2 Decision of the Day | Yes (decision pointer) |
| EQ-03 | What is the highest-value action today? | E2 (paired with EQ-02) | Yes (single route) |
| EQ-04 | What opportunity am I about to miss? | E3 Biggest Opportunity Today | Optional route only |
| EQ-05 | What does CartFlow understand about my business today? | E4 Understanding | No |
| EQ-06 | Is confidence sufficient to act? | E5 Confidence to Act | No (may advise wait) |
| EQ-07 | What changed since yesterday? | E6 What Changed | No |

---

## 3. Disclosure questions (collapsed by default)

| ID | Merchant question | Depth |
|----|-------------------|-------|
| EQ-D1 | Why does this deserve attention now? | L1 |
| EQ-D2 | What happens if I ignore this? | L1 |
| EQ-D3 | How did CartFlow reach this understanding? | L2 |
| EQ-D4 | What evidence supports this? | L2 |
| EQ-D5 | Where do I go to act or investigate? | Route chip when E2/E3 active |

---

## 4. Forbidden as Home answers

Home must **not** treat these as answers to EQ-*:

- Internal counters / canonical field names / loader or pipeline states  
- Engine thinking as default-visible content  
- Implementation terminology  
- Raw evidence dumps without merchant meaning  

---

## 5. CQ → EQ fuel (illustrative)

| CQ family | Typical EQ home |
|-----------|-----------------|
| CQ-C01, CQ-G01 | EQ-02 / EQ-03 (E2) |
| CQ-P*, CQ-R*, CQ-W* | EQ-04 (E3) and/or EQ-05 (E4) |
| CQ-H*, CQ-T*, CQ-K*, CQ-D* | EQ-05 (E4), EQ-06 (E5) |
| Any with store-level pressure | EQ-01 (E1) as verdict input |
| Material day-over-day delta | EQ-07 (E6) |

Diversity and authenticity rules from CQ Registry V1 and Identity Foundation still apply to fuel — they do not grant automatic Home admission.

---

## 6. Success metric for Home

Home succeeds when the merchant can answer **EQ-01 through EQ-06** in ~30 seconds with merchant meaning — not when more cards, widgets, or CQ IDs are visible.
