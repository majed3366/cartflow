# Executive Knowledge Materialization Investigation V1

**Status:** Investigation complete — await Architectural Review  
**Date (UTC):** 2026-07-24  
**Type:** Architectural investigation (not a feature · not a bug fix · not WP-ET-11)  
**Stores in scope:** `demo` · Zid development store (platform-linked merchant store)  
**Constraint:** Evidence only. No implementation. No backfill. No storage change. No WP-ET-11.

---

## 0. Primary question

Why does Executive Knowledge Preview report **KnowledgeRecordV1 = 0** despite historical demo activity, widget events, WhatsApp events, returns, purchases, and Reality Simulator capability?

---

## 1. Pipeline counts

### 1.1 Production Evidence Truth shadow pipeline (observed / inferred)

Executive Knowledge Preview reads **only** the Shadow Knowledge store. It does **not** expose Observation / Evidence / Bundle counts. Therefore upstream ET stage counts on production are established by:

1. Live Preview API (Knowledge + store inventory)  
2. Code-path / flag architecture (what can populate those stores)  
3. Static call-graph proof (who invokes composers)

| Stage | `demo` (ET shadow) | Zid development store (ET shadow) | Evidence basis |
|-------|--------------------|-------------------------------------|----------------|
| **Legacy platform activity** (Postgres carts, WA logs, recovery timeline, product signals, SRS history) | **Present** (non-zero historical activity documented elsewhere) | **Present when linked** (Identity Authority / merchant store row) | Prior Reality Simulator / merchant validation artifacts use `store_slug=demo`; Zid-linked stores use their own `Store.slug` |
| **Raw → Observation (ET)** | **0 effective** | **0 effective** | `CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE` defaults OFF; dual-write returns `skipped/flag_off` (`observation_shadow_dual_write_v1.shadow_dual_write_observation_v1`). No production Observation admin probe; Knowledge inventory empty globally |
| **Observation → Evidence Truth (ET)** | **0 effective** | **0 effective** | `CARTFLOW_EVIDENCE_DUAL_WRITE` defaults OFF; publishers no-op when OFF (`evidence_dual_write_v1`). Never invokes Bundle/Knowledge compose |
| **Evidence → Evidence Bundle (ET)** | **0** | **0** | Bundle composer has **zero** non-test production callers (static scan 2026-07-24). `CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW` defaults OFF |
| **Bundle → KnowledgeRecordV1 (ET)** | **0** | **0** | Knowledge composer has **zero** non-test production callers. Live Preview: `record_count=0`, `stores=[]` |
| **Preview read** | **0** | **0** | Live `GET /preview/executive-knowledge/api` and `?store_slug=demo` both return `empty=true`, `record_count=0` |

### 1.2 Live Preview API (2026-07-24)

Unfiltered:

```text
flag_enabled=true
record_count=0
stores=[]
empty=true
findings_enabled=false
guidance_enabled=false
knowledge_composer_input_enabled=false
consumers_activated=false
input_authority=shadow_knowledge_only
```

`store_slug=demo`:

```text
flag_enabled=true
store_filter=demo
record_count=0
stores=[]
empty=true
honesty.status=empty_knowledge
```

**Implication:** There is no Knowledge for *any* store in the Preview process — not only `demo`. A Zid-slug filter cannot retrieve records that do not exist.

### 1.3 Where records disappear

```text
Legacy Raw / merchant activity (Postgres, widget, WA, SRS)
        ✗  STOP — never enters ET Observation (dual-write OFF + no historical ingest)
ET Observation
        ✗  STOP — never published as ET Evidence (dual-write OFF)
ET Evidence Truth
        ✗  STOP — Bundle composer never scheduled on production paths
ET Evidence Bundle
        ✗  STOP — Knowledge composer never scheduled on production paths
KnowledgeRecordV1  →  Preview reads here → 0
```

**Primary disappearance point:** between **legacy platform activity** and **ET Observation** (pipeline never fed).  
**Secondary disappearance point:** between **ET Evidence** and **Bundle/Knowledge** (composers exist but are **not on any production call graph**).

---

