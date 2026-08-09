# Regression Results — Mobile Hierarchy Refinement V1

**Deploy SHA:** `79211357fd5ebe6ff29c64db4192ccdbc7b792f5`

## Automated gates (`production_probe.json`)

| Gate | Result |
|------|--------|
| deployOk | true |
| markerPresent | true |
| shellUntouched | true |
| decisionOwns430 / 390 | true |
| titleAboveStatus430 / 390 | true |
| decisionInFirstViewport430 / 390 | true |
| noOverflowX430 / 390 | true |
| desktopShellOk | true |
| desktopDecisionPresent | true |
| commerceInMotion | true |
| desktopMassStillDominant | true |

## Overflow (`mobile_overflow_probe.json`)

| Check | Result |
|-------|--------|
| noOverflow430 | true |
| noOverflow390 | true |
| offenderCount430 | 0 |
| offenderCount390 | 0 |

## Desktop safety

- Shell marker still `shell-integration-v1`
- Desktop mass font-size ≥ title (composition closure contract retained)
- No intentional desktop redesign

## Shell / navigation

Not modified in this task.
