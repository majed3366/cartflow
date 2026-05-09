/**
 * Light smoke / readiness checks — not a load or stress test.
 * Requires k6: https://k6.io/docs/getting-started/installation/
 *
 *   k6 run -e CARTFLOW_BASE_URL=http://127.0.0.1:8000 synthetic/k6/smoke.js
 */
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 1,
  iterations: 8,
  thresholds: {
    http_req_failed: ["rate<0.1"],
  },
};

const BASE = (__ENV.CARTFLOW_BASE_URL || "http://127.0.0.1:8000").replace(
  /\/+$/,
  "",
);

export default function () {
  let r = http.get(`${BASE}/health`);
  check(r, { "health 200": (x) => x.status === 200 });

  r = http.get(`${BASE}/dashboard/normal-carts`);
  check(r, { "normal-carts 200": (x) => x.status === 200 });

  r = http.get(`${BASE}/api/recovery-settings`);
  check(r, { "recovery-settings 200": (x) => x.status === 200 });

  const cartPayload = JSON.stringify({
    event: "cart_abandoned",
    store: "demo",
    session_id: `k6-smoke-${__VU}-${Date.now()}`,
    cart: [{ name: "k6 synthetic item", price: 10 }],
  });
  r = http.post(`${BASE}/api/cart-event`, cartPayload, {
    headers: { "Content-Type": "application/json" },
  });
  check(r, { "cart-event 200": (x) => x.status === 200 });

  r = http.get(`${BASE}/admin/operations/login`);
  check(r, { "admin login 200": (x) => x.status === 200 });

  sleep(0.3);
}
