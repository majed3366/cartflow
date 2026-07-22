# -*- coding: utf-8 -*-
"""
Merchant Experience Integration Foundation V1 — production/demo validation helper.

Usage:
  python scripts/_verify_merchant_experience_v1.py --base https://smartreplyai.net --store demo
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
        with urlopen(req, timeout=180) as resp:
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
        f"{base}/dev/merchant-experience"
        f"?store={args.store}&assembly_window={args.window}"
    )
    status, body = _request_json(url)
    highs = body.get("mev1_high_resolution") or {}
    report = {
        "ok": bool(
            status == 200
            and body.get("ok")
            and body.get("foundation_enabled")
            and body.get("registries_valid")
            and int(body.get("governed_consumption_pct") or 0) == 100
            and body.get("navigation_integrity") is True
            and body.get("routing_integrity") is True
            and body.get("canonical_fingerprint")
            and (all(bool(v) for v in highs.values()) if highs else False)
            and not (body.get("integration_failures") or [])
        ),
        "http_status": status,
        "store": args.store,
        "assembly_window": args.window,
        "probe": body,
    }
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
