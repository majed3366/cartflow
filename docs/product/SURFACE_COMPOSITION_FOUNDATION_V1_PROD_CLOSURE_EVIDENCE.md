# Surface Composition Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-22  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `397dd91f26a2038d64e464b4e11d9846a3eb4593` (PR #45)

---

## 1. Architecture inventory

| Concern | Finding |
|---------|---------|
| Home / dashboard / workspace / cart / communication projections | Page-owned select/dedupe/rank remains interim; SCF is the migration target |
| Knowledge / Guidance / Routing / Presentation | Closed Product Performance stack — **not duplicated** |
| Projection registries | GRF surface keys reused; SCF adds composition-only `surface_registry_v1` |
| Migration plan | Pages become consumers of `surface_compositions` after review; no page redesign in this task |

---

## 2. Implementation decision

| Decision | Choice |
|----------|--------|
| Immediate inputs | Merchant Presentation + Knowledge only |
| Routing | Consumed via Presentation `surface_key` (no re-routing) |
| Surfaces | Home, Decision Workspace, Carts, Communication, Settings |
| Storage | Projection table `surface_compositions` |
| Flag | `CARTFLOW_SURFACE_COMPOSITION_V1` (default on) |
| Probe | `GET /dev/surface-composition?store=demo` |

---

## 3. Pull request merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#45](https://github.com/majed3366/cartflow/pull/45) | Surface Composition Foundation V1 | `397dd91f26a2038d64e464b4e11d9846a3eb4593` |

**Source commit:** `75606c8` on `feature/surface-composition-foundation-v1`  
**Migration:** Alembic `h7i8j9k0l1m2` → table `surface_compositions`  
**Feature flag:** `CARTFLOW_SURFACE_COMPOSITION_V1` (enabled)

---

## 4. Production probe / runtime evidence

```bash
python scripts/_verify_surface_composition_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true`

| Field | Value |
|-------|-------|
| `foundation_enabled` | true |
| `table_exists` | true |
| `deterministic` | **true** |
| `accounting_ok` | **true** |
| `registries_valid` | true |
| `duplicate_current` | **0** |
| `composition_count` / `accounted_count` | **33 / 33** |
| `upserted` / `materialized_row_count` | **33** |
| `canonical_fingerprint` | `f62cf2e4887f2f684e69c20544f3b01f7ca7aa6f005a527fb09882ba71c6ed44` |
| `non_demo_writes` | false |
| `consumes_governed_inputs_only` | true |
| `no_raw_data_reads` | true |
| `no_page_ui` | true |

### Composition counts (Demo)

| Surface | Count |
|---------|------:|
| home | 24 |
| decision_workspace | 4 |
| carts | 3 |
| communication | 1 |
| settings | 1 |

### Information classes

executive_summary×4, critical_attention×4, operational_health×3, knowledge×20, empty_state×2

### Accounting

| Outcome | Count |
|---------|------:|
| composed | 16 |
| collapsed | 17 |
| suppressed | 0 |
| expired | 0 |
| deferred | 0 |
| rejected | 0 |
| failed | 0 |

### Duplicate / freshness / cognitive-load evidence

- Duplicate groups present (guidance + knowledge + empty); `duplicate_current=0`
- Freshness: all `fresh` in this snapshot
- Cognitive load: Home knowledge overflow → **17 collapsed** (limits enforced; no unbounded expansion)
- Empty states: Communication `no_operational_issues`, Settings `nothing_requiring_action`
- Sample Home hero: `presentation_intent=hero`, class `executive_summary`, accounting `composed`

---

## 5. Deterministic rerun

Probe `deterministic=true` (double generate same fingerprint).

---

## 6. Failure isolation

`failures=[]`; compose/materialize errors empty; non-demo writes blocked by probe allowlist.

---

## 7. Tests

`pytest tests/test_surface_composition_v1.py -q` → **12 passed**

Coverage includes: governed inputs only, no raw reads, registry, information classes, priority ordering, freshness, duplicate suppression, cognitive-load, empty-state, deterministic identity, idempotent rerun, no duplicate current, lifecycle, expiry/suppression, accounting, store isolation, demo isolation, feature flag, runtime probe wiring, main.py wiring-only.

---

## 8. Deployment

| Item | Status |
|------|--------|
| PR merge to `main` | Done (#45) |
| Live probe | `ok: true` |
| Flag | on |
| Table | present |

---

## 9. Forbidden scope confirmation

| Forbidden | Confirmed absent |
|-----------|------------------|
| Home / DW / Carts / Communication / Settings redesign | Pass |
| Figma / CSS / components / frontend | Pass |
| AI summaries / notifications | Pass |
| New commercial business logic | Pass |
| Routing decisions | Pass (consume only) |
| CIS / widget / WhatsApp / purchase raw reads | Pass |

---

## 10. STOP condition

**Surface Composition Foundation V1 is PRODUCTION CLOSED.**

Do **not** begin until reviewed and approved:

- Home redesign / Home UI rollout
- Decision Workspace / Carts / Communication / Settings redesign
- Page binding of compositions into merchant UI
- Merchant action execution
- AI-generated summaries or recommendations
