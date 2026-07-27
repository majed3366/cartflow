# Home Performance Hardening V1 — Audits

## Hot path (Stage 3)

| Item | Finding |
|------|---------|
| ORV / facts / themes / situations / publication on Home | **Removed** for SNAPSHOT/CACHE/DEGRADED |
| Double finalize | Skipped when Home exit already complete |
| Diagnostic read | Kept; ~15–26 ms; now dominant server stage |
| `dashboard_snapshots` miss (`no_snapshot`) | Still a coverage issue for builder; no longer forces multi-second ORV |

## Query audit (Stage 5)

After fix, Home snapshot path queries are bounded:

1. Resolve store slug / session (pre-existing)
2. `dashboard_snapshots` latest row (`LIMIT 1`) — miss path returns stub
3. `diagnostic_snapshots` read for publication attach

No duplicated ORV/history scans on Home. Expensive ORV SQL remains **LIVE builder only**.

## Serialization audit (Stage 6)

`json_serialize_measure` &lt; 1 ms for ~39KB payload — **under 50 ms**. No serialization fix required.

## Network vs server (Stage 7)

| Component | After (warm desktop) |
|-----------|----------------------|
| Server | ~26 ms timeline |
| Database (snapshot + diagnostic reads) | ~8 + ~16 ms inside timeline |
| Serialization | &lt;1 ms |
| Network + browser (client api_ms − server) | ~190 ms |
| Browser rendering | Not in API budget (paint separate) |
