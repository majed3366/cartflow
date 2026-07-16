# INV-002 WP-5 Review — Dashboard/Home → Identity Authority

| Field | Value |
|-------|-------|
| Investigation ID | INV-002 |
| Work Package ID | WP-5 |
| Title | Dashboard/Home Consumer Migration (Execution Architecture Phase 4 surface) |
| Branch | `feature/inv002-wp5` |
| Delivery commit | `03529fc` (`03529fcbc9da774b06fabba93a74fddee2e4e459`) |
| Review stamp tip | docs-only evidence pack on `feature/inv002-wp5` tip (code delivery remains `03529fc`) |
| Author | Engineering (agent) |
| Reviewer | ☐ Architecture Board |
| Date submitted (UTC) | 2026-07-16 |
| Evidence refreshed (UTC) | 2026-07-16 |

**Brief:** [`docs/investigations/INV_002_WP05_BRIEF.md`](docs/investigations/INV_002_WP05_BRIEF.md)

---

## 0. Frozen WP-5 contract (confirmed)

From [`INV_002_EXECUTION_ARCHITECTURE.md`](INV_002_EXECUTION_ARCHITECTURE.md) **Phase 4** — surface **Dashboard/Home only**.

| Item | Contract |
|------|----------|
| **Purpose** | Home consumes MQIC; retire independent Home identity (IA-2, IA-4, G-IA-1) |
| **Already migrated before this WP** | Knowledge (WP-2), Session (WP-3), Daily Brief (WP-4) |
| **Not this WP** | Timeline · Widget · Setup · Simulator Attach (Phase 5) · UI/copy/KPI changes |
| **Identity consumption only** | Confirmed — no UI redesign, no merchant copy, no KPI semantic changes |

---

## 1. Summary

Migrated **Dashboard/Home** to consume Platform Identity Authority MQIC:

- `dashboard_home_consumer_v1.py` — Phase 3 session bind, identity scope, ops diagnostics
- `build_merchant_home_experience_api_payload` — binds/scopes MQIC; passes **same** MQIC to Brief + Knowledge
- Activation snapshot attach seals caller slug via Authority (no new I/O)
- `main.py` — composition-only: passes `cookies=` into Home builder (**+2 lines**; no ResolveMQIC)

**Not started:** Timeline, Widget, Setup, Simulator Attach / Phase 5.

---

## 2. Exact Dashboard/Home identity paths migrated

| # | Path | Location | After WP-5 |
|---|------|----------|------------|
| H1 | Live Home composition (session → Home) | `build_merchant_home_experience_api_payload` in `services/merchant_home_composition_v1.py` | `bind_mqic_for_dashboard_home(cookies)` → Phase 3 `resolve_mqic_from_session` → `dashboard_home_identity_scope` → tenant = `mqic.store_slug` |
| H2 | Nested Daily Brief under Home | same builder → `build_merchant_daily_brief_api_payload(..., mqic=identity)` | Reuses bound MQIC (no second resolve) |
| H3 | Nested Knowledge under Home | same builder → `build_knowledge_report(..., mqic=identity)` | Reuses bound MQIC (no second resolve) |
| H4 | Summary → Home composition wiring | `main.py` `_api_json_dashboard_summary` call site | Passes `cookies=cookies` only (composition) |
| H5 | Snapshot/degraded Home activation attach | `compose_home_api_payload_from_summary_context` in `merchant_home_experience_activation_v1.py` | Caller slug sealed via `dashboard_home_identity_scope` / Authority (zero DB I/O) |

**First session → store → Home composition boundary:**  
`build_merchant_home_experience_api_payload` (invoked from live summary after auth-bound `dash_store`).

---

## 3. Exact legacy identity resolvers removed

| Removed behaviour | Where |
|-------------------|--------|
| Home treating raw caller `store_slug` as authoritative tenant without Authority seal | `build_merchant_home_experience_api_payload` (pre-WP-5) |
| Activation attach writing `home["store_slug"]` from raw summary/snapshot string without MQIC seal | `compose_home_api_payload_from_summary_context` (pre-WP-5) |
| Nested Brief/Knowledge under Home receiving only bare slug (could seal separately / diverge) | Home builder now passes the **same** bound `identity` MQIC |

**Not removed (intentionally — out of WP-5 scope):**

- Middleware `resolve_authenticated_store_slug` / `merchant_auth_store_slug` pointer
- `_dashboard_recovery_store_row` / `dashboard_store_context` Store-row lookup for KPIs
- `resolve_merchant_store_slug_for_snapshot` snapshot key
- `merchant_authenticated_store_slug` on non-Home routes (Timeline, Widget, etc.)

