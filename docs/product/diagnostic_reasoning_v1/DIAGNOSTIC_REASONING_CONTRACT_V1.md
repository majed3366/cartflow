# Diagnostic Reasoning Contract V1

**Status:** Implemented  
**Version:** `diagnostic_reasoning_v1`

## Chain

Observation → Evidence → Competing Causes → Best-Supported Diagnosis → Confidence → Recommendation → Merchant Publication

## Fields

See `services/diagnostic_reasoning_v1/contract_v1.py`.

## Evidence gate

No causal `selected_diagnosis` unless evidence distinguishes it from competing causes.  
Otherwise: `diagnosis_status = insufficient_evidence` or `conflicting_evidence`.

## Home

Home reads `diagnostic_publication_v1` from persisted snapshots only.  
No request-time compose / ORV / facts / situations when snapshot HES is ready.
