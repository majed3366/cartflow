# Merchant Findings Review Lab V1

**Status:** Ready for Product acceptance  
**Route:** `/dev/business-findings-review`  
**Date (UTC):** 2026-07-17  

## Purpose

Evaluate whether Business Findings Engine V1 produces findings a real merchant would value.

This is **not** Home.  
This is **not** merchant navigation.  
This is **not** production integration.

## How to open

```
/dev/business-findings-review
/dev/business-findings-review?source=fixture&store=demo
```

Optional: `source=db` attempts a bounded live load (falls back to fixture if sparse).

## What the page shows

One card per finding — merchant language only:

1. Title  
2. Summary  
3. Why this matters  
4. Suggested next step  
5. Confidence badge (Arabic)  
6. Supporting evidence (collapsed)

Under each card: Product-only review questions (Useful / Wow classification).

## Acceptance gate (on-page scoreboard)

- ≥ 5 findings classified **Useful** or **Wow**  
- ≥ 3 findings classified **Wow**  
- Every finding classified  

Only after Product approval may findings become eligible for Home selection.

## STOP

Do not connect to Home.  
Do not redesign Home.  
Do not treat passing tests as Product approval.
