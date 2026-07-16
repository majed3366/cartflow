# INV-002 WP-6 Review — Timeline → Identity Authority

| Field | Value |
|-------|-------|
| Investigation ID | INV-002 |
| Work Package ID | WP-6 |
| Title | Timeline Consumer Migration (Execution Architecture Phase 4 — RV-B critical) |
| Branch | `feature/inv002-wp6` |
| Delivery commit | 2439969 (24399698bd7df60b0e01486c9c7b847579def539) |
| Author | Engineering (agent) |
| Reviewer | ☐ Architecture Board |
| Date submitted (UTC) | 2026-07-16 |

---

## 0. Frozen contract

From Reality Validation Readiness Matrix V1 (approved) + Execution Architecture Phase 4:

| Item | Contract |
|------|----------|
| **Purpose** | Timeline consumes MQIC — final critical surface before RV-B |
| **Surface** | Merchant Activity Timeline + MQIC-gated timeline evidence readers |
| **Not this WP** | Widget · Setup · Attach / Phase 5 · WhatsApp · Recommendations · global middleware |

---

## 1. Summary

Migrated **Timeline** to Platform Identity Authority MQIC:

- `timeline_consumer_v1.py` — Phase 3 session bind, identity scope, diagnostics, violation flags
- `merchant_timeline_v1.py` — Activity Timeline builder; MQIC-gated evidence readers
- Home `while_away` built via Timeline consumer (same MQIC as Home/Brief/Knowledge)
- `route_timeline_knowledge_v1` — Timeline routing; `store_slug` from MQIC only
- **`main.py` untouched**
- **Phase 5 Attach not started**

---

## 2. Delivery

| Field | Value |
|-------|--------|
| **Branch** | `feature/inv002-wp6` |
| **Final commit hash** | 2439969 (24399698bd7df60b0e01486c9c7b847579def539) |
| **ICT command** | `python -m pytest tests/identity_authority/ -q --tb=line` |
| **ICT result** | **66 passed** |
| **Regression command** | `python -m pytest tests/identity_authority/test_wp6_timeline_consumer.py tests/test_merchant_home_experience_v1.py tests/test_merchant_home_experience_activation_v1.py tests/test_knowledge_routing_v1.py -q --tb=line` |
| **Regression result** | **39 passed** |
| **`main.py` impact** | **None** |
| **Query / I/O** | No new query classes; evidence gate parses recovery_key only; bulk reader reused |
| **Rollback** | `git revert <hash>` **or** `git reset --hard 0c9ac34` |
| **Phase 5 / Attach started** | **No** |

---

## 3. Files created

| Path |
|------|
| `services/identity_authority/timeline_consumer_v1.py` |
| `services/merchant_timeline_v1.py` |
| `tests/identity_authority/test_wp6_timeline_consumer.py` |
| `WP-06_REVIEW.md` |
| `docs/investigations/INV_002_WP06_BRIEF.md` |
| `docs/investigations/INV_002_WP06_REVIEW.md` |

## 4. Files modified

| Path |
|------|
| `services/identity_authority/__init__.py` |
| `services/merchant_home_composition_v1.py` |
| `services/merchant_home_experience_activation_v1.py` |
| `services/knowledge_routing_v1.py` |
| `docs/SYSTEM_SUMMARY.md` |
| `docs/investigations/INV-002.md` |

## 5. Files intentionally untouched

| Path / area | Why |
|-------------|-----|
| `main.py` | Composition-only; no WP-6 wiring needed |
| Widget / Setup / WhatsApp / Recommendations | Out of scope |
| Phase 5 Attach / Simulator | Forbidden until RV-B |
| Scheduler / pool / alembic | Forbidden |
| Timeline **writers** (`record_recovery_truth_event`) | Evidence append path — not merchant identity resolve |
| Unrelated dirt | Excluded |

---

## 6. Timeline identity paths migrated

| Path | After |
|------|--------|
| Home Activity Timeline (`while_away` / MV-5) | `build_merchant_activity_timeline_v1` under `timeline_identity_scope` |
| Timeline knowledge routing | `route_timeline_knowledge_v1(store_slug=mqic.store_slug)` |
| Evidence reader (merchant path) | `get_recovery_truth_timeline_for_mqic` / `bulk_timeline_status_sets_for_mqic` |

## 7. Legacy identity paths removed

| Removed |
|---------|
| Home inline while_away projection without Timeline MQIC consumer |
| Ungated assumption that Timeline tenant equals caller slug without Authority |

**Remaining (not WP-6):** normal-carts batch still uses ungated `bulk_timeline_status_sets` (cart list identity — separate from MV-5 Activity Timeline); Widget/Setup; Attach.

---

## 8–17. Impact

| Dimension | Result |
|-----------|--------|
| Identity Contract Tests | **66 passed** (WP-1…WP-6) |
| Timeline / Home / routing regression | **39 passed** |
| Production equivalence | Same while_away item shape; Home/Brief/Knowledge/Timeline share MQIC on session path |
| Query-count | **0 new classes**; recovery_key parse is CPU-only |
| I/O / Latency | No new I/O; one Authority seal (reuse when Home already bound) |
| Scheduler / Pool | **None** |
| Architectural Debt Introduced | **None** |
| Architectural Debt Removed | Timeline independent of Authority; RV-B Timeline gap |
| Legacy remaining | Widget, Setup, WhatsApp, Recommendations; cart-batch ungated timeline status helper; Phase 5 Attach |
| Authority Health | Owner `platform_identity_authority`; consumers + **Timeline**; Coverage Activity Timeline + gated evidence readers |

## 18. `main.py` impact

**None** — confirmed by ICT `test_main_py_untouched_by_wp6_identity`.

## 19. Rollback boundary

```text
git revert 2439969
# or
git reset --hard 0c9ac34
```

Independently reversible — no Phase 5 dependency.

## 20. Recommendation for RV-B

**Recommend: Approve WP-6 → run RV-B / RC-2 evaluation** (Home ≡ Knowledge ≡ Brief ≡ Timeline on session MQIC).

**Do not begin Reality Attach / Phase 5 until RV-B Architecture approval.**

---

## STOP

Await Architecture Review for **RV-B**. Do not begin Phase 5 Attach.
