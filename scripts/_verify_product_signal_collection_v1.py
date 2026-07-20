# -*- coding: utf-8 -*-
"""
Product Signal Collection V1 — production/demo validation helper.

1) POST cart_state_sync with lines for Demo store
2) GET /dev/product-signal-collection?store=demo for DB evidence

Usage:
  python scripts/_verify_product_signal_collection_v1.py --base https://smartreplyai.net --store demo
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
        with urlopen(req, timeout=45) as resp:
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
    post_status, post_body = _request_json(
        f"{base}/api/cart-event", method="POST", payload=payload
    )
    probe_status, probe_body = _request_json(
        f"{base}/dev/product-signal-collection?store={args.store}"
    )
    report = {
        "ok": bool(
            post_status == 200
            and probe_status == 200
            and probe_body.get("table_exists")
            and int(probe_body.get("total") or 0) > 0
            and int(probe_body.get("duplicate_dedup_hash_groups") or 0) == 0
        ),
        "http_status_cart_event": post_status,
        "http_status_probe": probe_status,
        "store": args.store,
        "session_id": sid,
        "cart_event_ok": post_status == 200 and bool(post_body.get("ok", True)),
        "probe": {
            "ok": probe_body.get("ok"),
            "table_exists": probe_body.get("table_exists"),
            "total": probe_body.get("total"),
            "by_signal_type": probe_body.get("by_signal_type"),
            "evidence_linked": probe_body.get("evidence_linked"),
            "duplicate_dedup_hash_groups": probe_body.get("duplicate_dedup_hash_groups"),
            "alembic_version": probe_body.get("alembic_version"),
            "alembic_stamped_exact": probe_body.get("alembic_stamped_exact"),
            "migration_satisfied": probe_body.get("migration_satisfied"),
            "collection_enabled": probe_body.get("collection_enabled"),
            "errors": probe_body.get("errors"),
            "sample_len": len(probe_body.get("sample") or []),
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
