# WP-ET-10.5 — Executive Knowledge Preview (Validation Surface)

**Status:** Implemented — await Executive Home Review  
**Date (UTC):** 2026-07-24  
**Package:** WP-ET-10.5 (temporary validation surface)  
**Dependencies:** WP-ET-10 Knowledge Composer shadow; Evidence Bundle Constitution V1  
**Type:** Validation only — **not** production Home · **not** consumer cutover  

**Rollback:** Unset `CARTFLOW_EXECUTIVE_KNOWLEDGE_PREVIEW` (default OFF). Preview routes return 404. No Home/Findings impact.

---

## 1. Scope

### In scope

| Item | Delivered |
|------|-----------|
| Temporary Executive Knowledge Preview | Yes |
| Consume Shadow Knowledge only | Yes |
| Feature flag default OFF | Yes |
| Honest empty Knowledge state | Yes |
| Read-only HTML + JSON API | Yes |
| Architecture validation questions surfaced | Yes |

### Out of scope (explicit)

- Production Home redesign or replacement  
- Knowledge INPUT cutover  
- Business Findings (WP-ET-11)  
- Guidance / recommendations / AI  
- Merchant production experience changes  
- Fabricated / placeholder insights  

---

## 2. Preview architecture

```text
Shadow Knowledge Store (WP-ET-10)
        ↓ read only
executive_knowledge_preview_v1 (builder)
        ↓
/preview/executive-knowledge      (HTML)
/preview/executive-knowledge/api  (JSON)
```

| Component | Path |
|-----------|------|
| Flag + builder | `services/evidence_truth/executive_knowledge_preview_v1.py` |
| Knowledge list helpers | `services/evidence_truth/knowledge_store_v1.py` (`list_recent`, `list_store_slugs`) |
| Routes | `routes/executive_knowledge_preview_v1.py` |
| HTML | `static/executive_knowledge_preview_v1.html` |
| Wiring | `main.py` include_router (flag still gates 404) |
| Eligibility | `executive_knowledge_preview` permitted on Knowledge artifacts |

**Forbidden inputs (enforced by architecture + import discipline):** Raw Event, Observation, Evidence Truth, Evidence Bundle. Preview never calls those stores.

---

## 3. Feature flag

| Flag | Default | Effect |
|------|---------|--------|
| `CARTFLOW_EXECUTIVE_KNOWLEDGE_PREVIEW` | **OFF** | OFF → HTTP 404 / disabled payload; ON → validation surface readable |

Not the same as `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT` (remains OFF / unwired).  
Enabling Preview does **not** enable Knowledge consumers, Findings, or Guidance.

---

## 4. Safety guarantees

| Guarantee | How |
|-----------|-----|
| Not Home | `production_home=false`; distinct `/preview/…` path; page banner |
| No cutover | Knowledge INPUT / Findings flags untouched |
| Read only | Builder only lists Knowledge store; no compose/write APIs |
| No mutations | No store puts from preview path |
| No production routing | Not wired into Home / Brief / merchant dashboard |
| Fail closed when OFF | 404 JSON/HTML |
| No fabricated insights | Empty store → honest “Knowledge has nothing to say” |
| No recommendations | Forbidden Findings/Guidance fields not rendered |

---

## 5. Knowledge consumed

| Input | Used? |
|-------|-------|
| Shadow `KnowledgeRecordV1` | **Yes** — sole input |
| Evidence Bundle | No |
| Evidence Truth | No |
| Observation | No |
| Raw Event | No |

Preview projects existing Knowledge fields into executive sections. It does not invent patterns.

To populate for Architecture Review: compose Shadow Knowledge via WP-ET-10 (harness / `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW` + Bundle seed), then enable Preview flag.

---

## 6. Screens rendered

| Surface | URL | Content |
|---------|-----|---------|
| HTML lab | `/preview/executive-knowledge` | Validation UI (flag ON) |
| JSON API | `/preview/executive-knowledge/api?store_slug=` | Structured preview payload |

**Sections (Knowledge statements only):**

1. What does CartFlow currently know?  
2. Which patterns are stable? (readiness Ready/Trusted)  
3. Which patterns are still immature?  
4. Where is evidence still insufficient?  
5. What changed recently? (newest shadow records first — no invented deltas)

---

## 7. Validation scenarios

| Scenario | Expected |
|----------|----------|
| Flag OFF | 404; production unchanged |
| Flag ON, empty Knowledge store | Honest empty message; no fake cards |
| Flag ON, seeded Knowledge | Real pattern statements from WP-ET-10 records |
| Import scan | Preview module does not import Evidence/Observation/Bundle stores |
| Eligibility | Preview allowed; Home/Findings prohibited |

---

## 8. Remaining limitations

| Limitation | Notes |
|------------|-------|
| In-process Knowledge store | Preview sees only process-local shadow Knowledge |
| Pattern vocabulary limited | WP-ET-10 types only (presence / ready-family set) |
| Not multi-worker shared | Same durability gap as WP-ET-09/10 shadow stores |
| Not Executive Home | Must never be promoted to production Home without new Architecture authorization |
| No historical analytics | “Recent” = store recency, not merchant timeline product |

---

## 9. Stop point

**WP-ET-10.5 complete as temporary validation surface.**

Do **not** begin WP-ET-11.  
Wait for **Executive Home Review**.  
Only after architectural approval may WP-ET-11 begin.

**STOP.**