## 2. Stage where records stop (verdict)

| Stop # | Stage boundary | Severity | Nature |
|--------|----------------|----------|--------|
| **S1** | Legacy activity → ET Observation | **Primary** | Flags OFF; no historical ET ingest; dual-write idle |
| **S2** | ET Evidence → Bundle | **Hard architectural** | Composer not invoked outside tests/harnesses |
| **S3** | Bundle → Knowledge | **Hard architectural** | Same — no production caller |
| **S4** | Knowledge → Preview | **Not failing** | Preview correctly reports honest empty |

Preview is **working as designed**. Emptiness is **materialization absence**, not a Preview rendering bug.

---

## 3. Root cause

### RC-1 — Preview enablement ≠ Knowledge materialization (confirmed)

Only `CARTFLOW_EXECUTIVE_KNOWLEDGE_PREVIEW=true` was enabled on production. That flag gates **read access** to the Shadow Knowledge store (`executive_knowledge_preview_v1.executive_knowledge_preview_enabled`). It does **not**:

- enable Observation dual-write  
- enable Evidence dual-write  
- enable Bundle composer shadow  
- enable Knowledge composer shadow  
- invoke any composer  
- backfill historical data  

WP-ET-10.5 docs state this explicitly (`docs/implementation/WP_ET_10_5_EXECUTIVE_KNOWLEDGE_PREVIEW.md` §3).

### RC-2 — Knowledge Composer is feature-flagged AND never executed in production (confirmed)

| Check | Result |
|-------|--------|
| Flag | `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW` default **OFF** (`flags_v1.py`) |
| INPUT flag | `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT` default OFF + **unwired** |
| Production callers of `maybe_compose_knowledge_record_v1` / `compose_knowledge_record_v1` outside `services/evidence_truth` + tests | **0** (repo static scan 2026-07-24) |
| Production callers of Bundle compose counterparts | **0** |
| `main.py` | Hooks Observation/Evidence dual-write only; **no** Bundle/Knowledge compose calls |

Therefore Knowledge Composer is:

- **disabled** by default flag  
- **never executed** on production request/event paths  
- **not** “executed but empty” / “failed eligibility” / “discarded” — those outcomes require a call that does not occur  

When `maybe_compose_knowledge_record_v1` *would* run with flag OFF, it returns `{ok:false, skipped:true, reason:flag_off}` — still no records.

### RC-3 — Upstream ET stores are also empty by default (confirmed by architecture)

Observation + Evidence dual-write hooks exist on production paths (`main.py` cart-event/conversion, `purchase_truth`, WhatsApp delivery, recovery timeline, product line/hesitation hooks) but:

- gated by `CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE` / `CARTFLOW_EVIDENCE_DUAL_WRITE`  
- default **OFF** → no-op (`skipped/flag_off`)  
- even if ON, they **do not** call Bundle/Knowledge composers  

### RC-4 — Shadow storage is process-local (confirmed)

| Store | Module | Persistence |
|-------|--------|-------------|
| Observation | `observation_store_v1.py` | In-process `OrderedDict` singleton |
| Evidence | `evidence_store_v1.py` | In-process |
| Bundle | `bundle_store_v1.py` | In-process |
| Knowledge | `knowledge_store_v1.py` | In-process `_GLOBAL_KNOWLEDGE_STORE` |

Documented in WP-ET-03 / WP-ET-10 as process-local / soak gap. Consequences:

- Deploy / restart clears all Shadow Knowledge  
- Multi-worker: Preview may read a worker that never composed  
- Historical Postgres rows are **not** the Knowledge store  

### RC-5 — Historical merchant activity was never processed by ET Observation→Evidence→Bundle→Knowledge (confirmed)

No backfill / replay / materialize job for Evidence Truth Knowledge exists in production wiring. Reality Simulator and legacy Knowledge Foundation (`knowledge_statements`, BFL, etc.) are **parallel systems**, not Shadow KnowledgeRecordV1.

Therefore historical demo / Zid activity explains **platform richness**, not ET Knowledge counts.

### RC-6 — Store-slug mismatch is **not** the primary cause (confirmed)

