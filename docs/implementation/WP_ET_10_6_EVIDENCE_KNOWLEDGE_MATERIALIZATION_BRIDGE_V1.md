# WP-ET-10.6 — Evidence Knowledge Materialization Bridge V1

**Status:** Implementation complete — await merge + Architectural/Product Review  
**Date (UTC):** 2026-07-24  
**Scope:** Demo-only durable materialization bridge: Observation → Evidence → Bundle → KnowledgeRecordV1 → Executive Knowledge Preview  
**Out of scope:** WP-ET-11, Findings, Guidance, Home cutover, Zid materialization, fabricated Knowledge

---

## 1. Executive Summary

WP-ET-10.6 closes the **EMPTY_BY_NON_MATERIALIZATION** gap identified by the Executive Knowledge investigation: Preview was correct and empty because no governed path wrote durable KnowledgeRecordV1.

This package adds:

1. Durable SQL shadow artifact storage (shared across workers / restarts)
2. `EvidenceKnowledgeMaterializationOrchestratorV1` — bounded, idempotent, demo-only
3. Governed historical input contract (Purchase Truth, recovery logs, abandoned carts, validation fixtures)
4. Internal CLI for DRY RUN / EXECUTE
5. Preview durable Knowledge reads (still read-only; preview flag never materializes)

All new execution flags default **OFF**. Production Home / Findings / Guidance / WhatsApp unchanged.

---

## 2. Root cause addressed

| Investigation RC | Bridge fix |
|------------------|------------|
| RC-1 Preview ≠ materialization | Separate flags; Preview remains display-only |
| RC-2 Composers never invoked | Explicit orchestrator + CLI caller |
| RC-3 Dual-write idle | Orchestrator uses `force=True` for approved composers only inside EXECUTE |
| RC-4 Process-local stores | Durable `evidence_truth_shadow_artifacts` table |
| RC-5 No historical path | Demo-only input contract + bounded discovery |

---

## 3. Architecture

```text
Approved demo sources (Postgres / fixtures)
        ↓ governed input contract
Observation (normalize + dual-write force)
        ↓
Evidence Truth (family publishers force)
        ↓ durable put (idempotent)
Evidence Bundle (compose force)
        ↓ durable put
KnowledgeRecordV1 (compose force)
        ↓ durable put
Executive Knowledge Preview (read durable + in-process)
```

No merchant request hot path invokes the orchestrator. `main.py` has no orchestrator calls.

---

## 4. Durable storage design

| Table | Purpose |
|-------|---------|
| `evidence_truth_materialization_runs` | Run ledger (mode, status, accounting_json, run id) |
| `evidence_truth_shadow_artifacts` | Observation / Evidence / Bundle / Knowledge payloads |

Properties:

- store_slug isolated (`demo` enforced on write)
- unique `idempotency_key` (duplicate-safe)
- lineage_json + source_ref + materialization_run_id
- indexed by store_slug + artifact_kind
- Alembic: `j9k0l1m2n3o4`
- Schema helper: `schema_evidence_truth_materialization_v1.py`
- In-memory stores retained for unit tests / same-process compose

---

## 5. Input contract

Module: `services/evidence_truth/materialization_input_contract_v1.py`

| Eligible source type | Raw kind |
|----------------------|----------|
| `purchase_truth_record` | purchase |
| `cart_recovery_log` | recovery |
| `abandoned_cart` (demo identity alias) | cart_event |
| `validation_fixture` (explicit opt-in) | purchase / cart_event |

Policies:

- timestamp authority: platform record / fixture clock
- dedupe key: `{source_type}:{source_id}`
- replay: idempotent raw_ref / durable idempotency keys
- unsupported / incomplete / non-demo → explicit accounting buckets
- Observation required — no bypass into Evidence/Bundle/Knowledge
- Zid remap forbidden; non-demo abort

Bounded: `ORDER BY id DESC LIMIT batch_limit` (max 500).

---

## 6. Orchestrator lifecycle

Module: `services/evidence_truth/materialization_orchestrator_v1.py`  
Class: `EvidenceKnowledgeMaterializationOrchestratorV1`

1. Assert `store_slug == demo`
2. Gate on materialization flags (or `force` in tests)
3. Discover sources
4. DRY RUN → expected counts, no mutation
5. EXECUTE → per-source Observation+Evidence dual-write (force) → durable put → Bundle → Knowledge → durable put
6. Persist run ledger with stage accounting
7. Abort + report on non-demo escape

CLI: `scripts/run_evidence_knowledge_materialization_v1.py`

---

## 7. Feature flags

| Flag | Default | Role |
|------|---------|------|
| `CARTFLOW_EVIDENCE_KNOWLEDGE_MATERIALIZATION_V1` | OFF | Master gate (dry_run + execute) |
| `CARTFLOW_EVIDENCE_KNOWLEDGE_MATERIALIZATION_EXECUTE` | OFF | Mutation gate for EXECUTE |
| `CARTFLOW_EXECUTIVE_KNOWLEDGE_PREVIEW` | unchanged | Read/display only — never materializes |

Does **not** activate Findings INPUT, Guidance, Home, or all-store dual-write.

---

## 8. Demo isolation

- `assert_demo_store_slug_v1` on every durable write
- Orchestrator abort_non_demo on escape
- Discovery filters `store_slug == demo`
- Abandoned carts only via demo identity alias (no Zid remap)
- Tests prove non-demo rejection and no remapping helpers

---