---

## 4. Evidence — Session · Home · Knowledge · Brief share one immutable MQIC

| Layer | Mechanism | Evidence |
|-------|-----------|----------|
| **Session** | `bind_mqic_for_dashboard_home` → `resolve_mqic_from_session` (WP-3) | `dashboard_home_consumer_v1.py` |
| **Dashboard/Home** | `dashboard_home_identity_scope` + `ensure_dashboard_home_mqic`; payload `store_slug = identity.store_slug` | `merchant_home_composition_v1.py` |
| **Daily Brief** | `build_merchant_daily_brief_api_payload(..., mqic=identity)` inside Home scope | same builder |
| **Knowledge** | `build_knowledge_report(..., mqic=identity)` inside Home scope | same builder |
| **Immutability** | ICT `test_immutability_preserved_under_home` — `reject_field_mutation` raises | `test_wp5_dashboard_home_consumer.py` |
| **Single resolve** | ICT `test_identity_resolved_once_in_home_scope` — second `resolve_and_bind` → `DualResolveViolation` | same |
| **Cross-surface equality** | ICT `test_home_brief_knowledge_share_same_mqic` — Brief + KL receive identical `mqic.store_slug` | same (ICT-14 class) |
| **Mismatch fail-closed** | ICT `test_home_slug_mismatch_fail_closed` | same |

---

## 5. Production-equivalence evidence

| Check | Evidence |
|-------|----------|
| Same session lookup class | Phase 3 reuses `resolve_merchant_onboarding_store` — no new identity query class |
| Same tenant after bind | Home `store_slug` = MQIC `store_slug` from session primary/active (explicit→session→primary) |
| KPI path unchanged | `_dashboard_recovery_store_row` / KPI projections not rewritten; still auth-bound Store row |
| No UI / copy / KPI semantic edits | Diff limited to identity wiring + docs/tests |
| Snapshot attach | Still transport-safe compose; slug sealed without new DB I/O |
| Unexplained difference → STOP | No unexplained merchant-facing delta observed in ICT/regression |

---

## 6. Identity Contract Tests

| Field | Value |
|-------|--------|
| **Command** | `python -m pytest tests/identity_authority/ -q --tb=line` |
| **Result** | **55 passed** (2026-07-16 evidence refresh) |
| **Includes** | WP-1…WP-5 ICT (core, Knowledge, session, Brief, Home) |

---

## 7. Dashboard/Home regression tests

| Field | Value |
|-------|--------|
| **Command** | `python -m pytest tests/test_merchant_home_experience_v1.py tests/test_merchant_home_experience_activation_v1.py -q --tb=line` |
| **Result** | **16 passed** (2026-07-16 evidence refresh) |

---

## 8. Query-count comparison

| Baseline (pre-WP-5 Home) | WP-5 |
|--------------------------|------|
| Session Home used caller slug; nested Brief/Knowledge could each seal from slug (Authority seal = no DB) | Live Home: **one** Phase 3 session bind (`resolve_merchant_onboarding_store` — same class as Knowledge/Brief HTTP) |
| No new Store enumeration / membership query | **No new query classes** |
| KPI Store row lookup | **Unchanged** |

**Verdict:** Query-count impact for identity = **0 new classes**; live path uses the same session onboarding lookup already used by migrated surfaces.

---

## 9. I/O impact

| Item | Result |
|------|--------|
| New global HTTP middleware | **None** |
| New network I/O | **None** |
| Snapshot activation seal | In-process Authority seal (caller slug) — **no DB** |
| Migrations | **None** |

---

## 10. Latency impact

| Item | Result |
|------|--------|
| Extra identity round-trips vs migrated Knowledge/Brief | **None** — one bind per Home composition; nested surfaces reuse MQIC |
| Hot-path KPI queries | Unchanged |
| **Verdict** | Operational latency for identity path **equivalent** (PI-7 class) |

---

## 11. Scheduler impact

**None** — no scheduler files touched; no job/scanner changes.

---

## 12. Pool impact

**None** — no pool config, session factory, or connection lifecycle changes.

---

## 13. `main.py` impact

| Item | Evidence |
|------|----------|
| Diff size | **+2 lines** in `03529fc` |
| Content | Comment + `cookies=cookies` kwarg to Home builder |
| ResolveMQIC / membership / bind in main | **Absent** (`test_main_py_composition_only_for_wp5`) |
| Verdict | **Composition-only** — compliant |

