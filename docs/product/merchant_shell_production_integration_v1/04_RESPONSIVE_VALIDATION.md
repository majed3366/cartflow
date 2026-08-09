# 04 — Responsive Validation

**Deploy SHA:** `111456b`

| Viewport | pageOverflow | stageOverflow | rootOverflow | ok |
|----------|--------------|---------------|--------------|-----|
| 1440 Home/Workspace | false | false | false | true |
| 1024 | false | false | false | true |
| 430 Home/Workspace | false | false | false | true |
| 390 Home/Workspace | false | false | false | true |

GlobalUpbar may scroll internally (`#cf2-nav`). Page does not gain horizontal scroll.

Raw: `responsive_overflow_probe.json`
