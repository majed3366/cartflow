# Diagnostic Reasoning Foundation V1 — CEO Home Review Pack

**Status:** Awaiting production deploy + Home-only CEO Review  
**Date (UTC):** 2026-07-27  
**Scope:** Home only (`/dashboard#home`)

## What changed

CartFlow no longer invents a cause from a shipping-stage observation.

If evidence cannot distinguish cost vs delivery time vs options:

> يغادر العملاء بعد خطوة الشحن، لكن الأدلة الحالية لا تكفي لتحديد ما إذا كان السبب تكلفة الشحن أو مدة التوصيل أو خيارات الشحن المتاحة.

Supported shipping cost (only when subtype evidence distinguishes it):

> الأدلة تشير إلى أن تكلفة الشحن هي السبب الأكثر احتمالاً لمغادرة العملاء.

## Architecture

Background → `diagnostic_snapshots` → `merchant_publication_v1` → Home read-only

## STOP

Await **HOME APPROVED**. No other dashboard page work.
