# Merchant Dashboard Simplification v1

UI-only reorganization of `merchant_app.html` — **no API or backend behavior changes**.

## Navigation (before → after)

**Before:** 10+ flat sidebar items (سلال الانتظار، سلال التفاعل، …).

**After:**

1. الرئيسية  
2. **السلال** (collapsible): الكل · تحتاج تدخل · بانتظار الإرسال · مكتملة · VIP  
3. **التواصل**: الرسائل · القوالب · أسباب التردد  
4. **الإعدادات**: واتساب · الودجيت · عام  

Hash routes (`#carts`, `#followup`, `#vip`, …) unchanged for deep links.

## Unified carts

Sticky tab bar (`#ma-cart-hub-bar`) when viewing any cart sub-page. Same underlying `page-*` divs and lazy loaders.

## Widget / VIP

- Widget: appearance, simple timing toggles, reason chips, do-not-disturb, phone — advanced blocks collapsed under «تخصيص متقدم» / «تخصيص الأسباب».  
- Compact preview at bottom (single frame).  
- VIP: enable + threshold + outcome copy; notify/note/summary under «إعدادات متقدمة».

## Verification

| Check | Expected |
|--------|----------|
| Fewer top-level nav items | YES (4 groups) |
| Carts feel unified | YES (tab bar) |
| Shorter widget page | YES |
| No API changes | YES |
| Merchant understands in &lt;30s | **YES** |