| Check | Result |
|-------|--------|
| Unfiltered Preview `stores` | `[]` |
| `store_slug=demo` | `record_count=0` |
| Preview filter | case-normalized slug equality (`list_recent`) |

If mismatch were the only bug, unfiltered Preview would still show Zid (or other) stores. It shows **none**.

`demo` remains the canonical commerce-lab slug. Zid development store maps via Identity Authority to its own `Store.slug` / aliases — but with `stores=[]`, identity mapping cannot surface Knowledge that was never written.

---

## 4. Supporting evidence (index)

| ID | Evidence | Location / result |
|----|----------|-------------------|
| E1 | Live Preview empty for all stores | `GET /preview/executive-knowledge/api` → `record_count=0`, `stores=[]` |
| E2 | Live Preview empty for demo | `...?store_slug=demo` → `empty=true`, `honesty.status=empty_knowledge` |
| E3 | Preview flag ON alone | `flag_enabled=true` while Knowledge still 0 |
| E4 | Findings/Guidance/INPUT remain OFF | Preview payload fields all `false` |
| E5 | Composer call-graph empty | Static scan: 0 non-package callers of compose helpers |
| E6 | Flags default OFF | `services/evidence_truth/flags_v1.py` |
| E7 | Dual-write no-op when OFF | `observation_shadow_dual_write_v1.py` L98–105 |
| E8 | Knowledge store in-process | `knowledge_store_v1.py` module docstring + `_GLOBAL_KNOWLEDGE_STORE` |
| E9 | Preview reads Knowledge only | `executive_knowledge_preview_v1.py` docstring + `forbidden_inputs` |
| E10 | WP-ET-10: no production hooks / INPUT unwired | `docs/implementation/WP_ET_10_KNOWLEDGE_COMPOSER.md` |
| E11 | WP-ET-10.5: Preview ≠ cutover | `docs/implementation/WP_ET_10_5_EXECUTIVE_KNOWLEDGE_PREVIEW.md` |
| E12 | WP-ET-09: Bundle CONSUME unwired; no production hooks | `docs/implementation/WP_ET_09_EVIDENCE_BUNDLE_COMPOSER.md` |

---

## 5. Historical backfill required?

| Question | Answer |
|----------|--------|
| Has historical activity been processed by Observation→Evidence→Bundle→Knowledge? | **No** |
| Can existing historical Postgres / SRS data appear in Preview without new work? | **No** — different storage + no ingest path |
| Is backfill required for Preview to show historical knowledge? | **Yes, if product wants history** — as an **authorized** materialization program (replay / batch compose), not by toggling Preview |
| Does Knowledge require brand-new events after WP-ET-10? | **For forward-only shadow mode: yes** — and even then only if Observation + Evidence dual-write **and** Bundle + Knowledge compose are enabled **and** compose is actually scheduled. New events alone with current wiring still yield Knowledge = 0 |

---

## 6. Storage architecture must change?

| Question | Answer |
|----------|--------|
| Can production Preview read the same store the composer writes? | **Yes, within one process** — both use `get_knowledge_record_store_v1()`. |
| Is that sufficient for production? | **No for durability / multi-instance** — process-local singleton is a known soak gap (WP-ET-10). |
| Must storage change before truthful production Preview of durable Knowledge? | **Architecturally recommended** (durable shared store). Not required to explain current zeros — zeros occur even before storage durability is the blocker. |

**Verdict on storage:** Storage architecture is a **necessary future change for durable Preview**, but **not** the first-order reason Knowledge is empty today. First-order reasons are RC-1…RC-5.

---

## 7. Recommended corrective action (investigation only — do not implement)

Ordered for Architectural Review:

1. **Decide materialization policy**  
   - Forward-only Shadow (new events after dual-write + compose schedule), **or**  
   - Historical backfill / replay into ET Observation→Evidence→Bundle→Knowledge  

2. **If forward-only:** authorize a controlled enablement sequence (not Preview alone):  
   - Observation dual-write soak → Evidence dual-write soak → Bundle shadow compose job → Knowledge shadow compose job → Preview remains read-only  