## 9. Pipeline stage counts (test / fixture execute)

Typical fixture run (`fixture_count=1`, force=True):

| Stage | Created / reused |
|-------|------------------|
| Sources eligible | ≥2 (purchase + cart fixture) |
| Observations | created or reused |
| Evidence | created or reused |
| Bundles | 1 |
| Knowledge | 1 |

Exact production DRY RUN / EXECUTE counts are recorded in the post-deploy run report (§10–12 after approval).

---

## 10. Accounting reconciliation

Every discovered source lands in exactly one of:

- eligible
- unsupported
- duplicated
- rejected

Per-source outcomes record `stage_stopped` when a record fails.  
`discovery_balanced` must be true. Tests assert balance on dry_run and execute.

---

## 11. Knowledge outputs

Knowledge is composed only via `maybe_compose_knowledge_record_v1(..., force=True)` from Evidence Bundle — never hardcoded.

Preview merges durable Knowledge with in-process records; after simulated restart, durable records remain visible.

---

## 12. Suppressed outputs and reasons

Suppression remains honest:

- no evidence in batch → bundle suppressed
- no bundle → knowledge suppressed
- composer `missing_sources` / insufficient readiness → suppressed with reason
- WP-ET-10 vocabulary / readiness rules unchanged

---

## 13. Traceability examples

Each successful source outcome produces a traceability row:

```text
source_type/source_id/source_timestamp
  → observation_id
  → evidence_id
  → bundle_id
  → knowledge_id
  → materialization_run_id
  → idempotency_keys
```

Reconstruction path: Knowledge → Bundle → Evidence → Observation → source record (lineage_json).

---

## 14. Restart / durability proof

Tests:

- Execute materialization → reset all in-process stores → Preview still reads durable Knowledge
- Idempotent second run reuses durable artifact keys
- Cleanup by `materialization_run_id` cannot delete unrelated run artifacts

Production restart proof: after deploy + EXECUTE, Preview must remain non-empty across Railway redeploy (post-merge validation).

---

## 15. Production safety proof

| Constraint | Status |
|------------|--------|
| Home unchanged | No Home wiring |
| Merchant routes unchanged | No merchant route changes |
| WhatsApp unchanged | `outbound_calls=0` in accounting |
| Purchase Truth unchanged | Sources read-only |
| No non-demo writes | Enforced |
| No schema verify on request hot paths | Schema ensure only on materialization/durable access |
| No orchestrator in `main.py` | Static test |
| Findings/Guidance OFF | Asserted |

---

## 16. Test results

```text
Evidence Truth suite (WP-ET-00…10.6): 122 passed
WP-ET-10.6 file: 17 passed
```

Coverage includes: demo isolation, non-demo rejection, no Zid remap, deterministic/idempotent rerun, resume, bounded batch, no silent loss, unsupported/duplicate accounting, lineage, durable visibility, restart, Preview read-only, preview flag ≠ materialization, no Findings/Guidance/Home, no outbound, cleanup isolation, reconciliation, hot-path isolation, flag OFF.

---

## 17. Production screenshots

**Pending post-merge deploy validation** (flags OFF → DRY RUN → approved EXECUTE → Preview URLs).

Targets after approval:

- `https://smartreplyai.net/preview/executive-knowledge?store_slug=demo`
- `https://smartreplyai.net/preview/executive-knowledge/api?store_slug=demo`

---

## 18. Remaining limitations

- V1 authorized for `store_slug=demo` only
- No automatic recurring schedule
- Intermediate Observation/Evidence compose still uses in-process stores during a single EXECUTE (durable Knowledge is the Preview authority)
- Validation fixtures are opt-in (`--include-validation-fixtures`)
- Historical coverage limited to allowlisted source types + batch limit

---

## 19. Rollback plan

1. Keep `CARTFLOW_EVIDENCE_KNOWLEDGE_MATERIALIZATION_V1` / `_EXECUTE` OFF
2. Preview continues to work; durable rows idle
3. Optional: delete demo artifacts via `delete_demo_shadow_artifacts_v1(confirm_store_slug="demo")`
4. Alembic downgrade `j9k0l1m2n3o4` if tables must be removed
5. No Home/Findings rollback required (never activated)

---

## 20. Final verdict

**WP-ET-10.6 implementation ready for PR merge.**

Correctness, honesty, lineage, and durability foundations are in place.  
A non-zero production Knowledge count requires an approved post-merge DRY RUN → EXECUTE for `demo`.

**STOP — do not begin WP-ET-11. Do not connect Knowledge to production Home.**

---

## Deliverable index

| Artifact | Path |
|----------|------|
| Flags | `services/evidence_truth/materialization_flags_v1.py` |
| Durable store | `services/evidence_truth/durable_shadow_store_v1.py` |
| Input contract | `services/evidence_truth/materialization_input_contract_v1.py` |
| Orchestrator | `services/evidence_truth/materialization_orchestrator_v1.py` |
| Serde | `services/evidence_truth/materialization_serde_v1.py` |
| CLI | `scripts/run_evidence_knowledge_materialization_v1.py` |
| Models | `EvidenceTruthMaterializationRun`, `EvidenceTruthShadowArtifact` |
| Alembic | `alembic/versions/j9k0l1m2n3o4_add_evidence_truth_materialization_v1.py` |
| Tests | `tests/test_evidence_truth_wp_et_10_6_materialization_bridge_v1.py` |
| Preview durable read | `services/evidence_truth/executive_knowledge_preview_v1.py` |
