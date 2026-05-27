# CartFlow Dead Code & Cleanup Candidates

**Date (UTC):** 2026-05-27  
**Scope:** Architecture audit — **DO NOT DELETE** from this document alone. Each item needs explicit approval and QA.

**Risk levels**

| Level | Meaning |
|-------|---------|
| **safe** | Likely unused or dev-only; low blast radius after grep + test |
| **review** | Reachable in some paths; needs stakeholder sign-off |
| **danger** | Rollback, integrations, or truth-path; do not remove without migration |

---

## 1. Routes

| Route / handler | Risk | Rationale |
|-----------------|------|-----------|
| `GET /dev/widget-test`, `/dev/widget-test/cart` | **review** | Legacy monolith harness; dev-only |
| `GET /demo/cart` (alias) | **safe** | Redirects to store paths; verify analytics |
| `POST /api/cart-recovery/reason` (`routes/cart_recovery_reason.py`) | **danger** | Alternate reason API; external callers unknown |
| `GET /demo/cartflow/*` (`routes/demo_panel.py`) | **review** | Demo panel only; not merchant prod |
| `GET /dev/*` bulk (~40 endpoints in `main.py`) | **review** | Many are QA; gate already `ENV=development` for most |
| `GET /api/recover/r` | **review** | Short link resolver; verify marketing use |
| `POST /dev/cartflow-delay-test` | **safe** | Dev delay experiments |

---

## 2. JavaScript / static

| File / symbol | Risk | Rationale |
|---------------|------|-----------|
| `static/cartflow_widget.js` (~8k+ lines) | **danger** | Legacy rollback + tests read file |
| `widget_loader.js` legacy branch (`__CARTFLOW_ALLOW_LEGACY_WIDGET`) | **review** | Needed until embed migration complete |
| `cartflow_widget_runtime/cartflow_widget_legacy_bridge.js` | **review** | May be no-op bridge; verify imports |
| `static/cartflow_dashboard_messages.js` | **review** | Grep lazy dashboard for inclusion |
| `cartflowFreshSessionForDelayTest` (`cart_abandon_tracking.js`) | **safe** | DevTools-only helper |
| `demo_pi_fresh` client block in `demo_store.html` | **review** | Overlaps merchant activation reset |
| Duplicate `postReason` paths in legacy widget | **danger** | If monolith removed without V2 parity |

---

## 3. Python services (duplicate / shadow)

| Module | Risk | Rationale |
|--------|------|-----------|
| `services/cartflow_lifecycle_truth.py` | **review** | Shadow compare at observe; remove only after v1 unified read |
| `services/lifecycle_intelligence.py` observe-only paths | **review** | Still wired from `main._observe_lifecycle_intelligence_decision` |
| `services/merchant_recovery_lifecycle_truth.py` duplicate labels | **review** | Enrichment; consolidate into lifecycle v1 later |
| `main._NORMAL_RECOVERY_PHASE_ORDER` display-only | **safe** | Superseded by lifecycle v1 for chips |
| `_normal_recovery_coarse_status` | **review** | Some rows may still expose `coarse` field |

---

## 4. Timeline & log statuses (unused or legacy strings)

| Status / alias | Risk | Rationale |
|----------------|------|-----------|
| `skipped_delay` (vs `skipped_delay_gate`) | **safe** | Alias map marks LEGACY |
| Timeline statuses not in `CANONICAL_ORDER` | **review** | DB may contain historical rows |
| `CartRecoveryLog` statuses only used in old VIP paths | **review** | Audit before filter removal |

---

## 5. Classifiers & dashboard

| Item | Risk | Rationale |
|------|------|-----------|
| Second label from classifier when lifecycle attached | **safe** | Dead UI if JS only reads lifecycle fields |
| `merchant_status_label_ar` without lifecycle attach on VIP rows | **review** | Verify VIP table path |
| Duplicate filter logic in `merchant_dashboard_lazy.js` vs classifier `visible_tabs` | **review** | Consolidation opportunity |

---

## 6. Demo / fallback paths

| Path | Risk | Rationale |
|------|------|-----------|
| `store_slug=default` in `coerce_cart_event_store_slug` | **danger** | Last-resort fallback; merchant tests must not hit |
| Public `demo` / `demo2` without activation | **ACTIVE** | Sandbox; keep |
| `reset_demo=1` without `merchant_activation` | **review** | Public demo reset |
| `services/demo_pi_fresh_session.py` | **review** | Parallel to test-widget identity |

---

## 7. Tests (orphan / redundant)

| Test file | Risk | Rationale |
|-----------|------|-----------|
| Tests that only `read_text('cartflow_widget.js')` for substring | **review** | Keep until monolith removed |
| `test_abandonment_reason_behavior_final.py` legacy branches | **review** | Now targets V2; prune legacy sections carefully |
| Duplicate e2e for same classifier behavior | **safe** | Merge in dedicated cleanup PR |
| `test_cartflow_lifecycle_truth_v1.py` shadow tests | **review** | Needed while shadow compare active |

---

## 8. Files possibly dead (grep before action)

| Path | Risk | Action |
|------|------|--------|
| `scripts/_patch_*.py` (untracked workspace scripts) | **safe** | Not in repo product path; do not commit |
| `services/cartflow_identity.py` | **review** | Small helper; verify importers |
| `services/decision_engine.py` | **review** | May be admin-only |
| `static/merchant_trigger_templates.js` | **review** | Dashboard trigger UI |

---

## 9. Recommended cleanup order (future PRs)

1. **safe:** Remove stale docs narratives; merge duplicate tests; drop unused coarse-only UI fields.  
2. **review:** Consolidate `demo_pi_fresh` into merchant activation reset; dev widget-test V2 parity route.  
3. **review:** Retire `cartflow_lifecycle_truth` shadow after unified read model.  
4. **danger:** `widget_loader` legacy branch removal (requires embed audit).  
5. **danger:** `cartflow_widget.js` deletion (last).

---

## 10. Explicit non-candidates (keep)

- `recovery_truth_timeline_v1.py`
- `customer_lifecycle_states_v1.py`
- `merchant_cart_row_classifier.py`
- `merchant_cart_lifecycle_archive_v1.py`
- `cartflow_session_truth.py` (until cache fully optional)
- `merchant_test_widget_store_v1.py` + identity contract in `main.py`

---

**No files were deleted in the architecture freeze task.** This list is input for future cleanup PRs only.
