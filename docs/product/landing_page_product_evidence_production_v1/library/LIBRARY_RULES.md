# Landing Evidence Library Rules

**Library root:** `docs/product/landing_page_product_evidence_production_v1/library/`  
**Date (UTC):** 2026-07-29  

## Asset folder layout

```text
library/EV-XXX/
  candidate.png          # ingested candidate (not yet publication-approved)
  approved.png           # only after Acceptance Result = pass + status Production Ready
  meta.json              # version, dates, scenario, sections, status
```

## meta.json required fields

```json
{
  "evidence_id": "EV-010",
  "name": "Home Dashboard",
  "version": 1,
  "capture_date_utc": "YYYY-MM-DD",
  "product_version_note": "face/pack reference",
  "scenario_id": "SCN-...",
  "source_path": "original path before ingest",
  "landing_sections": ["LP-08"],
  "status": "Ready After Fresh Capture",
  "last_verification_utc": "YYYY-MM-DD",
  "replacement_history": [],
  "retirement_history": [],
  "sensitive_data_review": "pass|fail|pending",
  "arabic_readiness": "pass|fail|pending",
  "acceptance_result": "pending|pass|fail"
}
```

## Status vocabulary

`Production Ready` · `Ready After Fresh Capture` · `Requires Reality Validation` · `Requires Operational Verification` · `Requires UI Polish` · `Blocked` · `Deferred` · `Outdated` · `Rejected Ineligible`

## Change management

If product UI or behaviour invalidates an asset → set status **`Outdated`** immediately.  
Must be reproduced, recaptured, and reapproved before landing use.  
Never silently keep outdated assets in future landing pages.

## Rejected folder

`library/_rejected_ineligible/` holds known ineligible references (e.g. settings screenshots) so they are never promoted.
