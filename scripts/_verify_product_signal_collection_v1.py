# -*- coding: utf-8 -*-
"""
Product Signal Collection V1 — production/demo validation helper.

1) POST cart_state_sync with lines for Demo store
2) Query local/prod signal count via optional DATABASE_URL (or print HTTP ok)

Usage (local against running app):
  python scripts/_verify_product_signal_collection_v1.py --base https://smartreplyai.net

Does not add merchant UI. Safe facts-only probe.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _post_json(url: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
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
    args = ap.parse_args()
    base = args.base.rstrip("/")
    sid = f"psc-verify-{uuid.uuid4().hex[:12]}"
    payload = {
        "event": "cart_state_sync",
        "store": args.store,
        "store_slug": args.store,
        "session_id": sid,
        "cart_id": f"cart-{sid[-8:]}",
        "reason": "add",
        "lines": [
            {
                "product_id": "demo_psc_probe",
                "name": "PSC Probe Product",
                "unit_price": 25,
                "quantity": 1,
            }
        ],
    }
    status, body = _post_json(f"{base}/api/cart-event", payload)
    print(
        json.dumps(
            {
                "ok": status == 200 and bool(body.get("ok", True)),
                "http_status": status,
                "store": args.store,
                "session_id": sid,
                "response_keys": sorted(list(body.keys()))[:20],
                "note": (
                    "Signal rows persist server-side when Product Signal Collection "
                    "is deployed; confirm via DB count for store_slug=demo."
                ),
            },
            indent=2,
        )
    )
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
