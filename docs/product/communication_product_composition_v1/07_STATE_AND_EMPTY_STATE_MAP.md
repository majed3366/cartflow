# 07 — State and Empty-State Map

| State | Source | Orientation / list |
|-------|--------|--------------------|
| No history | empty messages + empty followups | «لا توجد أحداث تواصل بعد» |
| Nothing needs merchant | followups.length = 0 | calm; needs filter empty is valid |
| All automated | `recovery_schedules` > 0, needs = 0 | «CartFlow يتابع تلقائياً» |
| Waiting for customer | delivered / sent, no follow-up | quiet row |
| Channel blocked | `communication_condition.constrained` | «التواصل غير جاهز» + ضبط التواصل |
| Failed send | delivery failed class / copy | quiet failed row, not يحتاج متابعتي |
| No-phone | `no_phone_total` | calm fact; Carts link; not merchant-response |
| Purchased / terminal | lifecycle completed / purchased | history only; no CTA |
| Partial API failure | fetch reject | «تعذّر تأكيد حالة التواصل» — no false calm |
