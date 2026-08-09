# 04 — Responsive Validation

Validated viewports: 1440 · 1024 · 430 · 390

See `responsive_overflow_probe.json` after Living Store capture.

Required invariants:
- no page-level horizontal overflow
- GlobalUpbar may scroll internally
- PageStage width ≤ viewport
- contextual open does not expand shell width
- UtilityRow + GlobalUpbar remain stable
