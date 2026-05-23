# Merchant dashboard — top bar + contextual sidebar (v1)

UI-only shell restructure. All hashes and pages unchanged.

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│ CartFlow │ حالة الإعداد │ الرئيسية السلال التواصل الإعدادات │ 🔔 👤 │
├──────────┬──────────────────────────────────────────────────┤
│ (سياقي)  │  عنوان الصفحة                                   │
│ الكل     │  ─────────────────────────────────────────────  │
│ تدخل     │  محتوى (تمرير واحد للصفحة)                      │
│ …        │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

- **Top bar:** where am I (section + store setup status).
- **Sidebar:** what can I do in this section (hidden/minimal on الرئيسية).
- **Main:** single scroll on `.ma-content-root` only (`body { overflow: hidden }`).
- **Top bar:** CartFlow green (`64px`), fixed.
- **Sidebar:** fixed right, no visible internal scrollbar.

## Hash compatibility

`#home`, `#carts`, `#followup`, `#completed`, `#vip`, `#messages`, `#reasons`, `#trigger-templates`, `#templates` (alias), `#widget`, `#whatsapp`, `#settings` — all preserved.