3. **Wire a single explicit compose scheduler / operator entrypoint** behind shadow flags (today: none on production call graph).  

4. **Plan durable shared Knowledge (and upstream) stores** before treating Preview as multi-worker truth.  

5. **Do not** enable Findings INPUT, Guidance, Home cutover, or WP-ET-11 as a shortcut to fill Preview.  

6. **Do not** fabricate Knowledge into the Preview store.

---

## 8. Architectural impact

| Area | Impact |
|------|--------|
| WP-ET-10.5 Preview | Validated as honest empty reader — keep |
| WP-ET-10 Knowledge Composer | Correct shadow library; missing **runtime invocation** |
| WP-ET-09 Bundle Composer | Same |
| WP-ET-03…08 dual-write | Idle unless flags ON; still does not compose Knowledge |
| Home / Findings / Guidance | Unchanged; correctly not activated |
| Identity / store mapping | Intact; not root cause of zeros |
| Parallel Knowledge Foundation / BFL | Unrelated store — must not be confused with KnowledgeRecordV1 |

---

## 9. Risk assessment

| Risk | Level | Notes |
|------|-------|-------|
| Misreading empty Preview as “product broken” | High (process) | Empty is correct; materialization unfinished |
| Enabling dual-write + compose without durable store | Medium | Worker asymmetry / loss on restart |
| Enabling Knowledge INPUT / Findings to “fill” Preview | **Critical governance** | Violates WP-ET-10/10.5 stop conditions |
| Silent historical backfill without Board approval | High | Constitutional / soak risk |
| store_slug chase | Low | Ruled out as primary |

---

## 10. Final verdict

**Verdict: EMPTY_BY_NON_MATERIALIZATION (EXPECTED UNDER CURRENT WIRING)**

Executive Knowledge Preview reports KnowledgeRecordV1 = 0 because:

1. Only the **Preview read flag** is ON.  
2. The ET pipeline that *creates* Knowledge is **not running** (upstream dual-write default OFF; Bundle/Knowledge composers **never called** in production).  
3. Shadow Knowledge is **process-local** and was never populated from historical merchant activity.  
4. This is **not** a Preview bug, **not** a `demo`/Zid slug mismatch primary failure, and **not** WP-ET-11.

**STOP — await Architectural Review.**  
Do not implement fixes, backfill, storage changes, or WP-ET-11 from this investigation alone.

---

## Appendix A — Flag matrix (defaults)

| Flag | Default | Wired? | Role |
|------|---------|--------|------|
| `CARTFLOW_EXECUTIVE_KNOWLEDGE_PREVIEW` | OFF | Yes (routes) | Read Preview |
| `CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE` | OFF | Yes (hooks) | Raw → Observation |
| `CARTFLOW_EVIDENCE_DUAL_WRITE` | OFF | Yes (hooks) | Observation → Evidence |
| `CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW` | OFF | Library only | Evidence → Bundle |
| `CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_CONSUME` | OFF | **Unwired** | Consume cutover |
| `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW` | OFF | Library only | Bundle → Knowledge |
| `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT` | OFF | **Unwired** | Knowledge consumer cutover |
| `CARTFLOW_EVIDENCE_FINDINGS_COMPOSER_INPUT` | OFF | **Unwired** | WP-ET-11+ |

## Appendix B — Knowledge Composer status checklist

| Hypothesis | Status |
|------------|--------|
| Disabled by flag | **True** (default OFF; production not shown enabling SHADOW) |
| Never executed in production | **True** (call-graph = 0) |
| Feature-flagged | **True** |
| Executed but produced zero | **False** (no execution) |
| Executed but failed eligibility | **False** (no execution) |
| Executed but discarded outputs | **False** (no execution) |

## Appendix C — Store identity notes

| Store | Identity |
|-------|----------|
| `demo` | Canonical commerce-lab / SRS slug; Preview filter normalizes case |
| Zid development store | Resolved via Identity Authority → `Store` row / aliases (`zid_store_id`, permalink, etc.). Exact production slug not required to explain zeros: global `stores=[]` |

---

**End of investigation.**
