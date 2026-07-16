# INV-002 WP-4 Review — Daily Brief → Identity Authority

| Field | Value |
|-------|-------|
| Investigation ID | INV-002 |
| Work Package ID | WP-4 |
| Title | Daily Brief Consumer Migration (Execution Architecture Phase 4 surface) |
| Branch | `feature/inv002-wp4` |
| Commit hash | `584eaf8` (`584eaf8292b2a6e72d7f8a0597147a80b6bff605`) |
| Author | Engineering (agent) |
| Reviewer | ☐ Architecture Board |
| Date submitted (UTC) | 2026-07-16 |

**Brief:** [`docs/investigations/INV_002_WP04_BRIEF.md`](docs/investigations/INV_002_WP04_BRIEF.md)

---

## 0. Frozen WP-4 contract (pre-implementation confirmation)

### Exact frozen contract

From [`INV_002_EXECUTION_ARCHITECTURE.md`](INV_002_EXECUTION_ARCHITECTURE.md) **Phase 4**:

```text
Phase 4  Merchant surface consumer migration
         Dashboard · Knowledge · Brief · Timeline · Widget paths · WhatsApp · Recommendations · Setup
```

| Item | Contract |
|------|----------|
| **Objective** | Merchant surfaces consume MQIC; retire private resolvers (IA-2, IA-4, G-IA-1) |
| **WP-4 surface** | **Daily Brief only** (next Phase 4 surface after Knowledge / WP-2; per WP-02 sequencing) |
| **Already migrated** | Knowledge (WP-2) |
| **ICT** | ICT-12 Daily Brief keyed only from MQIC |
| **Rollback** | Per-surface consumer PR — revert WP-4 without stranding Knowledge/session |
| **Not this WP** | Dashboard/Home · Timeline · Widget · Setup · Simulator · WhatsApp · Recommendations · Phase 5 Attach · Phase 6 providers · WP-5 · global middleware |

### Dependencies

| Dependency | Status |
|------------|--------|
| WP-1 Identity Authority foundation | **Required — complete** |
| WP-2 Knowledge consumer | **Required — complete** (Brief may call Knowledge with MQIC) |
| WP-3 Session & membership | **Required — complete** (Brief HTTP bind → `resolve_mqic_from_session`) |

### Consumer / surface migrated

**Daily Brief** (`GET /api/dashboard/daily-brief` + `build_merchant_daily_brief_api_payload`).

### Expected files

| Path | Nature |
|------|--------|
| `services/identity_authority/daily_brief_consumer_v1.py` | create |
| `services/identity_authority/__init__.py` | export WP-4 API |
| `routes/daily_brief.py` | MQIC bind; remove legacy auth-slug resolve |
| `services/merchant_daily_brief_v1.py` | `daily_brief_identity_scope` |
| `tests/identity_authority/test_wp4_daily_brief_consumer.py` | ICT |
| `WP-04_REVIEW.md` / brief / SYSTEM_SUMMARY / INV-002 | delivery docs |

### Prohibited files

| Path / area | Reason |
|-------------|--------|
| `main.py` | Composition-only — no WP-4 wiring |
| Dashboard/Home identity resolve | Separate Phase 4 surface |
| Timeline / Widget / Setup / Simulator | Out of scope |
| Scheduler / pool / alembic | Forbidden impact |
| Unrelated local dirt | Must not enter WP-4 commit |

### Completion criteria

- Brief HTTP path binds MQIC via Phase 3 session membership
- Brief builder tenant key = `mqic.store_slug`
- No `merchant_authenticated_store_slug(` on Brief route
- ICT WP-1…WP-4 + Brief regression green
- Production merchant-facing Brief behaviour equivalent (same store after session bind)
- `main.py` unchanged

### Rollback boundary

`git revert 584eaf8` **or** `git reset --hard 223c66c`

### Reality Validation impact

| Gate | Impact |
|------|--------|
| RV-B (Surface one-store story) | **Partial progress** — Brief + Knowledge share MQIC on session path; Home/Timeline still legacy until later Phase 4 WPs |
| RV-A | Unchanged (Phase 3 already delivered) |
| RC-2 | Not claimed complete (requires Home/Timeline too) |

### Invariants confirmed before coding

| Invariant | Commitment |
|-----------|------------|
| Architectural debt must not increase | Yes — retire Brief-local resolve |
| Operational quality/speed must not degrade | Yes — same session lookup class as Knowledge |
| `main.py` composition-only | Yes — **untouched** |
| No new database queries | Yes — Phase 3 reuse |
| No new I/O | Yes — no global middleware |
| No Scheduler / Pool impact | Yes |
| No provider-specific identity leakage | Yes — canonical slug only |
| Identity resolves once | Yes — request-scoped bind |
| MQIC immutable | Yes — IA-3 |
| No independent store_slug resolution in migrated consumer | Yes |
| No unrelated consumer migration | Yes — Brief only |
| Production merchant-facing behaviour equivalent | Yes |
| Unexplained difference → STOP | Acknowledged |
| Unrelated local dirt excluded from commit | Yes |

---

## 1. Summary

Migrated **Daily Brief** to consume Platform Identity Authority MQIC:

- `daily_brief_consumer_v1.py` — session bind (Phase 3), identity scope, ops diagnostics
- `routes/daily_brief.py` — removed legacy auth-slug resolve; MQIC bind + mismatch fail-closed
- `build_merchant_daily_brief_api_payload` — tenant from MQIC; Knowledge call passes MQIC
- Home composition still passes caller slug (sealed via Authority; Home not migrated)
- **`main.py` untouched**; Dashboard/Timeline/Widget not migrated

