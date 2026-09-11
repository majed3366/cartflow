# Paid Event → OrderEconomicFact End-to-End V1

**Status:** DSE CLOSED FOR `74389634`; PIPE READY; E2E WRITE WAITING ON A NEW REAL PAID ORDER  
**Date (UTC):** 2026-09-11  
**General release:** NO  
**Level 3:** NO

## Root cause for `74389634`

Zid store `3121837` / `cartflow-42b491` had **zero** webhook subscriptions. The paid transition was never delivered to CartFlow. Independently, `/webhook/zid` required undocumented `X-Zid-Signature` + `ZID_WEBHOOK_SECRET` (unset), so a documented Zid Basic Auth delivery would 401 before persist.

## Classification

**A — EVENT NEVER SENT / NOT SUBSCRIBED**

Provider historical redelivery: **NO** (retries on failure only; no replay of a never-subscribed event).

## Minimal correction

Accept documented Zid `Authorization: Basic` on `/webhook/zid`. Then subscribe `order.payment_status.update` → `https://smartreplyai.net/webhook/zid`. No new env. No schema change. Scheduler untouched.

A new cheap paid Zid order is required for E2E write proof. Do not fabricate `74389634`.
