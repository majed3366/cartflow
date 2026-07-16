# INV-002 WP-5 Review — Dashboard/Home → Identity Authority

| Field | Value |
|-------|-------|
| Investigation ID | INV-002 |
| Work Package ID | WP-5 |
| Title | Dashboard/Home Consumer Migration (Execution Architecture Phase 4 surface) |
| Branch | `feature/inv002-wp5` |
| Commit hash | *(stamped at delivery)* |
| Author | Engineering (agent) |
| Reviewer | ☐ Architecture Board |
| Date submitted (UTC) | 2026-07-16 |

**Brief:** [`docs/investigations/INV_002_WP05_BRIEF.md`](docs/investigations/INV_002_WP05_BRIEF.md)

---

## 0. Frozen WP-5 contract (pre-implementation)

### Exact frozen contract

From [`INV_002_EXECUTION_ARCHITECTURE.md`](INV_002_EXECUTION_ARCHITECTURE.md) **Phase 4**:

```text
Phase 4  Merchant surface consumer migration
         Dashboard · Knowledge · Brief · Timeline · Widget paths · WhatsApp · Recommendations · Setup
```

| Item | Contract |
|------|----------|
| **Purpose** | Merchant surfaces consume MQIC; retire private resolvers (IA-2, IA-4, G-IA-1) |
| **WP-5 surface** | **Dashboard/Home only** |
| **Already migrated** | Knowledge (WP-2), Session (WP-3), Daily Brief (WP-4) |
| **ICT** | ICT-10 Home keyed from MQIC; ICT-14 cross-surface same MQIC with Brief/Knowledge |
| **Expected outcome** | Session, Home, Dashboard summary Home embed, Knowledge, Brief share one canonical store |
| **Not this WP** | Timeline · Widget · Setup · Simulator Attach (Phase 5) · UI/copy/KPI changes |

### Current identity paths identified (pre-migration)

| Path | Location | Role |
|------|----------|------|
| Middleware auth slug | `main.py` `merchant_auth_gate_middleware` → `set_merchant_auth_store_slug` | Session pointer (unchanged) |
| Dashboard store row | `main._dashboard_recovery_store_row` / `dashboard_store_context` | Store row for KPIs (unchanged lookup class) |
| Snapshot slug | `resolve_merchant_store_slug_for_snapshot` | Snapshot key (unchanged) |
| **Home composition boundary** | `build_merchant_home_experience_api_payload` called from `_api_json_dashboard_summary` | **First session→store→Home composition boundary — migrated** |
| Activation attach | `compose_home_api_payload_from_summary_context` | Snapshot-safe Home attach — sealed via Authority |

### Identity consumption only

Yes — no UI redesign, no merchant copy, no KPI semantic changes, no Attach, no unrelated surfaces.

### Invariants

| Invariant | Commitment |
|-----------|------------|
| Architectural Debt Introduced: None | Yes — retire Home-independent identity use |
| Operational performance must not degrade | Yes — Phase 3 session bind reuse |
| `main.py` no identity/business logic | Yes — cookies composition wiring only |
| No new DB queries / I/O / Scheduler / Pool | Yes |
| No provider leakage · resolve once · MQIC immutable | Yes |
| Home must not resolve/substitute store_slug independently | Yes |
| Knowledge, Brief, Home same MQIC | Yes — nested pass-through |
| No unrelated dirt in commit | Yes |

---

## 1. Summary

Migrated **Dashboard/Home** to consume Platform Identity Authority MQIC:

- `dashboard_home_consumer_v1.py` — Phase 3 session bind, identity scope, ops diagnostics
- `build_merchant_home_experience_api_payload` — binds/scopes MQIC; passes same MQIC to Brief + Knowledge
- Activation snapshot attach seals caller slug via Authority (no new I/O)
- `main.py` — composition-only: passes `cookies=` into Home builder (no ResolveMQIC in main)
- **Not started:** Timeline, Widget, Setup, Simulator Attach / Phase 5

