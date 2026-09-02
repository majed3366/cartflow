# Merchant IA & Ownership Reconciliation V3 — Report

**Base SHA:** `9a5a6acf4b606629c5380c3d8b7fa9b2c96f9d15`  
**Candidate SHA:** `68e30239726ffd777c3bbedd0512da0f7030e280`  
**Direct parent:** `9a5a6acf4b606629c5380c3d8b7fa9b2c96f9d15`  
**Deploy:** NOT performed

## Proven ownership

| Concern | Canonical owner |
|---------|-----------------|
| Delay / attempts / reason templates | Settings → سياسة الاسترجاع (`#ma-tpl-root`) |
| Sent history / bodies / lifecycle | Communication |
| Current package (read-only) | Account drawer + Settings → المتجر (`#ma-subscription-root`) |
| VIP cart minimum value | Settings → سياسة السلال المهمة (`vip_cart_threshold`) |

## Legacy route

| Field | Value |
|-------|-------|
| Previous merchant-facing link | `/dashboard?cf_ui=v1#trigger-templates` |
| Renderer | Merchant UI V1 (`merchant_app.html` / legacy cascade) |
| Canonical destination | `#trigger-templates` → Settings recovery panel (V2) |
| Merchant-reachable from V2 | **NO** (handoff removed; in-V2 button only) |
| Legacy rollback route | Remains available via explicit `?cf_ui=v1` (not linked) |

## Package truth

| Field | Value |
|-------|-------|
| Source | `/api/merchant/subscription` (+ Settings store card) |
| Catalog API | `/api/merchant/plans-catalog` exists (read-only) |
| Merchant comparison UI | Not shipped in V2 — no fake pricing cards |
| Upgrade/downgrade | **BLOCKED_BY_COMMERCIAL_CONTRACT** |

## «العتبة» semantics

`vip_cart_threshold` = minimum cart value for VIP / important-cart follow-up.  
Merchant label: **الحد الأدنى لقيمة السلة**.

## Account context

Drawer paints `store_name` from `/api/merchant/session-identity` and plan from `/api/merchant/subscription`. Destinations: الملف / الباقة → Settings store panel (no Settings ownership duplication).

## Evidence

`docs/product/merchant_ia_ownership_reconciliation_v3/evidence/`
