# CartFlow Active vs Legacy Inventory

**Date (UTC):** 2026-05-27  
**Scope:** Architecture freeze — classify surfaces without deleting anything.

**Classification key**

| Tag | Meaning |
|-----|---------|
| **ACTIVE** | Production path; new features must align here |
| **LEGACY** | Still reachable; rollback, dev harness, or duplicate semantics |
| **DEPRECATED** | Documented for removal; avoid new dependencies |
| **UNKNOWN** | Needs owner confirmation before change |

---

## 1. Widget & storefront

| Component | Tag | Notes |
|-----------|-----|-------|
| `static/widget_loader.js` + `CARTFLOW_WIDGET_RUNTIME_V2` | **ACTIVE** | Default embed path |
| `static/cartflow_widget_runtime/*` | **ACTIVE** | V2 flows, triggers, API, UI |
| `static/cart_abandon_tracking.js` | **ACTIVE** | Session/cart IDs, abandon POST |
| `static/cartflow_return_tracker.js` | **ACTIVE** | Return-to-site POST |
| `static/cartflow_widget.js` (monolith) | **LEGACY** | Only via `__CARTFLOW_ALLOW_LEGACY_WIDGET` or dev harness |
| `GET /dev/widget-test*` | **LEGACY** | `ENV=development` only; loads monolith directly |
| `static/cartflow_demo_panel.js` | **ACTIVE** (demo) | Demo store cart page only |
| `static/cartflow_demo_guide.js` | **ACTIVE** (demo) | Demo UX overlay |

---

## 2. Demo & test paths

| Path | Tag | Store slug | Identity |
|------|-----|------------|----------|
| `/demo/store`, `/demo/store2` | **ACTIVE** (sandbox) | `demo` / `demo2` | Public sandbox |
| `?merchant_activation=1` on `/demo/store` | **ACTIVE** | Authenticated merchant `zid_store_id` | Test-widget contract + reset |
| `/dashboard/test-widget` | **ACTIVE** | Redirects to merchant activation URL | Same as above |
| `?reset_demo=1` | **ACTIVE** | Demo reset script in `demo_store.html` | Clears session/cart LS |
| `?fresh=1` + `cf_test_phone` | **LEGACY** | Demo PI fresh session (`demo_pi_fresh_session.py`) | Seeds `price_high`; parallel to activation reset |
| `coerce_cart_event_store_slug` fallback `"default"` | **LEGACY** | When no auth and empty payload | Avoid for merchant tests |
| `POST /api/test-widget/new-lifecycle` | **ACTIVE** | Merchant test reset API | Clears runtime cache for old `recovery_key` |
| `GET /dev/test-widget-identity-trace` | **ACTIVE** | Dev verification | Read-only |

---

## 3. API & recovery execution

| Surface | Tag | Notes |
|---------|-----|-------|
| `POST /api/cart-event` | **ACTIVE** | Central ingest |
| `POST /api/cartflow/reason` | **ACTIVE** | Widget reason + schedule arm |
| `POST /api/cartflow/assist-handoff` | **ACTIVE** | Audit-only handoff |
| `POST /api/cart-recovery/reason` | **LEGACY** | Layer D alternate; some integrations may still use |
| `POST /api/conversion` | **ACTIVE** | Demo + explicit conversion |
| `RecoverySchedule` + DB scanner | **ACTIVE** | Durable delayed send |
| In-memory `_session_recovery_*` | **ACTIVE** (cache) | Not durable; see session truth audit |

---

## 4. Truth & classification (duplicate surfaces)

| Module | Tag | Role |
|--------|-----|------|
| `recovery_truth_timeline_v1` | **ACTIVE** | Durable proven transitions |
| `merchant_cart_row_classifier` | **ACTIVE** | Tab buckets + `merchant_status_label_ar` |
| `customer_lifecycle_states_v1` | **ACTIVE** | Chip + explanation + archive UX |
| `merchant_recovery_lifecycle_truth` | **LEGACY** (enrichment) | Extra fields; not primary label owner |
| `cartflow_lifecycle_guard` | **ACTIVE** | Send-time precedence (purchase > reply > return > …) |
| `lifecycle_intelligence` | **ACTIVE** (observe) | Decision observe hooks; shadow compare |
| `cartflow_lifecycle_truth` | **LEGACY** | Shadow / migration compare at observe sites |
| `main._NORMAL_RECOVERY_PHASE_ORDER` | **LEGACY** (display) | Phase keys for older dashboard copy |
| `_normal_recovery_coarse_status` | **LEGACY** | Coarse bucket; classifier partially supersedes |

