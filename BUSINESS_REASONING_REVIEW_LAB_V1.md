# Business Reasoning Review Lab V1

**Status:** Ready for Product acceptance  
**Route:** `/dev/business-reasoning-review`  
**Date (UTC):** 2026-07-18  

## Purpose

Evaluate whether Business Reasoning Engine V1 produces merchant-level thinking that deserves to become the foundation of CartFlow.

This is **not** Home.  
This is **not** Products.  
This is **not** Knowledge.  
This is **not** an AI evaluation.  
This is **not** merchant navigation.

No merchant surface may consume Business Reasoning until this review is approved.

## How to open

```
/dev/business-reasoning-review
/dev/business-reasoning-review?source=fixture&store=demo
```

Standalone host (optional):

```
python scripts/_serve_business_reasoning_review_lab_v1.py
```

Default: `http://127.0.0.1:8766/dev/business-reasoning-review?source=fixture&store=demo`

Optional: `source=db` runs Findings from a bounded live load, then Reasoning (falls back to fixture if sparse).

## Data source (only)

Approved Business Findings → Business Reasoning Engine → Merchant Guidance

- No direct Truth  
- No direct Evidence  
- No experimental AI  

## What the page shows

One card = one business decision — merchant language only:

1. Headline  
2. Business Meaning  
3. Merchant Priority  
4. Expected Impact  
5. Confidence  
6. Reasoning Type (merchant label)  
7. Observed / Likely / Unknown  
8. Supporting Findings (collapsed by default)

Under each card: Product-only review questions.

## Review questions (Product only)

1. Does this reasoning create a real business decision?  
2. Is this more valuable than reading the Findings separately?  
3. Would an experienced merchant trust this reasoning?  
4. Does this reasoning save merchant thinking time?  
5. Classification: Good / Useful / Wow  

## Wow standard

A Wow reasoning should make the reviewer think:

> I would not have connected these findings myself.

Examples of Wow:

- WhatsApp restores customer interest, but shipping still prevents purchase.  
- Recovery is working; conversion is not.  
- The real bottleneck is before messaging starts.  

Not Wow (those are Findings):

- Shipping appears often.  
- Customers returned.  
- Product has low conversion.  

## Acceptance gate (on-page scoreboard)

- ≥ 5 reasoning cards classified **Useful** or **Wow**  
- ≥ 3 reasoning cards classified **Wow**  
- Every reasoning card classified  
- Every reasoning adds value beyond the original Findings  
- Reasoning reduces merchant decision effort  
- Reasoning feels like commercial thinking, not data summarization  

Only after Product approval may Business Reasoning become the canonical decision layer for merchant-facing surfaces.

## Display rules

Do **not** expose on the page:

- Business Reasoning Engine  
- Finding Registry  
- Relationship Graph  
- Rule Engine  
- Pattern Match  
- Internal IDs  
- Evidence Objects  
- Contracts  

## STOP

Do not connect Business Reasoning to:

- Home  
- Products  
- Customers  
- WhatsApp  
- Knowledge  
- Reports  

until Product approval is complete.
