# Reality Replay Gate A — INV-001 (after WP-5)

| Field | Value |
|-------|-------|
| Gate | **A** |
| After | WP-5 Dashboard/Home Time Authority Migration |
| Date (UTC) | 2026-07-16 |
| Branch | `feature/inv001-wp5` |
| Decision | ☐ Approved — **awaiting Architecture Review** |

## Frozen requirement (Execution Blueprint §7)

> `demo` May history: as-of/sim-end context → Knowledge + Dashboard agree non-denial; production context → typed out-of-window (not silent no-data) when history exists.

## Evidence pack

| Artifact | Path |
|----------|------|
| Machine evidence | `docs/architecture/reality_replay_gate_a_wp5/gate_a_evidence.json` |
| Automated proof | `tests/time_authority/test_wp5_reality_replay_gate_a.py` |

## Results (fixture class)

| Context | Knowledge `cart_count` (7d) | Dashboard `abandoned_total` (7d) | Windows equal |
|---------|----------------------------:|--------------------------------:|:-------------:|
| July production inject | 0 | 0 | Yes |
| Simulation as-of 2026-05-04 | 27 | 27 | Yes |

History rows exist in both contexts; July emptiness is **out-of-window**, not missing store data. Same Query Time Context ⇒ identical `[start, end)` for Knowledge and Dashboard.

## Verdict

**PASS** (automated Gate A pack). Full Reality Lab V1 campaign remains **WP-13**.

## Stop

Do **not** begin WP-6 until Architecture Review approves Gate A.
