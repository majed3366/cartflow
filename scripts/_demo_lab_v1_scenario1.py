# -*- coding: utf-8 -*-
"""
CLI: Demo Commerce Lab V1 — Scenario 1 (Visit → … → Purchase).

Usage (from repo root):
  python scripts/_demo_lab_v1_scenario1.py

Always Lab-Resets demo first. No UI. Demo store only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from fastapi.testclient import TestClient

    from main import app
    from services.demo_lab_scenario1_v1 import run_lab_scenario1_v1

    client = TestClient(app)
    report = run_lab_scenario1_v1(store_slug="demo", client=client)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