---

## 2. Delivery

| Field | Value |
|-------|--------|
| **Branch** | `feature/inv002-wp5` |
| **Final commit hash** | *(stamped at commit)* |
| **Test command** | `python -m pytest tests/identity_authority/ tests/test_merchant_home_experience_v1.py tests/test_merchant_home_experience_activation_v1.py tests/test_merchant_daily_brief_v1.py -q --tb=line` |
| **Test result** | **80 passed** |
| **`main.py` impact** | Composition wiring only (`cookies=` kwarg) — no identity logic |
| **Query / I/O** | No new query classes; Phase 3 reuse; no global middleware |
| **Rollback** | `git revert <hash>` **or** `git reset --hard 2add863` |
| **Phase 5 / Timeline started** | **No** |

---

## 3. Files created

| Path | Change |
|------|--------|
| `services/identity_authority/dashboard_home_consumer_v1.py` | add |
| `tests/identity_authority/test_wp5_dashboard_home_consumer.py` | add |
| `WP-05_REVIEW.md` | add |
| `docs/investigations/INV_002_WP05_BRIEF.md` | add |
| `docs/investigations/INV_002_WP05_REVIEW.md` | stub |

## 4. Files modified

| Path | Change |
|------|--------|
| `services/merchant_home_composition_v1.py` | MQIC scope; pass MQIC to Brief/Knowledge |
| `services/merchant_home_experience_activation_v1.py` | Seal attach slug via Authority |
| `services/identity_authority/__init__.py` | export WP-5 API |
| `main.py` | pass `cookies=` to Home builder (composition only) |
| `docs/SYSTEM_SUMMARY.md` | changelog |
| `docs/investigations/INV-002.md` | WP-5 pointer |

## 5. Files intentionally untouched

| Path / area | Why |
|-------------|-----|
| Timeline / Widget / Setup / Simulator | Out of scope |
| KPI projection semantics | No KPI semantic changes |
| Snapshot slug resolver / `_dashboard_recovery_store_row` | Existing row lookup; Home consumes MQIC |
| Scheduler / pool / alembic | Forbidden |
| Unrelated repo dirt | Excluded |

## 6. Identity paths migrated

| Path | After |
|------|--------|
| Live Home composition | Session → Phase 3 MQIC → Home/Brief/Knowledge |
| Snapshot Home activation attach | Caller slug sealed via Authority |

## 7. Legacy paths removed

- Home composition treating raw `store_slug` as authoritative without Authority seal
- Activation attach writing `store_slug` without MQIC seal

## 8–17. Impact

| Dimension | Result |
|-----------|--------|
| Identity Contract Tests | WP-1…WP-5 suite (**80 passed** with Home/Brief regressions) |
| Production equivalence | Same session primary/active slug; Home/Brief/Knowledge share MQIC |
| Query / I/O / latency | No new queries; Phase 3 bind class |
| Scheduler / Pool | None |
| Architectural Debt Introduced | **None** |
| Architectural Debt Removed | Home independent identity consumption |
| Migration Remaining | Timeline, Widget, Setup, WhatsApp, Recommendations; Phase 5 Attach |
| Authority Health | Owner `platform_identity_authority`; consumers Knowledge + Session + Brief + **Home** |
| Reality Validation | RV-B **advanced** (Home+Knowledge+Brief); Timeline still legacy — do not claim RV-B Done |
| Rollback | Parent tip `2add863` |

## 18. Recommendation — next Phase 4 surface

**Recommend: Timeline** (ICT-13) as next Phase 4 surface after Architecture Approval of this WP.

**Do not begin Simulator Attach / Execution Architecture Phase 5 without Architecture Approval.**

---

## STOP

Await Architecture Review. Do not begin Timeline / Widget / Setup / Phase 5 Attach in this delivery.
