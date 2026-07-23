# -*- coding: utf-8 -*-
"""Verify GET /dev/commercial-guidance for cguide_v1 closure gates."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = (os.environ.get("CARTFLOW_BASE_URL") or "https://smartreplyai.net").rstrip("/")
URL = f"{BASE}/dev/commercial-guidance?store=demo"


def main() -> int:
    try:
        with urllib.request.urlopen(URL, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw": raw}
        status = exc.code
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2

    def _i(key: str) -> int:
        val = body.get(key)
        return int(val) if val is not None else -1

    gates = {
        "http_ok": status == 200,
        "ok": body.get("ok") is True,
        "deterministic": body.get("deterministic") is True,
        "unaccounted_0": _i("unaccounted") == 0,
        "failed_0": _i("failed") == 0,
        "claim_boundary_ok": body.get("claim_boundary_ok") is True,
        "lineage_ok": body.get("lineage_ok") is True,
        "duplicate_current_false": body.get("duplicate_current") is False,
        "non_demo_writes_0": _i("non_demo_writes") == 0,
        "knowledge_only": body.get("consumes_knowledge_only") is True,
    }
    summary = {
        "url": URL,
        "status": status,
        "gates": gates,
        "eligible_knowledge_count": body.get("eligible_knowledge_count"),
        "guidance_created": body.get("guidance_created"),
        "observe_only": body.get("observe_only"),
        "evidence_gap": body.get("evidence_gap"),
        "conflicting": body.get("conflicting"),
        "rejected": body.get("rejected"),
        "abstained": body.get("abstained"),
        "expired": body.get("expired"),
        "failed": body.get("failed"),
        "unaccounted": body.get("unaccounted"),
        "ok": all(gates.values()),
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
