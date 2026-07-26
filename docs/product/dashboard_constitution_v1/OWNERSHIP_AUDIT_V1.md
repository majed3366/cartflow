# Dashboard Ownership Audit V1

**Date (UTC):** 2026-07-26  
**Law:** Product Constitution V1 + Dashboard Constitution Implementation V1  
**Rule:** Nothing may belong to multiple pages.

## Matrix

| Component | Current page | Constitutional owner | Action |
|-----------|--------------|----------------------|--------|
| HES store health / top decision / product / carts / comm teasers | Home | Home | **Keep** |
| HES View Details CTAs | Home | → owner page | **Keep** |
| Home month KPI wall `#home-month` | Home | — | **Remove** (nav + page hidden) |
| Home setup `#home-setup` | Home | Settings | **Move** (sidebar → Settings) |
| ORV / MEIF / ECC / Pulse Home painters | Home | — | **Remove** (already suppressed when HES owns) |
| Workspace decision cards (why / evidence / action / impact) | Workspace | Workspace | **Keep** |
| Workspace category landscape | Workspace | Workspace | **Keep** (Arabic labels only) |
| Products situation cards → Workspace | Products | Products | **Keep** |
| Products page hero “مواقف العمل” | Products | Products | **Fix language** |
| Carts operational tables / filters / next action | Carts | Carts | **Keep** |
| Carts attention hero / shared question-first hero | Carts | Carts | **Fix** → operational question only |
| Carts publication systemic business decision | Carts | Workspace | **Remove** (link only, no decision text) |
| MEIF carts “حقيقة” trust chip | Carts | — | **Remove** |
| VIP threshold form on VIP carts | Carts | Settings | **Keep** for this pass (move tracked) |
| Communication status + facts | Communication | Communication | **Keep** + action paths |
| Reasons recommendations | Communication | Workspace | **Remove** guidance block |
| Templates / WhatsApp / Widget / Plans | Settings / Comms | Settings / Communication | **Keep** (working) |
| Automation mode “للتذكير فقط” | Settings | — | **Remove** (hidden) |
| Shopify قريباً | Settings | — | **Remove** |
| Settings diagnostics in merchant nav | Settings | Admin/Dev | **Remove** from merchant sidebar |
| Inactive notify 🔔 | Shell | — | **Remove** |
| Empty hash → Workspace | Shell | Home | **Fix** → `#home` |

## One question per page

| Page | Question |
|------|----------|
| Home | ماذا يجب أن أعرف الآن عن متجري؟ |
| Workspace | أي قرار يجب أن أتخذه، ولماذا؟ |
| Products | ماذا يحدث لمنتجاتي؟ |
| Carts | ما حالة كل سلة؟ |
| Communication | ماذا حدث في التواصل مع العملاء؟ |
| Settings | كيف أضبط CartFlow؟ |
