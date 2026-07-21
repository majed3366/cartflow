# -*- coding: utf-8 -*-
"""
Guidance Routing Foundation V1 — production/demo validation helper.

Usage:
  python scripts/_verify_guidance_routing_v1.py --base https://smartreplyai.net --store demo
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
        f"{base}/dev/guidance-routing"
        f"?store={args.store}&assembly_window={args.window}"
    )
    status, body = _request_json(url)
    report = {
        "ok": bool(
            status == 200
            and body.get("ok")
            and body.get("table_exists")
            and body.get("deterministic") is True
            and body.get("consumes_commercial_guidance_only") is True
            and body.get("accounting_ok") is True
            and body.get("no_home_presentation_fields") is True
            and int(body.get("expected_route_pairs") or 0) > 0
            and int(body.get("unaccounted_route_count") or 0) == 0
            and body.get("canonical_fingerprint")
            and not any(
                str(e).startswith("materialize:") for e in (body.get("errors") or [])
            )
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
