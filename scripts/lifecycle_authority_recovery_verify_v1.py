# -*- coding: utf-8 -*-
"""Lifecycle Authority Recovery v1 — local + optional production verification."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

OUT_DIR = Path(__file__).resolve().parent / "_lifecycle_authority_recovery_verify_v1_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = OUT_DIR / "verify_report.json"

PROD_BASE = "https://smartreplyai.net"


def _lifecycle_alignment(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing = 0
    conflicts = 0
    samples: list[dict[str, str]] = []
    for row in rows:
        state = str(row.get("customer_lifecycle_state") or "").strip()
        label = str(row.get("customer_lifecycle_label_ar") or "").strip()
        bucket = str(row.get("merchant_cart_bucket") or "").strip()
        if not state:
            missing += 1
            continue
        if state == "archived" and bucket not in ("archived", ""):
            conflicts += 1
        if state == "completed" and bucket not in ("recovered", ""):
            conflicts += 1
        if len(samples) < 5:
            samples.append(
                {
                    "recovery_key": str(row.get("recovery_key") or "")[:80],
                    "customer_lifecycle_state": state,
                    "merchant_cart_bucket": bucket,
                    "label_ar": label[:80],
                }
            )
    return {
        "rows": len(rows),
        "missing_lifecycle": missing,
        "bucket_conflicts": conflicts,
        "samples": samples,
        "ok": missing == 0 and conflicts == 0,
    }


def _followup_derived_from_lifecycle(rows: list[dict[str, Any]]) -> dict[str, Any]:
    bad = 0
    for row in rows:
        state = str(row.get("customer_lifecycle_state") or "").strip()
        if not state:
            continue
        seq = row.get("merchant_followup_sequence_line_ar")
        nxt = row.get("merchant_followup_next_line_ar")
        what = str(row.get("customer_lifecycle_what_next_ar") or "")
        nfu = str(row.get("customer_lifecycle_next_followup_line_ar") or "")
        if seq and "لا مزيد" in what and seq != what and "اكتملت" not in seq:
            bad += 1
        if nxt and nfu and nxt != nfu:
            bad += 1
    return {"rows_checked": len(rows), "followup_conflicts": bad, "ok": bad == 0}


def run_local_verification() -> dict[str, Any]:
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from main import app

    fake_row = {
        "recovery_key": "store:s1",
        "customer_lifecycle_state": "waiting_first_send",
        "customer_lifecycle_label_ar": "بانتظار الإرسال",
        "customer_lifecycle_is_archived_visual": False,
        "merchant_cart_bucket": "waiting",
        "merchant_cart_is_active": True,
        "merchant_cart_is_terminal": False,
        "merchant_followup_sent_count": 1,
        "merchant_followup_configured_count": 2,
        "merchant_followup_progress_ar": "تم إرسال ١ من ٢",
    }
    client = TestClient(app)
    checks: dict[str, Any] = {}

    with (
        patch("main._dashboard_recovery_store_row", return_value=None),
        patch(
            "main._normal_recovery_merchant_lightweight_alert_list_for_api",
            return_value=([fake_row], {"carts_count": 1}),
        ),
        patch(
            "services.recovery_truth_timeline_v1.get_recovery_truth_timeline",
            return_value=[],
        ),
        patch(
            "services.recovery_truth_timeline_v1.timeline_status_set",
            return_value=frozenset(),
        ),
    ):
        res = client.get("/dev/lifecycle-truth-check", params={"recovery_key": "store:s1"})
        checks["dev_lifecycle_truth_check"] = {
            "status": res.status_code,
            "ok": res.status_code == 200 and res.json().get("consistent"),
            "body": res.json() if res.status_code == 200 else None,
        }

    try:
        from services.lifecycle_authority_recovery_v1 import (
            attach_merchant_row_lifecycle_authority,
        )

        vip_row: dict[str, Any] = {"recovery_key": "s:vip"}
        attach_merchant_row_lifecycle_authority(
            vip_row,
            recovery_key="s:vip",
            is_vip_lane=True,
            vip_lifecycle_status_evidence="contacted",
        )
        checks["vip_lifecycle_authority"] = {
            "state": vip_row.get("customer_lifecycle_state"),
            "display_status_ar": vip_row.get("display_status_ar"),
            "label_match": vip_row.get("display_status_ar")
            == vip_row.get("customer_lifecycle_label_ar"),
            "ok": bool(vip_row.get("customer_lifecycle_state")),
        }
    except Exception as exc:  # noqa: BLE001
        checks["vip_lifecycle_authority"] = {"ok": False, "error": str(exc)[:200]}

    checks["alignment"] = _lifecycle_alignment([fake_row])
    checks["followup"] = _followup_derived_from_lifecycle([fake_row])
    checks["ok"] = all(
        c.get("ok")
        for c in checks.values()
        if isinstance(c, dict) and "ok" in c
    )
    return checks


def probe_production() -> dict[str, Any]:
    out: dict[str, Any] = {"base": PROD_BASE, "reachable": False}
    try:
        req = urllib.request.Request(
            f"{PROD_BASE}/login",
            headers={"User-Agent": "cartflow-lifecycle-authority-verify-v1"},
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            html = resp.read().decode("utf-8", "replace")
            out["reachable"] = True
            out["status"] = resp.status
            if "merchant_dashboard_lazy.js" in html:
                out["dashboard_js_linked"] = True
            else:
                out["dashboard_js_linked"] = False
            out["note"] = (
                "Authenticated dashboard API checks require merchant session; "
                "deploy marker only until post-deploy gate run."
            )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        out["error"] = str(exc)[:200]
    return out


def main() -> int:
    report: dict[str, Any] = {
        "task": "Lifecycle Authority Recovery v1",
        "ts": time.time(),
        "local": run_local_verification(),
        "production": probe_production(),
    }
    report["pass"] = bool(report["local"].get("ok"))
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
