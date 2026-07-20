# -*- coding: utf-8 -*-
"""
Product Evidence Assembly Foundation V1 — production/demo validation helper.

Usage:
  python scripts/_verify_product_evidence_assembly_v1.py --base https://smartreplyai.net --store demo
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
        with urlopen(req, timeout=120) as resp:
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
        f"{base}/dev/product-evidence-assembly"
        f"?store={args.store}&assembly_window={args.window}"
    )
    s1, b1 = _request_json(url)
    report = {
        "ok": bool(
            s1 == 200
            and b1.get("ok")
            and b1.get("table_exists")
            and b1.get("items_table_exists")
            and b1.get("deterministic") is True
            and b1.get("inputs_metrics_and_trends_only") is True
            and int(b1.get("bundle_count") or 0) > 0
            and int(b1.get("item_count") or 0) > 0
            and b1.get("canonical_fingerprint")
        ),
        "http_status": s1,
        "store": args.store,
        "assembly_window": args.window,
        "probe": b1,
    }
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
