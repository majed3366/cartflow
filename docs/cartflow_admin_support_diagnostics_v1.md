# Admin Support Diagnostics v1

**Date (UTC):** 2026-05-19  
**Commit:** `feat: add admin support diagnostics v1`  
**Scope:** Read-only diagnostics for admin/support — no recovery, WhatsApp, widget, lifecycle, or merchant dashboard changes.

---

## API

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/admin/support-diagnostics` | Admin session (`CARTFLOW_ADMIN_PASSWORD`) |
| `GET` | `/admin/support-diagnostics/ui` | Admin HTML UI |

**Query:** `store_slug=`, optional `session_id=`, optional `recovery_key=`

**Response:** `diagnostic` object with `summary`, `severity`, `issue_type`, `likely_cause`, `evidence[]`, `recommended_action`, `merchant_safe_message`; plus `context` (onboarding, delivery truth, template enforcement).

---

## Supported issue types (initial)

| issue_type | Typical evidence |
|------------|------------------|
| `blocked_template_required` | `CartRecoveryLog`, template enforcement |
| `whatsapp_failed` | Log / schedule + `recovery_failure_explanation_v1` |
| `sent_real` / `mock_sent` / `queued` | `CartRecoveryLog` |
| `delivered_to_customer` / `read_by_customer` | `whatsapp_delivery_truth` |
| `recovery_waiting_delay` | `RecoverySchedule` due_at |
| `recovery_stopped_purchase` | `purchase_truth_records` |
| `recovery_stopped_return` | `skipped_anti_spam` / `returned_to_site` |
| `missing_phone` / `missing_reason` | Log / schedule skip statuses |
| `provider_not_ready` / `store_not_ready` | `evaluate_onboarding_readiness` |
| `activation_not_complete` | Onboarding milestones |
| `cart_not_visible` | No `AbandonedCart` for session |

---

## Module

`services/admin_support_diagnostics_v1.py` — `build_admin_support_diagnostics()`, `list_support_question_inventory()`.
