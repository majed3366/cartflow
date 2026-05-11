/**
 * Stress / load: reason capture + cart abandon (widget-style API).
 *
 * Smoke (default): low VUs — CI-friendly.
 * Full: set LOAD_PROFILE=full and tune VUs (requires PostgreSQL + sized app tier).
 *
 *   k6 run -e CARTFLOW_BASE_URL=http://127.0.0.1:8000 synthetic/k6/widget-recovery-stress.js
 *   LOAD_PROFILE=full k6 run -e CARTFLOW_BASE_URL=https://staging.example.com synthetic/k6/widget-recovery-stress.js
 *
 * After run, generate HTML/PDF path:
 *   python scripts/reports/k6_summary_to_html.py synthetic/reports/k6-summary.json synthetic/reports/k6-report.html
 *
 * k6 v0.49+: --summary-export=synthetic/reports/k6-summary.json
 */
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = (__ENV.CARTFLOW_BASE_URL || "http://127.0.0.1:8000").replace(
  /\/+$/,
  "",
);
const PROFILE = (__ENV.LOAD_PROFILE || "smoke").toLowerCase();
const FULL_VUS = parseInt(__ENV.FULL_TARGET_VUS || "5000", 10);

const smokeOptions = {
  scenarios: {
    widget_flow: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "20s", target: 30 },
        { duration: "40s", target: 30 },
        { duration: "15s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<1000"],
  },
};

const fullOptions = {
  scenarios: {
    peak: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "2m", target: Math.min(FULL_VUS, 2000) },
        { duration: "3m", target: FULL_VUS },
        { duration: "2m", target: FULL_VUS },
        { duration: "1m", target: 0 },
      ],
      gracefulRampDown: "30s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.02"],
    http_req_duration: ["p(95)<1000"],
  },
};

export const options = PROFILE === "full" ? fullOptions : smokeOptions;

function postJson(path, body) {
  return http.post(`${BASE}${path}`, JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    tags: { name: path },
  });
}

export default function () {
  const sid = `k6-${__VU}-${__ITER}-${Date.now()}`;
  const slug = "demo";

  let r = http.get(`${BASE}/health?db=1`);
  check(r, { "health+db 200": (x) => x.status === 200 });

  r = postJson("/api/cart-recovery/reason", {
    store_slug: slug,
    session_id: sid,
    reason_tag: "price_high",
  });
  check(r, {
    "reason saved": (x) => x.status === 200 && String(x.body || "").includes('"saved":true'),
  });

  r = postJson("/api/cart-event", {
    event: "cart_abandoned",
    store: slug,
    session_id: sid,
    cart_id: `${sid}_cart`,
    cart: [{ name: "k6 load item", price: 199.0, category: "إلكترونيات" }],
  });
  check(r, {
    "cart-event ok": (x) =>
      x.status === 200 && String(x.body || "").includes('"ok":true'),
  });

  sleep(0.05 + Math.random() * 0.15);
}

function htmlReport(data) {
  const m = data.metrics || {};
  const dur = m.http_req_duration?.values || {};
  const fail = m.http_req_failed?.values || {};
  const p50 = dur.med ?? dur["avg"] ?? "-";
  const p95 = dur["p(95)"] ?? "-";
  const p99 = dur["p(99)"] ?? "-";
  const max = dur.max ?? "-";
  const failRate = fail.rate != null ? (100 * fail.rate).toFixed(3) + "%" : "-";
  const ts = new Date().toISOString();
  return `<!DOCTYPE html><html><head><meta charset="utf-8"/><title>CartFlow k6 report</title>
<style>body{font-family:system-ui,sans-serif;margin:24px;}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:8px}</style>
</head><body>
<h1>CartFlow load test — ${ts}</h1>
<p><strong>Profile:</strong> ${PROFILE} &nbsp; <strong>Base URL:</strong> ${BASE}</p>
<h2>Latency (http_req_duration)</h2>
<table><tr><th>p50/med</th><th>p(95)</th><th>p(99)</th><th>max</th></tr>
<tr><td>${p50}</td><td>${p95}</td><td>${p99}</td><td>${max}</td></tr></table>
<h2>Reliability</h2>
<table><tr><th>http_req_failed rate</th></tr><tr><td>${failRate}</td></tr></table>
<p>Target: p(95) &lt; 1000 ms, low error rate. Print this page to PDF from the browser for the formal deliverable.</p>
<p><em>Curves:</em> import k6 JSON into Grafana or re-run with <code>k6 run --out influxdb=...</code> for time-series charts.</p>
</body></html>`;
}

function textSummaryPlain(data) {
  const lines = ["\n// summary\n"];
  const m = data.metrics || {};
  for (const k of Object.keys(m).sort()) {
    const v = m[k];
    if (v && v.values) {
      lines.push(`${k}: ${JSON.stringify(v.values)}`);
    }
  }
  return lines.join("\n");
}

export function handleSummary(data) {
  return {
    stdout: textSummaryPlain(data),
    "synthetic/reports/k6-last-run.html": htmlReport(data),
  };
}
