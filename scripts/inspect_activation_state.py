#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Print live activation fields from GET /api/dashboard/summary?activation_inspect=1

Usage (production or local):
  set CARTFLOW_BASE_URL=https://your-app.example
  set CARTFLOW_SESSION_COOKIE=session=...; other=...
  python scripts/inspect_activation_state.py

No code changes to stage logic — read-only HTTP inspect.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def main() -> int:
    base = (os.environ.get("CARTFLOW_BASE_URL") or "http://127.0.0.1:8000").rstrip(
        "/"
    )
    cookie = (os.environ.get("CARTFLOW_SESSION_COOKIE") or "").strip()
    url = f"{base}/api/dashboard/summary?activation_inspect=1"
    headers = {"Accept": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:800]}")
        return 1
    except OSError as e:
        print(f"Request failed: {e}")
        return 1

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(raw[:2000])
        return 1

    if not data.get("ok"):
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 1

    act = data.get("merchant_activation") or {}
    dbg = data.get("merchant_activation_visibility_debug") or {}
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print()
    print("[ACTIVATION STATE]")
    print(f"home_stage={act.get('home_stage')}")
    print(f"activation_display={act.get('activation_display')}")
    print(f"hide_setup_card={act.get('hide_setup_card')}")
    print(
        "production_signal_reasons="
        + json.dumps(
            act.get("production_signal_reasons")
            or dbg.get("production_signal_reasons"),
            ensure_ascii=False,
        )
    )
    print(
        "milestones="
        + json.dumps(act.get("milestones"), ensure_ascii=False, default=str)
    )
    from services.merchant_activation_live_inspect_v1 import (  # noqa: PLC0415
        infer_ui_blocker_inferred,
    )

    print(f"ui_blocker_inferred={infer_ui_blocker_inferred(act, dbg)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
