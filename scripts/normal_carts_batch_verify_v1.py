# -*- coding: utf-8 -*-
"""
Normal Carts Architecture Recovery v1 — local verification runner.

Usage:
  python scripts/normal_carts_batch_verify_v1.py
  python scripts/normal_carts_batch_verify_v1.py --rows 45
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import event

from extensions import db
from main import _api_json_dashboard_normal_carts, _merchant_dashboard_db_ready
from models import AbandonedCart, Store
from services.normal_carts_dashboard_batch_v1 import build_normal_carts_unified_rows


def _count_queries(fn, *args, **kwargs) -> tuple[int, float, object]:
    queries: list[str] = []

    @event.listens_for(db.engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany) -> None:
        if not statement.strip().upper().startswith("PRAGMA"):
            queries.append(statement)

    t0 = time.perf_counter()
    try:
        out = fn(*args, **kwargs)
    finally:
        event.remove(db.engine, "before_cursor_execute", _before)
    return len(queries), (time.perf_counter() - t0) * 1000.0, out


def _seed(store: Store, n: int, suffix: str) -> None:
    now = datetime.now(timezone.utc)
    for i in range(n):
        db.session.add(
            AbandonedCart(
                store_id=int(store.id),
                zid_cart_id=f"z-ncv-{suffix}-{i}",
                recovery_session_id=f"s-ncv-{suffix}-{i}",
                customer_phone=f"9665099{i:04d}"[-12:],
                status="abandoned",
                cart_value=150.0 + i,
                last_seen_at=now,
            )
        )
    db.session.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=45)
    parser.add_argument("--out", default="scripts/_normal_carts_batch_verify_v1_out/verify_report.json")
    args = parser.parse_args()

    os.environ.setdefault("ENV", "development")
    db.create_all()
    suffix = uuid.uuid4().hex[:8]
    slug = f"nc-verify-{suffix}"
    store = Store(zid_store_id=slug, vip_cart_threshold=8000)
    db.session.add(store)
    db.session.commit()

    _seed(store, max(1, int(args.rows)), suffix)

    _merchant_dashboard_db_ready()
    build_normal_carts_unified_rows(store, page_limit=50, page_offset=0)

    qn, ms, out = _count_queries(_api_json_dashboard_normal_carts, store)
    body, prof = out
    perf = body.get("_perf") or {}

    report = {
        "ok": True,
        "rows_seeded": int(args.rows),
        "business_queries": qn,
        "endpoint_ms": round(ms, 2),
        "perf": perf,
        "prof": prof,
        "merchant_rows": len(body.get("merchant_carts_page_rows") or []),
        "archived_rows": len(body.get("merchant_archived_carts_page_rows") or []),
        "pass": (
            not bool(perf.get("partial"))
            and not bool(perf.get("degraded"))
            and int(perf.get("visible_rows") or 0) > 0
            and qn <= 55
            and ms < 12000.0
        ),
    }

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