**Duplicate classifiers:** Layer A (classifier) vs Layer B (lifecycle v1) vs phase/coarse strings — **frozen rule:** lifecycle v1 wins for visible chip when attached.

---

## 5. Timeline vs logs vs behavioral

| Signal | Tag | Dashboard use |
|--------|-----|-----------------|
| `recovery_truth_timeline_events` | **ACTIVE** | Sent / reply / continuation proof |
| `CartRecoveryLog.status` | **ACTIVE** | Fallback sent, return logs, skips |
| `AbandonedCart.cf_behavioral` | **ACTIVE** (secondary) | Return hints; not reply proof |
| `_session_recovery_sent` | **LEGACY** (cache) | Gates only; not dashboard |

---

## 6. Archive & terminal

| Component | Tag |
|-----------|-----|
| `merchant_cart_lifecycle_archive_v1` | **ACTIVE** |
| `purchase_truth_records` | **ACTIVE** |
| `lifecycle_closure_records_v1` | **ACTIVE** (closure audit) |
| Auto-archive when exhausted (classifier) | **ACTIVE** (display); persistence via archive service |

---

## 7. Dashboard

| Asset | Tag |
|-------|-----|
| `GET /api/dashboard/normal-carts` | **ACTIVE** |
| `static/merchant_dashboard_lazy.js` | **ACTIVE** |
| `static/merchant_app.css` lifecycle/archive styles | **ACTIVE** |
| `static/cartflow_dashboard_messages.js` | **UNKNOWN** | Cheerful tone LS; verify product use |
| Legacy dashboard templates (non-lazy) | **LEGACY** | Redirects to lazy shell |

---

## 8. Unused / orphan candidates (do not delete — see `candidate_remove.md`)

| Item | Tag | Risk |
|------|-----|------|
| `static/cartflow_widget.js` full monolith | **DEPRECATED** (target) | Rollback + dev harness |
| `GET /dev/widget-test` | **LEGACY** | Dev-only |
| `demo_pi_fresh` link without `merchant_activation` | **LEGACY** | Overlaps activation reset |
| `routes/demo_panel.py` demo logs API | **ACTIVE** (demo panel only) | Not merchant dashboard |
| Duplicate reason route `cart_recovery_reason.py` | **LEGACY** | External integrations |
| `cartflow_dashboard_messages.js` if unused in lazy shell | **UNKNOWN** | Verify before removal |

---

## 9. Test files (representative)

| Area | Tag | Files |
|------|-----|-------|
| Timeline / classifier / lifecycle v1 | **ACTIVE** | `test_recovery_truth_timeline_v1.py`, `test_merchant_cart_row_classifier_e2e.py`, `test_customer_lifecycle_states_v1.py` |
| Legacy widget static reads | **LEGACY** | Tests that `read_text(cartflow_widget.js)` |
| V2 baseline lock | **ACTIVE** | `test_v2_widget_baseline_lock.py`, `test_demo_behavioral_navigation.py` |
| Lifecycle shadow / intelligence | **LEGACY** (guard rails) | `test_cartflow_lifecycle_truth_v1.py`, `test_lifecycle_intelligence.py` |

---

## 10. Frozen decisions (this audit)

1. **New dashboard labels** → extend `customer_lifecycle_states_v1` + classifier bucket; do not add a third classifier.
2. **New progression proof** → write `recovery_truth_timeline_v1` first; log mapping from `CartRecoveryLog` second.
3. **Merchant test** → always `merchant_activation=1` + authenticated store slug; never rely on `demo` fallback.
4. **Reply / engaged** → timeline-required; return-to-site never implies reply.

**See also:** `docs/widget_legacy_cleanup_audit.md`, `docs/v2_widget_baseline_lock.md`, `docs/cartflow_lifecycle_alias_map.md`.
