# Home Performance Hardening V1

**Status:** Implementation + production validation  
**Scope:** Home `/api/dashboard/summary` only — measurement-first performance.

## Deliverables

| # | Artifact |
|---|----------|
| 1 | Full execution timeline — `?home_perf=1` → `_home_perf_timeline_v1` |
| 2 | Latency flame / top stages — `top_stages` in timeline |
| 3 | Top bottlenecks — see ROOT_CAUSE + prod_measure |
| 4 | Root cause report — `ROOT_CAUSE_V1.md` |
| 5 | Optimization — stale snapshot no longer forces DEGRADED composition |
| 6 | Before / after — baseline 3.3s vs prod_measure |
| 7 | Production measurements — `prod_measure.json` |

## How to measure

```bash
python scripts/_home_performance_hardening_prod_v1.py
```

Living Store session only. Opt-in timeline does not change merchant paint.

## Success definition

We know exactly why Home was slow, removed the dominant bottleneck, and measurements prove it.

## STOP

No Collector Prioritization. No new observables. No other pages.
