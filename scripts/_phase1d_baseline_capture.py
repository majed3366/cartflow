"""Capture Phase 1D baseline: route inventory + moved dev GET responses."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ENV", "development")

MOVED = [
    "/dev/routes",
    "/dev/config-system-verify",
    "/dev/admin-operational-summary",
    "/dev/production-readiness",
    "/dev/widget-runtime-config-verify",
    "/dev/store-template-debug",
    "/dev/template-truth",
    "/dev/store-identity-runtime-truth",
    "/dev/widget-runtime-truth",
    "/dev/recovery-truth",
    "/dev/attempt-2-trace",
    "/dev/recovery-operational-truth",
    "/dev/vip-merchant-alert-operational-truth",
    "/dev/lifecycle-truth-check",
    "/dev/merchant-truth-trace",
    "/dev/recovery-health",
    "/dev/recovery-delay-verify",
    "/dev/recovery-attempts-verify",
    "/dev/recovery-unit-verify",
    "/dev/recovery-dashboard-render-test",
    "/dev/recovery-logs/demo",
    "/dev/test-widget-identity-trace",
]


def summarize(body):
    if isinstance(body, dict):
        return {"type": "dict", "keys": sorted(body.keys())[:40], "ok": body.get("ok")}
    if isinstance(body, list):
        return {"type": "list", "len": len(body), "sample": body[:3]}
    return {"type": type(body).__name__, "preview": str(body)[:200]}


def main():
    from fastapi.testclient import TestClient
    import main

    paths = sorted({getattr(r, "path", str(r)) for r in main.app.routes})
    out = {
        "route_count": len(main.app.routes),
        "unique_paths": len(paths),
        "paths": paths,
        "dev_routes_list": None,
        "endpoints": {},
    }
    client = TestClient(main.app)
    r = client.get("/dev/routes")
    out["dev_routes_list"] = r.json()
    for path in MOVED:
        resp = client.get(path)
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]
        out["endpoints"][path] = {
            "status_code": resp.status_code,
            "summary": summarize(body) if path != "/dev/routes" else {"type": "list", "len": len(body)},
        }
    dest = ROOT / "scripts" / f"_phase1d_{sys.argv[1] if len(sys.argv) > 1 else 'baseline'}.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(dest, "route_count", out["route_count"])


if __name__ == "__main__":
    main()
