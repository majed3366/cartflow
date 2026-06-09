"""Capture Phase 1E-A baseline: route inventory + Group A dev GET responses."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MOVED = [
    "/dev/whatsapp-message-test",
    "/dev/should-send-test",
    "/dev/recovery-timing-test",
    "/dev/recovery-duplicate-test",
    "/dev/run-flow",
]


def summarize(body):
    if isinstance(body, dict):
        return {
            "type": "dict",
            "keys": sorted(body.keys()),
            "ok": body.get("ok"),
            "recent": body.get("recent"),
            "idle": body.get("idle"),
            "cases_keys": sorted((body.get("cases") or {}).keys())
            if isinstance(body.get("cases"), dict)
            else None,
            "first_attempt": (body.get("first_attempt") or {}).get("should_send")
            if isinstance(body.get("first_attempt"), dict)
            else None,
            "second_attempt": (body.get("second_attempt") or {}).get("should_send")
            if isinstance(body.get("second_attempt"), dict)
            else None,
            "message_keys": sorted(body.keys()) if "new_price" in body else None,
            "cart_keys": sorted((body.get("cart") or {}).keys())
            if isinstance(body.get("cart"), dict)
            else None,
        }
    if isinstance(body, list):
        return {"type": "list", "len": len(body), "sample": body[:3]}
    return {"type": type(body).__name__, "preview": str(body)[:200]}


def capture(env_label: str, env_value: str) -> dict:
    os.environ["ENV"] = env_value
    # Force reimport with new ENV
    for mod in list(sys.modules):
        if mod == "main" or mod.startswith("main."):
            del sys.modules[mod]
    from fastapi.testclient import TestClient
    import main

    paths = sorted({getattr(r, "path", str(r)) for r in main.app.routes})
    out = {
        "env": env_label,
        "route_count": len(main.app.routes),
        "unique_paths": len(paths),
        "paths": paths,
        "dev_routes_list": None,
        "endpoints": {},
    }
    client = TestClient(main.app)
    r = client.get("/dev/routes")
    try:
        out["dev_routes_list"] = r.json()
    except Exception:
        out["dev_routes_list"] = None
        out["dev_routes_status"] = r.status_code
    for path in MOVED:
        resp = client.get(path)
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]
        out["endpoints"][path] = {
            "status_code": resp.status_code,
            "summary": summarize(body),
            "body": body if path != "/dev/routes" else None,
        }
    return out


def main():
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    tag = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    dev = capture("development", "development")
    prod = capture("production", "production")
    out = {"development": dev, "production": prod}
    dest = ROOT / "scripts" / f"_phase1ea_{tag}.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(dest, "route_count", dev["route_count"])


if __name__ == "__main__":
    main()
