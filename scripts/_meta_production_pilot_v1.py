# -*- coding: utf-8 -*-
"""
Meta Production Pilot V1 — controlled recovery journey against production.

Usage:
  python scripts/_meta_production_pilot_v1.py

Requires production WHATSAPP_PROVIDER=meta and approved template.
Does not click buttons. Does not use admin test send / hello_world / Graph direct send.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://smartreplyai.net"
PHONE = "+966546518011"
STORE = "demo"
REASON = "other"  # message_count=1, delay=1 minute on production demo
CHECKOUT_URL = f"{BASE}/demo/store/checkout"
EVIDENCE_DIR = ROOT / "docs" / "architecture" / "meta_production_pilot_v1" / "evidence"


def _http(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    timeout: float = 45.0,
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


def _save(name: str, payload: Any) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE_DIR / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path


def main() -> int:
    report: dict[str, Any] = {
        "pilot": "meta_production_pilot_v1",
        "base": BASE,
        "phone": PHONE,
        "store": STORE,
        "reason": REASON,
    }

    code, preflight = _http("GET", "/dev/meta-pilot-preflight")
    report["preflight_http"] = code
    report["preflight"] = preflight
    _save("01_preflight.json", preflight)
    print("preflight", code, json.dumps(preflight, ensure_ascii=False)[:500])
    if code != 200 or not isinstance(preflight, dict) or preflight.get("ok") is not True:
        report["abort"] = "preflight_failed"
        _save("00_pilot_report.json", report)
        print("ABORT: preflight failed — no cart created, no send attempted")
        return 2

    token = uuid.uuid4().hex[:12]
    session_id = f"meta_pilot_v1_{token}"
    cart_id = f"cf_cart_meta_pilot_{token}"
    recovery_key = f"{STORE}:{cart_id}"
    report["session_id"] = session_id
    report["cart_id"] = cart_id
    report["recovery_key"] = recovery_key

    # Fresh purge for this phone on demo (normal QA path)
    fresh_q = urllib.parse.urlencode(
        {"fresh": "1", "cf_test_phone": PHONE, "store_slug": STORE}
    )
    code_f, fresh_body = _http("GET", f"/demo/store?{fresh_q}")
    report["fresh_http"] = code_f
    _save("02_fresh_session.json", {"http": code_f, "note": "html_omitted"})

    reason_payload = {
        "store": STORE,
        "store_slug": STORE,
        "session_id": session_id,
        "cart_id": cart_id,
        "reason": REASON,
        "custom_text": "سبب اخر",
        "customer_phone": PHONE,
        "checkout_url": CHECKOUT_URL,
        "cart_url": CHECKOUT_URL,
    }
    code_r, reason_body = _http("POST", "/api/cartflow/reason", body=reason_payload)
    report["reason_http"] = code_r
    report["reason_response"] = reason_body
    _save("03_reason.json", {"http": code_r, "body": reason_body})
    print("reason", code_r, reason_body)

    abandon_payload = {
        "event": "cart_abandoned",
        "store": STORE,
        "store_slug": STORE,
        "session_id": session_id,
        "cart_id": cart_id,
        "cart_value": 189.0,
        "currency": "SAR",
        "checkout_url": CHECKOUT_URL,
        "cart_url": CHECKOUT_URL,
        "items": [{"name": "Meta Pilot Product", "price": 189.0, "qty": 1}],
    }
    code_a, abandon_body = _http("POST", "/api/cart-event", body=abandon_payload)
    report["abandon_http"] = code_a
    report["abandon_response"] = abandon_body
    _save("04_abandon.json", {"http": code_a, "body": abandon_body, "recovery_key": recovery_key})
    print("abandon", code_a, abandon_body)

    if code_a != 200 or not isinstance(abandon_body, dict):
        report["abort"] = "abandon_failed"
        _save("00_pilot_report.json", report)
        return 3
    if abandon_body.get("recovery_scheduled") is not True:
        report["abort"] = "recovery_not_scheduled"
        _save("00_pilot_report.json", report)
        return 3

    delay_s = float(abandon_body.get("recovery_delay_seconds") or 60.0)
    # Wait delay + execution buffer (no second send / no Twilio fallback)
    wait_s = max(75.0, delay_s + 45.0)
    report["wait_seconds"] = wait_s
    print(f"waiting {wait_s:.0f}s for scheduled recovery execution…")
    time.sleep(wait_s)

    evidence_snapshots: list[Any] = []
    final_evidence: Any = None
    for i in range(12):
        code_e, evidence = _http(
            "GET",
            f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(recovery_key)}",
        )
        snap = {"http": code_e, "body": evidence, "t": time.time()}
        evidence_snapshots.append(snap)
        _save(f"05_evidence_poll_{i:02d}.json", snap)
        print(
            "evidence",
            i,
            code_e,
            "logs",
            len((evidence or {}).get("recovery_logs") or []) if isinstance(evidence, dict) else 0,
            "providers",
            (evidence or {}).get("providers_seen") if isinstance(evidence, dict) else None,
        )
        if isinstance(evidence, dict) and evidence.get("ok") and (
            evidence.get("meta_path_used")
            or evidence.get("twilio_path_used")
            or any(
                str(x.get("status") or "").lower()
                in ("sent_real", "whatsapp_failed", "failed", "queued")
                for x in (evidence.get("recovery_logs") or [])
                if isinstance(x, dict)
            )
        ):
            final_evidence = evidence
            break
        time.sleep(15)

    if final_evidence is None and evidence_snapshots:
        final_evidence = evidence_snapshots[-1].get("body")

    code_t, timeline = _http(
        "GET",
        f"/dev/recovery-truth?recovery_key={urllib.parse.quote(recovery_key)}",
    )
    code_o, operational = _http(
        "GET",
        f"/dev/recovery-operational-truth?recovery_key={urllib.parse.quote(recovery_key)}",
    )
    report["timeline_http"] = code_t
    report["timeline"] = timeline
    report["operational_http"] = code_o
    report["operational"] = operational
    report["final_evidence"] = final_evidence
    _save("06_timeline.json", timeline)
    _save("07_operational.json", operational)
    _save("08_final_evidence.json", final_evidence)
    _save("00_pilot_report.json", report)

    logs = (final_evidence or {}).get("recovery_logs") if isinstance(final_evidence, dict) else []
    meta_sid = None
    provider = None
    for lg in logs or []:
        if not isinstance(lg, dict):
            continue
        if str(lg.get("provider") or "").lower() == "meta" and lg.get("provider_message_sid"):
            meta_sid = lg.get("provider_message_sid")
            provider = "meta"
            break
        if lg.get("provider_message_sid") and provider is None:
            meta_sid = lg.get("provider_message_sid")
            provider = lg.get("provider")

    print("=== PILOT RESULT ===")
    print("recovery_key=", recovery_key)
    print("provider=", provider)
    print("meta_message_id=", meta_sid)
    print("twilio_path_used=", (final_evidence or {}).get("twilio_path_used"))
    print("meta_path_used=", (final_evidence or {}).get("meta_path_used"))
    print("evidence_dir=", EVIDENCE_DIR)

    if (final_evidence or {}).get("twilio_path_used"):
        return 4
    if not meta_sid:
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
