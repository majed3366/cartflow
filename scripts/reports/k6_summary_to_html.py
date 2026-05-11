#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert k6 --summary-export=summary.json into a simple HTML report (print to PDF from browser).

Usage:
  k6 run --summary-export=synthetic/reports/k6-summary.json synthetic/k6/widget-recovery-stress.js
  python scripts/reports/k6_summary_to_html.py synthetic/reports/k6-summary.json synthetic/reports/k6-report.html
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: k6_summary_to_html.py <summary.json> <out.html>", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    data = json.loads(src.read_text(encoding="utf-8"))
    metrics = data.get("metrics") or {}
    dur = (metrics.get("http_req_duration") or {}).get("values") or {}
    fail = (metrics.get("http_req_failed") or {}).get("values") or {}
    checks = (metrics.get("checks") or {}).get("values") or {}

    def fmt(v: object) -> str:
        if v is None:
            return "—"
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)

    fail_rate = fail.get("rate")
    fail_pct = f"{100.0 * float(fail_rate):.3f}%" if fail_rate is not None else "—"

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>CartFlow k6 summary</title>
<style>body{{font-family:system-ui,sans-serif;margin:24px}}table{{border-collapse:collapse}}th,td{{border:1px solid #ccc;padding:8px}}</style>
</head><body>
<h1>CartFlow k6 summary report</h1>
<p>Source: <code>{src.name}</code></p>
<h2>http_req_duration</h2>
<table>
<tr><th>avg</th><th>med</th><th>p(90)</th><th>p(95)</th><th>p(99)</th><th>max</th></tr>
<tr>
<td>{fmt(dur.get('avg'))}</td>
<td>{fmt(dur.get('med'))}</td>
<td>{fmt(dur.get('p(90)'))}</td>
<td>{fmt(dur.get('p(95)'))}</td>
<td>{fmt(dur.get('p(99)'))}</td>
<td>{fmt(dur.get('max'))}</td>
</tr>
</table>
<h2>http_req_failed</h2>
<p>Rate: <strong>{fail_pct}</strong></p>
<h2>checks</h2>
<p>Pass rate: <strong>{fmt(checks.get('rate'))}</strong> (if present)</p>
<p><em>Enterprise criterion:</em> p(95) latency under budget, error rate near zero. Attach Grafana screenshots for time-series if using Influx/Cloud.</p>
</body></html>"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(html, encoding="utf-8")
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