---

## 14. Architectural Debt Introduced

**None.**

(Phase 4 remains incomplete until Timeline/etc. migrate — that is **remaining migration**, not debt introduced by WP-5.)

---

## 15. Architectural Debt Removed

- Dashboard/Home independent identity consumption (G-IA-1 breach risk on Home composition)
- Activation attach unsigned raw slug as Home tenant without Authority seal
- Nested Brief/Knowledge under Home able to diverge on identity from Home

---

## 16. Authority Health

| Field | Value |
|-------|-------|
| **Owner** | `platform_identity_authority` |
| **Consumers** | Knowledge (WP-2); Session/membership (WP-3); Daily Brief (WP-4); **Dashboard/Home (WP-5)** |
| **Coverage** | Session bind → Home composition + nested Brief/Knowledge; snapshot Home attach seal |
| **Violations** | Dual-resolve / immutability / slug-mismatch fail-closed enforced in ICT |
| **Legacy paths remaining** | Timeline; Widget; Setup; Simulator; WhatsApp/Recommendations surfaces; `merchant_authenticated_store_slug` outside migrated routes; KPI Store-row helpers (row lookup, not speech identity); snapshot slug resolver for snapshot **key** (Home attach seals separately) |

---

## 17. Files created

| Path |
|------|
| `services/identity_authority/dashboard_home_consumer_v1.py` |
| `tests/identity_authority/test_wp5_dashboard_home_consumer.py` |
| `WP-05_REVIEW.md` |
| `docs/investigations/INV_002_WP05_BRIEF.md` |
| `docs/investigations/INV_002_WP05_REVIEW.md` |

## 18. Files modified

| Path |
|------|
| `services/merchant_home_composition_v1.py` |
| `services/merchant_home_experience_activation_v1.py` |
| `services/identity_authority/__init__.py` |
| `main.py` |
| `docs/SYSTEM_SUMMARY.md` |
| `docs/investigations/INV-002.md` |

## 19. Files intentionally untouched

| Path / area | Why |
|-------------|-----|
| Timeline / Widget / Setup / Simulator Attach | Out of scope |
| KPI projection / Time Authority recipes | No KPI semantic changes |
| `_dashboard_recovery_store_row` / snapshot slug resolver | Row/key lookup; Home identity is MQIC |
| Scheduler / pool / alembic | Forbidden |
| Unrelated local dirt | Excluded from `03529fc` |

---

## 20. Clean WP-5 delivery-path confirmation

| Check | Result |
|-------|--------|
| Delivery commit | `03529fc` |
| Delivery paths vs tip (code + review artefacts) | Confirmed clean at evidence refresh prior to this stamp |
| Unrelated dirt | Present in working tree; **not** in WP-5 commits |
| Timeline / Phase 5 Attach | **Not started** |
| Push | **Not performed** |

---

## 21. Rollback boundary

```text
git revert 03529fc
# or
git reset --hard 2add863
```

Parent tip before WP-5 delivery: `2add863` (WP-4 stamp).

---

## 22. Reality Validation status

### What is now testable (session path)

| Gate / check | Status |
|--------------|--------|
| Session → single MQIC (RV-A foundation) | Available (WP-3) |
| Same session: **Home ≡ Knowledge ≡ Daily Brief** canonical store | **Testable** on session / ICT-14 path |
| Home keyed only from MQIC (ICT-10 class) | **Testable** |
| Mismatch slug ≠ MQIC fail-closed | **Testable** |

### What remains blocked before Simulator Attach (Phase 5)

| Blocker | Why |
|---------|-----|
| Full **RV-B** (one-store story across Home/Knowledge/Brief/**Timeline**) | Timeline not migrated |
| Merchant Validation MV-5 (Timeline) / MV-9 complete story | Surfaces incomplete |
| **RV-C / Phase 5 Attach** honesty | Attach product path not started — **must not begin** until Architecture authorizes Phase 5 |
| Final Merchant Validation campaign | Explicitly **not claimed** by WP-5 |

---

## 23. Recommendation — next Phase 4 surface

**Recommend: Timeline** (ICT-13) as the next Phase 4 consumer migration after Architecture Approval of this review.

**Do not begin Simulator Attach / Execution Architecture Phase 5 without Architecture Approval.**  
**Do not begin Widget / Setup in the same WP as Timeline.**

---

## STOP

Governed WP-5 review complete. Await Architecture Review.

- Do **not** begin Timeline migration in this task.
- Do **not** begin Phase 5 Attach.
- Do **not** push unless explicitly requested.
