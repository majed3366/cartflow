# Reality Validation Identity Certification V1

## Constitutional rule

No screenshot, UX review, Product Review, Product decision, or Gate closure may proceed while:

```text
CEO_REVIEW_SAFE = FALSE
```

Without this certification, every CEO review is **invalid**.

## Probe

```http
GET /dev/reality-validation-context?store=demo
GET /dev/reality-validation-context?store=demo&format=html
```

Use the HTML form for the mandatory pre-review screenshot.

## Required before every CEO review

Screenshot must show:

- `Status = CONSISTENT`
- `CEO_REVIEW_SAFE = TRUE`

Only then may Home and Decision Workspace be reviewed.

## CEO_REVIEW_SAFE = TRUE only if

- Production environment
- Production database (not sqlite)
- `store_slug = demo`
- Browser session resolves to `demo`
- Living Store `simulation_run_id` present (`living_store` profile)
- Living Store timestamp present
- Observations / Business Facts / Commerce Situations non-empty
- Identity status `CONSISTENT` across all surfaces
- Home projection non-empty

## Identity matrix

Environment · Database · Store Slug · Merchant Session · Simulation Run · Living Store Profile · Timestamp · Observation / Facts / Situation counts · Home · Workspace · Products · Carts · Communication · Status

## Divergence

When `INCONSISTENT`:

- `divergence_begins_at`
- `expected_value`
- `actual_value`
- `affected_surfaces`
- `recommendation`

## No scope creep

No UX work. No Product Intelligence. No feature work. Certification only.
