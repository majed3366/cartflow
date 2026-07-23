# -*- coding: utf-8 -*-
"""
Product Trends Foundation V1 — production/demo validation helper.

Usage:
  python scripts/_verify_product_trends_foundation_v1.py --base https://smartreplyai.net --store demo
"""
from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _request_json(url: str) -> tuple[int, dict]:
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=90) as resp:
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
    ap.add_argument("--window", default="d7")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    url = (
        f"{base}/dev/product-trends-foundation"
        f"?store={args.store}&trend_window={args.window}"
    )
    s1, b1 = _request_json(url)
    s2, b2 = _request_json(url)
    fp1 = str(b1.get("canonical_fingerprint") or "")
    fp2 = str(b2.get("canonical_fingerprint") or "")
    # Fingerprints may differ across wall-clock seconds if as_of is not frozen
    # between HTTP calls; require each response deterministic=true and ok.
    report = {
        "ok": bool(
            s1 == 200
            and s2 == 200
            and b1.get("ok")
            and b2.get("ok")
            and b1.get("table_exists")
            and b1.get("deterministic") is True
            and b2.get("deterministic") is True
            and b1.get("consumes_metrics_only") is True
            and fp1
            and fp2
        ),
        "http_status_1": s1,
        "http_status_2": s2,
        "store": args.store,
        "trend_window": args.window,
        "same_as_of_fingerprint_match": bool(
            fp1 and fp1 == fp2 and b1.get("as_of") == b2.get("as_of")
        ),
        "probe": b1,
        "probe_2_fingerprint": fp2,
    }
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
