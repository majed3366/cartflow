# -*- coding: utf-8 -*-
"""One-shot Meta recovery journey final execute. Do not reuse without review."""
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
BASE = "https://smartreplyai.net"
PHONE = "+966546518011"
STORE = "demo"
REASON = "other"
CUSTOM_REASON = "سبب اخر"
CHECKOUT_URL = f"{BASE}/demo/store/checkout"
EVIDENCE_DIR = (
    ROOT
    / "docs"
    / "architecture"
    / "meta_production_pilot_v1"
    / "evidence"
    / "journey_v2_final_execute"
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
    report: dict[str, Any] = {
        "pilot": "meta_first_real_recovery_journey_v2_final_execute",
        "base": BASE,
        "phone": PHONE,
        "store": STORE,
        "reason": REASON,
        "scheduler_preflight_line": (
            "[SCHEDULER META RUNTIME] role=scheduler whatsapp_provider=meta "
            "meta_template_name=cartflow_cart_reminder_ar_v2 "
            "access_token_configured=true phone_number_id_configured=true "
            "waba_id_configured=true ready_for_meta_recovery=true"
        ),
        "no_retry": True,
        "no_button_clicks": True,
    }

    code, preflight = http("GET", "/dev/meta-pilot-preflight")
    report["preflight_http"] = code
    report["preflight"] = (
        {
            k: preflight.get(k)
            for k in (
                "ok",
                "provider",
                "provider_is_meta",
                "template_name_env",
                "template_name_expected",
                "template_exists",
                "template_status",
                "comparison",
                "template_id",
                "mismatch_hints",
            )
        }
        if isinstance(preflight, dict)
        else preflight
    )
    save("01_preflight.json", preflight)
    print("preflight", code, report["preflight"], flush=True)
    if code != 200 or not isinstance(preflight, dict):
        report["abort"] = "preflight_http_failed"
        save("00_pilot_report.json", report)
        print("ABORT: preflight http failed", flush=True)
        return 2
    if not (
        preflight.get("provider_is_meta") is True
        and preflight.get("template_status") == "APPROVED"
        and preflight.get("comparison") == "SAME"
        and preflight.get("template_name_env") == "cartflow_cart_reminder_ar_v2"
    ):
        report["abort"] = "preflight_substantive_gate_failed"
        save("00_pilot_report.json", report)
        print("ABORT: substantive preflight gate failed", flush=True)
        return 2

    code_pc, pub = http("GET", f"/api/public/config?store={STORE}")
    store_name = None
    if isinstance(pub, dict):
        store_name = (
            pub.get("widget_display_name")
            or pub.get("widget_name")
            or pub.get("store_name")
        )
    report["store_display_name"] = store_name
    save(
        "01b_public_config_store_name.json",
        {
            "http": code_pc,
            "widget_display_name": store_name,
            "widget_name": pub.get("widget_name") if isinstance(pub, dict) else None,
        },
    )
    print("store_display_name", store_name, flush=True)

    token = uuid.uuid4().hex[:12]
    session_id = f"meta_pilot_v2_final_{token}"
    cart_id = f"cf_cart_meta_pilot_v2_final_{token}"
    recovery_key = f"{STORE}:{cart_id}"
    report["session_id"] = session_id
    report["cart_id"] = cart_id
    report["recovery_key"] = recovery_key
    report["checkout_url"] = CHECKOUT_URL
    print("recovery_key", recovery_key, flush=True)

    fresh_q = urllib.parse.urlencode(
        {"fresh": "1", "cf_test_phone": PHONE, "store_slug": STORE}
    )
    code_f, _ = http("GET", f"/demo/store?{fresh_q}")
    report["fresh_http"] = code_f
    save("02_fresh_session.json", {"http": code_f, "note": "html_omitted"})
    print("fresh", code_f, flush=True)

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
    code_a, abandon_body = http("POST", "/api/cart-event", body=abandon_payload)
    report["abandon_http"] = code_a
    report["abandon_response"] = abandon_body
    save(
        "04_abandon.json",
        {"http": code_a, "body": abandon_body, "recovery_key": recovery_key},
    )
    print("abandon", code_a, abandon_body, flush=True)
    if code_a != 200 or not isinstance(abandon_body, dict):
        report["abort"] = "abandon_failed"
        save("00_pilot_report.json", report)
        print("ABORT: abandon failed", flush=True)
        return 3

    reason_payload = {
        "store": STORE,
        "store_slug": STORE,
        "session_id": session_id,
        "cart_id": cart_id,
        "reason": REASON,
        "custom_text": CUSTOM_REASON,
        "customer_phone": PHONE,
        "checkout_url": CHECKOUT_URL,
        "cart_url": CHECKOUT_URL,
    }
    code_r, reason_body = http("POST", "/api/cartflow/reason", body=reason_payload)
    report["reason_arm"] = {"http": code_r, "body": reason_body}
    save(
        "03b_reason_arm.json",
        {"http": code_r, "body": reason_body, "recovery_key": recovery_key},
    )
    print("reason_arm", code_r, reason_body, flush=True)
    if code_r != 200 or not (
        isinstance(reason_body, dict) and reason_body.get("ok") is True
    ):
        report["abort"] = "reason_arm_failed"
        save("00_pilot_report.json", report)
        print("ABORT: reason arm failed — no second cart", flush=True)
        return 3

    code_e0, ev0 = http(
        "GET",
        f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(recovery_key)}",
    )
    save("04b_after_reason_evidence.json", {"http": code_e0, "body": ev0})
    print(
        "after_reason schedules",
        (ev0 or {}).get("schedule_rows") if isinstance(ev0, dict) else None,
        flush=True,
    )

    delay_s = float(abandon_body.get("recovery_delay_seconds") or 60.0)
    sched = (ev0 or {}).get("schedule_rows") if isinstance(ev0, dict) else None
    if isinstance(sched, list) and sched:
        report["schedule_ids_early"] = [
            s.get("id") for s in sched if isinstance(s, dict)
        ]
    wait_s = max(90.0, delay_s + 50.0)
    report["wait_seconds"] = wait_s
    save("00_pilot_report.json", report)
    print(f"waiting {wait_s:.0f}s for scheduled recovery execution…", flush=True)
    time.sleep(wait_s)

    final_evidence: Any = None
    for i in range(16):
        code_e, evidence = http(
            "GET",
            f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(recovery_key)}",
        )
        snap = {"http": code_e, "body": evidence, "t": time.time()}
        save(f"05_evidence_poll_{i:02d}.json", snap)
        providers = (
            (evidence or {}).get("providers_seen") if isinstance(evidence, dict) else None
        )
        logs = (
            (evidence or {}).get("recovery_logs") or []
            if isinstance(evidence, dict)
            else []
        )
        print(
            "evidence",
            i,
            code_e,
            "logs",
            len(logs),
            "providers",
            providers,
            "meta",
            (evidence or {}).get("meta_path_used") if isinstance(evidence, dict) else None,
            flush=True,
        )
        if isinstance(evidence, dict) and evidence.get("ok") and (
            evidence.get("meta_path_used")
            or evidence.get("twilio_path_used")
            or any(
                str(x.get("status") or "").lower()
                in ("sent_real", "whatsapp_failed", "failed", "queued")
                for x in logs
                if isinstance(x, dict)
            )
        ):
            final_evidence = evidence
            break
        time.sleep(15)

    if final_evidence is None:
        _code_e, evidence = http(
            "GET",
            f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(recovery_key)}",
        )
        final_evidence = evidence if isinstance(evidence, dict) else {"raw": evidence}

    _code_t, timeline = http(
        "GET",
        f"/dev/recovery-truth?recovery_key={urllib.parse.quote(recovery_key)}",
    )
    _code_o, operational = http(
        "GET",
        f"/dev/recovery-operational-truth?recovery_key={urllib.parse.quote(recovery_key)}",
    )
    save("06_timeline.json", timeline)
    save("07_operational.json", operational)
    save("08_final_evidence.json", final_evidence)

    logs = (
        (final_evidence or {}).get("recovery_logs")
        if isinstance(final_evidence, dict)
        else []
    )
    meta_sid = None
    provider = None
    log_statuses = []
    for lg in logs or []:
        if not isinstance(lg, dict):
            continue
        log_statuses.append(
            {
                "status": lg.get("status"),
                "provider": lg.get("provider"),
                "sid": lg.get("provider_message_sid"),
                "preview": (lg.get("message_preview") or "")[:80],
                "template_name": lg.get("template_name"),
                "error_code": lg.get("error_code"),
            }
        )
        p = str(lg.get("provider") or "").lower()
        sid = lg.get("provider_message_sid")
        if p == "meta" and sid and meta_sid is None:
            meta_sid = sid
            provider = "meta"
        elif sid and provider is None:
            meta_sid = sid
            provider = lg.get("provider")

    sched_rows = (
        (final_evidence or {}).get("schedule_rows")
        if isinstance(final_evidence, dict)
        else None
    )
    summary = {
        "recovery_key": recovery_key,
        "schedule_ids": [
            s.get("id") for s in (sched_rows or []) if isinstance(s, dict)
        ],
        "schedule_rows": sched_rows,
        "provider": provider,
        "meta_message_id": meta_sid,
        "log_statuses": log_statuses,
        "meta_path_used": (
            (final_evidence or {}).get("meta_path_used")
            if isinstance(final_evidence, dict)
            else None
        ),
        "twilio_path_used": (
            (final_evidence or {}).get("twilio_path_used")
            if isinstance(final_evidence, dict)
            else None
        ),
        "runtime_provider": (
            (final_evidence or {}).get("runtime_provider")
            if isinstance(final_evidence, dict)
            else None
        ),
        "delivery_truth": (
            (final_evidence or {}).get("delivery_truth")
            if isinstance(final_evidence, dict)
            else None
        ),
        "template_expected": "cartflow_cart_reminder_ar_v2",
        "store_display_name": store_name,
        "checkout_url": CHECKOUT_URL,
        "no_button_clicks": True,
        "providers_seen": (
            (final_evidence or {}).get("providers_seen")
            if isinstance(final_evidence, dict)
            else None
        ),
        "sanitized_template_params": (
            (final_evidence or {}).get("sanitized_template_params")
            if isinstance(final_evidence, dict)
            else None
        ),
        "body_param": (
            (final_evidence or {}).get("body_param")
            if isinstance(final_evidence, dict)
            else None
        ),
        "button_url_param": (
            (final_evidence or {}).get("button_url_param")
            if isinstance(final_evidence, dict)
            else None
        ),
    }
    report["summary"] = summary
    report["timeline"] = timeline
    report["operational"] = operational
    report["final_evidence"] = final_evidence
    save("09_summary.json", summary)
    save("00_pilot_report.json", report)

    print("=== PILOT RESULT ===", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)

    if summary.get("twilio_path_used"):
        print("FAIL: twilio_path_used — STOP no retry", flush=True)
        return 4
    if provider != "meta" or not meta_sid:
        print("FAIL: meta not accepted — STOP no retry", flush=True)
        return 5
    print(
        "PASS: Meta Graph accepted — STOP await phone visual confirmation",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
