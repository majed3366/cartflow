# 01 — V1 → V2 Communication Map

V1 is the source of communication truth. V2 is a new PageStage composition, not a visual copy.

| V1 behavior | Canonical truth contract | V2 presentation |
|-------------|--------------------------|-----------------|
| `#communication` status facts (`meif-communication-root` / CS banner) | `merchant_publication_v1.communication_condition` + MEIF `operational_truth` | Compact orientation (needs count / automated / blocked / calm) |
| `#messages` send log (`ma-messages-card`) | `GET /api/dashboard/messages` → `merchant_message_history_rows` | Status list rows (send / delivery / reply facts) |
| Message modal timeline | `communication_timeline` + `delivery_timeline` + `customer_reply_ar` | Detail «أحداث التواصل» (history, not chat) |
| Follow-up badge / rows | `GET /api/dashboard/followups` → `needs_merchant_followup` | يحتاج متابعتي only from this count |
| «يحتاج متابعة» chip (Gate 4) | `__maNeedsMerchantResponseCount` / follow-up rows | Same contract; orientation + row chip |
| ضبط التواصل → `#whatsapp` | constrained / `normal_forbidden` | Restrained `#settings` link when blocked |
| سجل الرسائل as second page | Alias `#messages` → `#communication` | One `#cf2-comms-root`; V2 hash `#communication` |
| Templates / reasons rails | Settings / Workspace ownership | Not on Communication |
| Follow-up WhatsApp CTA | Carts execution | Not rendered; handoff `#carts` |

Not carried from V1 UI:

- message avatar / dots chrome
- dual `#messages` page
- قالب / أسباب contextual rail
- `contact_wa_href` / فتح واتساب
- MEIF fact KPI grid (sent/delivered/replied/returned as dashboard cards)
