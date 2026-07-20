# -*- coding: utf-8 -*-
"""
Product Metrics Foundation V1 — production/demo validation helper.

1) Ensure Demo has signals (optional cart-event)
2) GET /dev/product-metrics-foundation?store=demo
3) Require deterministic=true and ok=true

Usage:
  python scripts/_verify_product_metrics_foundation_v1.py --base https://smartreplyai.net --store demo
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _request_json(url: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body) if body else {}
            except json.JSONDecodeError:
                parsed = {"raw": body[:500]}
            return int(resp.status), parsed if isinstance(parsed, dict) else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"raw": body[:500]}
        return int(exc.code), parsed if isinstance(parsed, dict) else {}
    except URLError as exc:
        return 0, {"error": str(exc)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://smartreplyai.net")
    ap.add_argument("--store", default="demo")
    ap.add_argument("--skip-cart-event", action="store_true")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    post_status, post_body = 200, {"skipped": True}
    if not args.skip_cart_event:
        sid = f"pmf-verify-{uuid.uuid4().hex[:12]}"
        payload = {
            "event": "cart_state_sync",
            "store": args.store,
            "store_slug": args.store,
            "session_id": sid,
            "cart_id": f"cart-{sid[-8:]}",
            "reason": "add",
            "lines": [
                {
                    "product_id": "demo_pmf_probe",
                    "name": "PMF Probe Product",
                    "unit_price": 25,
                    "quantity": 1,
                }
            ],
        }
        post_status, post_body = _request_json(
            f"{base}/api/cart-event", method="POST", payload=payload
        )

    probe_status, probe_body = _request_json(
        f"{base}/dev/product-metrics-foundation?store={args.store}"
    )
    # Second call must match fingerprint (determinism across requests)
    probe2_status, probe2_body = _request_json(
        f"{base}/dev/product-metrics-foundation?store={args.store}"
    )
    fp1 = str(probe_body.get("canonical_fingerprint") or "")
    fp2 = str(probe2_body.get("canonical_fingerprint") or "")
    report = {
        "ok": bool(
            post_status == 200
            and probe_status == 200
            and probe2_status == 200
            and probe_body.get("ok")
            and probe_body.get("table_exists")
            and probe_body.get("deterministic") is True
            and fp1
            and fp1 == fp2
            and int(probe_body.get("signal_row_count") or 0) > 0
        ),
        "http_status_cart_event": post_status,
        "http_status_probe": probe_status,
        "http_status_probe_2": probe2_status,
        "store": args.store,
        "cart_event": post_body if not args.skip_cart_event else {"skipped": True},
        "fingerprint_match": bool(fp1 and fp1 == fp2),
        "probe": probe_body,
        "probe_2_fingerprint": fp2,
    }
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
