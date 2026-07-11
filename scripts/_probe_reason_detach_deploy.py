# -*- coding: utf-8 -*-
"""Quick probe: loader version + reason arm header on prod."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE = "https://smartreplyai.net"
TS = int(time.time() * 1000)


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def main() -> None:
    loader = get(f"{BASE}/static/widget_loader.js?_ts={TS}")
    for token in (
        "v2-widget-reason-post-detach-v1-4",
        "v2-widget-reason-post-detach-v1-3",
        "v2-widget-reason-post-detach-v1-2",
        "v2-widget-reason-post-detach-v1-1",
        "v2-widget-bridge-fail-fast-v1",
        "v2-widget-",
    ):
        print("loader_has", token, token in loader)

    core = get(
        f"{BASE}/static/cartflow_widget_runtime/cartflow_storefront_cart_bridge_core.js?_ts={TS}"
    )
    print("prod_defer_cart_persist", "defer_cart_persist" in core)
    print(
        "prod_schedule_after_only_export",
        "scheduleBackgroundPersistAfterReason" in core,
    )

    flows = get(
        f"{BASE}/static/cartflow_widget_runtime/cartflow_widget_flows.js?_ts={TS}"
    )
    print("prod_flows_defer_gate", "defer_cart_persist" in flows)

    body = json.dumps(
        {
            "store_slug": "probe-missing",
            "session_id": "s_probe",
            "reason": "price",
            "sub_category": "price_discount_request",
        }
    ).encode()
    req = urllib.request.Request(
        f"{BASE}/api/cartflow/reason",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            hdrs = {k.lower(): v for k, v in r.headers.items()}
            raw = r.read().decode("utf-8", "replace")
            print("reason_status", r.status)
            print("x-cf-reason-arm", hdrs.get("x-cf-reason-arm"))
            print("server-timing", hdrs.get("server-timing"))
            print("body_snip", raw[:300])
    except urllib.error.HTTPError as e:
        hdrs = {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
        print("reason_http", e.code)
        print("x-cf-reason-arm", hdrs.get("x-cf-reason-arm"))
        print("server-timing", hdrs.get("server-timing"))
        print("body_snip", e.read()[:300])


if __name__ == "__main__":
    main()
