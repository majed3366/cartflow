# -*- coding: utf-8 -*-
"""Local First-100 critical-route burst. Does not deploy. Does not hit production."""
from __future__ import annotations

import concurrent.futures
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from main import app
from services.db_resource_safety_v1.admission_v1 import reset_for_tests, snapshot

OUT = Path(__file__).resolve().parent / "LOCAL_VALIDATION.json"


def _hit(c: TestClient, path: str) -> dict:
    t0 = time.perf_counter()
    r = c.get(path)
    return {
        "path": path,
        "status": r.status_code,
        "ms": round((time.perf_counter() - t0) * 1000.0, 1),
    }


def burst(n: int, paths: list[str]) -> dict:
    reset_for_tests()
    c = TestClient(app)
    jobs = [paths[i % len(paths)] for i in range(n)]
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(n, 32)) as ex:
        rows = list(ex.map(lambda p: _hit(c, p), jobs))
    elapsed = round(time.perf_counter() - t0, 3)
    ok = sum(1 for r in rows if r["status"] == 200)
    return {
        "n": n,
        "elapsed_s": elapsed,
        "ok": ok,
        "fail": n - ok,
        "max_ms": max(r["ms"] for r in rows),
        "admission_after": snapshot(),
        "pass": ok == n and snapshot()["global_in_use"] == 0,
    }


def main() -> None:
    paths = ["/ping", "/health", "/login"]
    out = {
        "A_1": burst(3, paths),
        "B_4_tabs": burst(4, paths),
        "C_10": burst(10, paths),
        "D_25": burst(25, paths),
        "E_50": burst(50, paths),
        "F_100": burst(100, paths),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
