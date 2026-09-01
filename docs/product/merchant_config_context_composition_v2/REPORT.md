# Merchant Configuration & Context Composition V2 — Report

**Base SHA:** `652ad169c56d13791417e1f9d2a98ff640e0b560`  
**Candidate SHA:** uncommitted (worktree dirty atop base)  
**Direct parent:** `652ad169c56d13791417e1f9d2a98ff640e0b560`  
**Deploy:** NOT performed

## Proven outcomes

| Area | Result |
|------|--------|
| Home الملخص | Independent `renderSummaryView()` via ctx `summary`; overview `render()` has no recovery strip |
| Home recovery truth | Operational KPI only (`merchant_kpi_recovered_fmt`, `merchant_kpi_revenue_fmt`, period label) |
| Recovery reasons | Canonical tags from `services/store_reason_templates.py`: price, shipping, warranty, thinking, quality, delivery, other |
| Reason-specific templates | `#ma-tpl-root` lazy-loaded on recovery panel; `trigger-templates` hash → recovery (not communication) |
| Historical immutability | Communication reads persisted log bodies; Settings edits `Store.reason_templates_json` only |
| الودجيت rename | Settings ctx + panel title; no remaining `title: "التجربة"` in V2 settings |
| Widget color | UI `#mw-widget-color` → POST recovery-settings `widget_primary_color` → `Store.widget_primary_color` → `cartflow_widget.js` runtime |
| Widget timing | UI `#mw-hes-sec` → `widget_trigger_config.hesitation_after_seconds` → public config → widget arm delay |
| Widget intent | UI `#mw-hes-cond` → `hesitation_condition` (inactivity / exit_intent / …) → public config → widget trigger gate |
| Emoji forms | 🟢/💼/🔵 removed from WhatsApp mode titles; CF marker `ma-wa-mode-marker` instead |
| mock_sent root cause | Store Reality Simulator writes `[SRS] mock_sent — no provider call` to `CartRecoveryLog.message`; leaked via messages API |
| Production isolation | Presentation fix: `merchant_message_presentation_v1.py` + comms JS filter; DB truth preserved |
| Carts sidebar | `ctxCounts()` filter totals appended when authoritative |
| Communication sidebar | needs/active/all counts from `ctxCounts()` |
| Settings sidebar | `ctxHint()` readiness hints per area |

## mock_sent classification

**Root cause:** DATA/PRESENTATION ISOLATION FAILURE — simulator ingress (`services/store_reality_simulator/ingress_adapter_v1.py`) persists internal marker text as `CartRecoveryLog.message`; merchant messages endpoint surfaced raw body.

**Fix class:** Presentation contract (not CSS hide, not DB delete). Internal status `mock_sent` remains for ops/KPI; merchant-visible body empty when internal-only.

## Gate

56 passed — `test_merchant_config_context_composition_v2.py` + refinement + whatsapp mode + controlled visual fix.

## Real-device review

Structural/contracts PASS. Founder visual review at 390px RTL + 1280px desktop **PENDING** (requires authenticated merchant session).
