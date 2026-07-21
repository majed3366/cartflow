# -*- coding: utf-8 -*-
"""CIS → Knowledge Integration V1 — production verify helper."""
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
            parsed = json.loads(body) if body else {}
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
    url = (
        f"{args.base.rstrip('/')}/dev/commerce-intelligence-knowledge"
        f"?store={args.store}&time_window_key={args.window}"
    )
    status, body = _request_json(url)
    report = {
        "ok": bool(
            status == 200
            and body.get("ok")
            and body.get("deterministic") is True
            and int(body.get("unaccounted") or 0) == 0
            and int(body.get("failed") or 0) == 0
            and body.get("claim_boundary_ok") is True
            and body.get("lineage_ok") is True
            and body.get("duplicate_current") is False
            and int(body.get("non_demo_writes") or 0) == 0
            and body.get("consumes_synthesis_only") is True
            and body.get("input_contract_version")
            == "commerce_intelligence_synthesis_v1"
            and body.get("intake_policy_version") == "ciknow_v1"
        ),
        "http_status": status,
        "probe": body,
    }
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
