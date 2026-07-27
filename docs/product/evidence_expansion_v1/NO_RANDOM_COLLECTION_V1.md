# No Random Data Collection V1

## Rule

Do **not** collect signals because they might be useful.

Every new observable must satisfy:

> Which diagnosis becomes more accurate if we collect this?

If no diagnosis family benefits — **do not collect it**.

## Enforcement in code

`services/evidence_expansion_v1/observable_registry_v1.py`:

1. `OBSERVABLE_CATALOG_V1` — each key declares:
   - `separates_causes` (which causes it distinguishes)
   - `diagnosis_families` (which families benefit)
2. `assert_observable_benefits_diagnosis_v1(key)` — false if either list is empty
3. `observables_for_family_v1` — skips catalog entries that do not benefit the family

## Review gate before collectors

Adding a collector / widget signal requires:

1. Catalog entry with non-empty `separates_causes` + `diagnosis_families`
2. Family list update in `FAMILY_MISSING_OBSERVABLES_V1`
3. Explicit architecture approval (this pack)
4. Link from an open Evidence Gap (preferred)

Catalog entries alone do **not** collect data. Collectors are a separate, gated phase.
