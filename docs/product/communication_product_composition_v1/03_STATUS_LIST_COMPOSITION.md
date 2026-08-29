# 03 — Status List Composition

The list is a **communication event / status feed**, not a thread inbox.

Each row uses existing fields only:

- who: `phone_masked` (or masked follow-up phone)
- what: `message_type_ar` / «رد العميل»
- latest status: delivery outcome or يحتاج متابعتك
- when: `time_ar` / `replied_at`
- CartFlow handling: quiet chip «CartFlow يتابع»
- merchant required: chip «يحتاج متابعتي» only if follow-up row matches

Sort: needs → blocked → automated → waiting → terminal.

Filters (operational, not folders): يحتاج متابعتي / جاري / السجل.

No unread counts. No customer names. No invented last-message previews.
