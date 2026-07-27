# Diagnostic Snapshot Design V1

**Table:** `diagnostic_snapshots`  
**Model:** `DiagnosticSnapshot`  
**Store:** `snapshot_store_v1.py`

## Properties

- Unique on `(store_slug, subject_type, subject_id, diagnostic_family)`
- Idempotent via `content_hash`
- Bounded evidence window on contract
- `expires_at` + stale last-good serve
- Versioned `diagnostic_version`
- On persist failure: keep last-good; never blank Home; never recompose on request
