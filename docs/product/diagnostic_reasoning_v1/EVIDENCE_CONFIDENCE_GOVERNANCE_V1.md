# Evidence and Confidence Governance V1

## Scoring inputs

- Strong subtype signal volume (e.g. `shipping_cost`)
- Weak generic signals (e.g. `shipping`) — never alone select a subtype
- Contradicting signals
- Diversity, recurrence, product identity
- Minimum sample

## Tie-break

If top two causal scores differ by ≤ `TIE_MARGIN_V1` (2.0):  
`diagnosis_status = conflicting_evidence` — no arbitrary winner.

## Confidence

- high / medium / low / insufficient  
Painted confidence math is **not** shown on Home.
