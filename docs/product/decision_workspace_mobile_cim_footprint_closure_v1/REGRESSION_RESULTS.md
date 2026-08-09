# Regression Results — Mobile CIM Footprint Closure V1

**Deploy:** `d52da0b0d035c8074d652462cf82951a43f26033`

## Gates (`production_probe.json`)

| Gate | Result |
|------|--------|
| deployOk | true |
| shellUntouched | true |
| hierarchyMarkerPresent | true |
| cimPresent430 / 390 | true |
| fieldCompressed430 / 390 (≤48px) | true |
| gapReduced430 / 390 (≤56px) | true |
| minHeightCleared430 / 390 | true |
| decisionOwns430 / 390 | true |
| noOverflow430 / 390 | true |
| desktopShellOk | true |
| desktopFieldUnchangedContract | true |

## Overflow (`mobile_overflow_probe.json`)

| Check | Result |
|-------|--------|
| noOverflow430 / 390 | true |
| offenderCount | 0 / 0 |

## Desktop safety

Desktop sparse fieldHeight remains **100px** (language default). No intentional desktop redesign.
