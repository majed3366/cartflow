# Evidence Expansion V1 — Pre-merge confirmation

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Gaps isolated by store and diagnosis family | **PASS** | `gap_id` = hash(`store\|family\|diagnostic_id\|version`); row stores `store_slug` + `diagnostic_family`; list filters by store; tests assert distinct ids across stores/families |
| 2 | Repeated materialization idempotent (no duplicates) | **PASS** | Upsert by unique `gap_id`; same content → `mode=touch`; tests assert stable `gap_id` on recompose |
| 3 | Resolved / superseded lifecycle states governed | **PASS** | Contract statuses: `open`, `partially_filled`, `resolved`, `superseded`, `suppressed`; validation rejects unknown statuses |
| 4 | Gap creation never on Home request path | **PASS** | Register only from diagnostic materialize (snapshot builder / CLI / allowlisted `/dev` probe); Home finalize modules have zero references |
| 5 | Home payloads contain no evidence-gap fields | **PASS** | No attach into summary/HES/publication; builder records expansion metrics in internal tick `results` only |
| 6 | Catalog entries identify which diagnosis they improve | **PASS** | Each `OBSERVABLE_CATALOG_V1` entry has `diagnosis_families` + `separates_causes` |
| 7 | No collector without separate approved task | **PASS** | No collector modules in package; docs STOP until architecture approval |
| 8 | Diagnostic + Home tests remain green | **PASS** | See CI / local pytest on diagnostic + home diagnosis suites |

**STOP:** Do not merge collectors. Do not activate storefront/widget collection until explicit approval after architecture review.
