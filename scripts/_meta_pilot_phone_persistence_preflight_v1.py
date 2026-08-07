# -*- coding: utf-8 -*-
"""
Meta Pilot Phone Persistence Preflight V1.

Creates one controlled cart, arms reason with canonical customer_phone,
proves durable DB phone, then converts the cart so the schedule cannot send.

Does NOT wait for due. Does NOT send WhatsApp.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.meta_pilot_fixture_v1 import (  # noqa: E402
    PILOT_CHECKOUT_URL,
    PILOT_PHONE_DIGITS,
    PILOT_PHONE_E164,
    PILOT_STORE,
    build_abandon_payload,
    build_cartflow_reason_payload,
    evaluate_phone_persistence_ready,
    mask_phone_digits,
)

BASE = "https://smartreplyai.net"
EVIDENCE_DIR = (
    ROOT
    / "docs"
    / "architecture"
    / "meta_production_pilot_v1"
    / "evidence"
    / "phone_persistence_preflight_v1"
)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def http(
    method: str,
    path: str,
    body: dict | None = None,
    timeout: float = 60.0,
) -> tuple[int, Any]:
    url = path if path.startswith("http") else f"{BASE}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                parsed: Any = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = {"_raw": raw[:2000]}
            return int(resp.status), parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw) if raw else {"error": str(exc)}
        except json.JSONDecodeError:
            parsed = {"_raw": raw[:2000]}
        return int(exc.code), parsed


def save(name: str, payload: Any) -> None:
    (EVIDENCE_DIR / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> int:
    token = uuid.uuid4().hex[:12]
    session_id = f"meta_pilot_phone_pf_{token}"
    cart_id = f"cf_cart_meta_pilot_phone_pf_{token}"
    recovery_key = f"{PILOT_STORE}:{cart_id}"

    report: dict[str, Any] = {
        "pilot": "meta_pilot_fixture_phone_persistence_preflight_v1",
        "recovery_key": recovery_key,
        "session_id": session_id,
        "cart_id": cart_id,
        "phone_input": PILOT_PHONE_E164,
        "expected_digits": PILOT_PHONE_DIGITS,
        "no_send": True,
        "cancel_before_due": True,
    }
    print("recovery_key", recovery_key, flush=True)

    # Fresh session (no cf_test_phone — durable path is reason.customer_phone)
    fresh_q = urllib.parse.urlencode({"fresh": "1", "store_slug": PILOT_STORE})
    code_f, _ = http("GET", f"/demo/store?{fresh_q}")
    report["fresh_http"] = code_f

    abandon = build_abandon_payload(
        session_id=session_id,
        cart_id=cart_id,
        checkout_url=PILOT_CHECKOUT_URL,
    )
    code_a, ab_body = http("POST", "/api/cart-event", body=abandon)
    report["abandon"] = {"http": code_a, "body": ab_body}
    save("01_abandon.json", report["abandon"])
    print("abandon", code_a, ab_body, flush=True)
    if code_a != 200:
        report["abort"] = "abandon_failed"
        save("00_preflight_report.json", report)
        return 2

    reason = build_cartflow_reason_payload(
        session_id=session_id,
        cart_id=cart_id,
        customer_phone=PILOT_PHONE_E164,
        checkout_url=PILOT_CHECKOUT_URL,
    )
    assert "cf_test_phone" not in reason
    assert reason.get("customer_phone") == PILOT_PHONE_E164
    code_r, rs_body = http("POST", "/api/cartflow/reason", body=reason)
    report["reason"] = {"http": code_r, "body": rs_body}
    save("02_reason.json", report["reason"])
    print("reason", code_r, rs_body, flush=True)
    if code_r != 200 or not (isinstance(rs_body, dict) and rs_body.get("ok")):
        report["abort"] = "reason_failed"
        save("00_preflight_report.json", report)
        return 3

    # Poll durable evidence BEFORE due (do not sleep until due)
    evidence = None
    for i in range(24):
        code_e, evidence = http(
            "GET",
            f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(recovery_key)}",
        )
        save(f"03_evidence_poll_{i:02d}.json", {"http": code_e, "body": evidence})
        ac = (evidence or {}).get("abandoned_cart") if isinstance(evidence, dict) else None
        crr = (
            (evidence or {}).get("cart_recovery_reason")
            if isinstance(evidence, dict)
            else None
        )
        sched = (evidence or {}).get("schedule_rows") if isinstance(evidence, dict) else None
        ac_mask = (ac or {}).get("phone_masked") if isinstance(ac, dict) else None
        crr_mask = (crr or {}).get("phone_masked") if isinstance(crr, dict) else None
        sched_id = None
        if isinstance(sched, list) and sched:
            sched_id = sched[0].get("id")
        print(
            "poll",
            i,
            "ac_mask",
            ac_mask,
            "crr_mask",
            crr_mask,
            "schedule_id",
            sched_id,
            flush=True,
        )
        if ac_mask and crr_mask and sched_id:
            break
        time.sleep(1.0)

    if not isinstance(evidence, dict):
        report["abort"] = "evidence_missing"
        save("00_preflight_report.json", report)
        return 4

    ac = evidence.get("abandoned_cart") or {}
    crr = evidence.get("cart_recovery_reason") or {}
    sched_rows = evidence.get("schedule_rows") or []
    sched0 = sched_rows[0] if sched_rows else {}
    schedule_id = sched0.get("id")

    # Evidence is masked — expected mask for 966546518011 is 966…11
    expected_mask = mask_phone_digits(PILOT_PHONE_DIGITS)
    ac_mask = ac.get("phone_masked")
    crr_mask = crr.get("phone_masked")
    masks_ok = ac_mask == expected_mask and crr_mask == expected_mask

    # Use operational/DB-facing evaluation with masks as proxy when raw unavailable;
    # for readiness we require both masks match canonical expected mask + schedule linked.
    ready = bool(
        masks_ok
        and schedule_id
        and evidence.get("recovery_key") == recovery_key
        and ac.get("cart_id") == cart_id
        and (ac.get("session_id") == session_id or crr.get("session_id") == session_id)
        and not evidence.get("meta_path_used")
        and not evidence.get("twilio_path_used")
    )

    persistence = {
        "recovery_key": recovery_key,
        "schedule_id": schedule_id,
        "schedule_status": sched0.get("status"),
        "schedule_due_at": sched0.get("due_at"),
        "crr_phone_masked": crr_mask,
        "abandoned_cart_phone_masked": ac_mask,
        "expected_phone_masked": expected_mask,
        "phone_normalized_ok": masks_ok,
        "identity_linked": evidence.get("recovery_key") == recovery_key,
        "phone_persistence_ready": ready,
        "no_send_yet": True,
        "providers_seen": evidence.get("providers_seen"),
    }
    # Also run helper with digit stand-ins when masks match (sanitized report)
    if masks_ok:
        helper = evaluate_phone_persistence_ready(
            recovery_key=recovery_key,
            crr_phone=PILOT_PHONE_DIGITS,
            ac_phone=PILOT_PHONE_DIGITS,
            schedule_id=int(schedule_id) if schedule_id else None,
            schedule_recovery_key=recovery_key,
        )
        persistence["helper_ready"] = helper["phone_persistence_ready"]
        ready = ready and helper["phone_persistence_ready"]
        persistence["phone_persistence_ready"] = ready

    report["persistence"] = persistence
    save("04_persistence.json", persistence)
    print(json.dumps(persistence, ensure_ascii=False, indent=2), flush=True)

    # Cancel before due: conversion truth blocks Scheduler send
    conv_body = {
        "store": PILOT_STORE,
        "store_slug": PILOT_STORE,
        "session_id": session_id,
        "cart_id": cart_id,
        "purchase_completed": True,
        "checkout_url": PILOT_CHECKOUT_URL,
    }
    code_c, conv = http("POST", "/api/conversion", body=conv_body)
    report["conversion_cancel"] = {"http": code_c, "body": conv}
    save("05_conversion_cancel.json", report["conversion_cancel"])
    print("conversion_cancel", code_c, conv, flush=True)

    # Re-check: still no provider send
    code_e2, ev2 = http(
        "GET",
        f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(recovery_key)}",
    )
    report["evidence_after_cancel"] = {
        "http": code_e2,
        "meta_path_used": (ev2 or {}).get("meta_path_used") if isinstance(ev2, dict) else None,
        "twilio_path_used": (ev2 or {}).get("twilio_path_used") if isinstance(ev2, dict) else None,
        "providers_seen": (ev2 or {}).get("providers_seen") if isinstance(ev2, dict) else None,
        "schedule_rows": (ev2 or {}).get("schedule_rows") if isinstance(ev2, dict) else None,
    }
    save("06_evidence_after_cancel.json", report["evidence_after_cancel"])

    go = bool(
        ready
        and not (report["evidence_after_cancel"].get("meta_path_used"))
        and not (report["evidence_after_cancel"].get("twilio_path_used"))
    )
    report["go_no_go"] = "GO" if go else "NO-GO"
    report["phone_persistence_ready"] = ready
    save("00_preflight_report.json", report)

    print("=== PREFLIGHT ===", flush=True)
    print("phone_persistence_ready=", ready, flush=True)
    print("go_no_go=", report["go_no_go"], flush=True)
    return 0 if go else 5


if __name__ == "__main__":
    raise SystemExit(main())