---

## 2. Delivery (final)

| Field | Value |
|-------|--------|
| **Branch** | `feature/inv002-wp4` |
| **Final commit hash** | `584eaf8` (`584eaf8292b2a6e72d7f8a0597147a80b6bff605`) — WP-4 delivery |
| **Test command** | `python -m pytest tests/identity_authority/ tests/test_merchant_daily_brief_v1.py tests/test_merchant_daily_brief_composer_v2.py tests/time_authority/test_wp6_daily_brief_cross_surface.py -q --tb=line` |
| **Test result** | **86 passed** |
| **`main.py` unchanged** | **Confirmed** |
| **Query / I/O evidence** | No new query classes; Phase 3 session bind reuse; no global middleware; no migrations |
| **Rollback boundary** | `git revert 584eaf8` **or** `git reset --hard 223c66c` |
| **WP-5 started** | **No** |

---

## 3. Files created

| Path | Change |
|------|--------|
| `services/identity_authority/daily_brief_consumer_v1.py` | add |
| `tests/identity_authority/test_wp4_daily_brief_consumer.py` | add |
| `WP-04_REVIEW.md` | add |
| `docs/investigations/INV_002_WP04_BRIEF.md` | add |
| `docs/investigations/INV_002_WP04_REVIEW.md` | stub |

## 4. Files modified

| Path | Change |
|------|--------|
| `routes/daily_brief.py` | MQIC bind; remove legacy auth-slug resolve |
| `services/merchant_daily_brief_v1.py` | `daily_brief_identity_scope` |
| `services/identity_authority/__init__.py` | export WP-4 API |
| `docs/SYSTEM_SUMMARY.md` | changelog |
| `docs/investigations/INV-002.md` | WP-4 pointer |

## 5. Files intentionally untouched

| Path / area | Why |
|-------------|-----|
| `main.py` | Composition-only |
| Dashboard/Home identity | Separate Phase 4 surface |
| Timeline / Widget / Setup / Simulator | Out of scope |
| Scheduler / pool / alembic | Forbidden |
| Unrelated repo dirt | Excluded from commit |

## 6. Exact identity paths migrated

| Path | Before | After |
|------|--------|-------|
| `GET /api/dashboard/daily-brief` | `merchant_authenticated_store_slug` | `bind_mqic_for_daily_brief` → Phase 3 |
| `build_merchant_daily_brief_api_payload` | raw `store_slug` | `daily_brief_identity_scope` / MQIC |

## 7. Legacy identity paths removed (this WP)

- Route-local `merchant_authenticated_store_slug` on Daily Brief API

## 8–17. Impact table

| Dimension | Result |
|-----------|--------|
| Identity Contract Tests | WP-1…WP-4 suite (see delivery stamp) |
| Existing consumer regression | Brief v1 + composer v2 + INV-001 WP-6 cross-surface |
| Production equivalence | Same primary/session slug after bind; Home caller-slug seal preserved |
| Query-count impact | **None** (Phase 3 reuse) |
| I/O impact | **None** new |
| Operational latency | Equivalent session bind class |
| Scheduler impact | **None** |
| Pool impact | **None** |

## 18. Authority Health

| Field | Value |
|-------|-------|
| Authority Owner | `platform_identity_authority` |
| Authority Consumers | Knowledge; Session (Phase 3); **Daily Brief (WP-4)** |
| Authority Coverage | Knowledge + Daily Brief HTTP + Brief builder |
| Legacy Identity Paths Remaining | Dashboard/Home, Timeline, Widget, Setup, Simulator, `merchant_authenticated_store_slug` outside Knowledge/Brief |
| Identity Violations | Dual-resolve / immutability / mismatch fail-closed (ICT) |
| Migration Progress | WP-1 ✓ · WP-2 ✓ · WP-3 ✓ · WP-4 Brief ✓ · WP-5 not started |

## 19. Architectural Debt Introduced

- Phase 4 incomplete (Home/Timeline/… still legacy) — expected; RV-B not claimed
- Phase 2 global composition middleware still absent (documented)

## 20. Architectural Debt Removed

- Daily Brief route independent identity resolve (G-IA-1)

## 21. Legacy Identity Paths Remaining

- Dashboard / Home composition store resolution
- Timeline / Widget / Setup / Simulator
- `merchant_authenticated_store_slug` outside Knowledge + Daily Brief routes
- Home embed of Brief still passes caller slug (sealed; Home not migrated)

## 22. `main.py` impact

**None** — not modified; router include unchanged.

## 23. Risks

| Risk | Level | Mitigation |
|------|-------|------------|
| Partial Phase 4 (RV-B incomplete) | Medium | Documented; do not claim one-store story Done |
| Home vs Brief identity until Home migrates | Low | Home slug seal + session Brief share primary when session-correct |

## 24. Rollback boundary

Revert `584eaf8` (and tip stamp if needed); parent tip before WP-4: `223c66c`.

## 25. Reality Validation impact

RV-B **partial** (Brief + Knowledge). Do not start Phase 5 on RV-B alone.

## 26. Recommendation on WP-5

**Recommend: Approve WP-4 → authorize next Phase 4 surface** (Dashboard/Home or Timeline — Board chooses) **or** Board-named WP-5 only after Architecture Review.

**Do not begin WP-5 / Phase 5 Attach without Architecture Approval.**

---

## STOP

**Do not begin WP-5.** Await Architecture Review.
