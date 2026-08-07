# -*- coding: utf-8 -*-
"""Arm waiting cart + wait for Meta send. Same journey — not a second cart."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://smartreplyai.net"
PHONE = "+966546518011"
STORE = "demo"
SESSION = "meta_pilot_v2_final_fcca85c6acf2"
CART = "cf_cart_meta_pilot_v2_final_fcca85c6acf2"
RK = f"{STORE}:{CART}"
CHECKOUT_URL = f"{BASE}/demo/store/checkout"
CUSTOM_TEXT = "سبب اخر"
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
    # Store display name (best-effort)
    store_name = "مساعد المتجر"
    for path in (
        f"/api/stores/{STORE}/public",
        f"/demo/api/store-config?store={STORE}",
        f"/api/cartflow/store-config?store_slug={STORE}",
    ):
        code, body = http("GET", path)
        if code == 200 and isinstance(body, dict):
            cand = (
                body.get("widget_display_name")
                or body.get("widget_name")
                or body.get("store_name")
                or (body.get("store") or {}).get("widget_display_name")
                if isinstance(body.get("store"), dict)
                else None
            )
            if cand:
                store_name = str(cand)
                save(
                    "01b_public_config_store_name.json",
                    {"http": code, "path": path, "widget_display_name": store_name},
                )
                break
    else:
        save(
            "01b_public_config_store_name.json",
            {
                "http": None,
                "widget_display_name": store_name,
                "note": "fallback_known_demo_name",
            },
        )
    print("store_display_name", store_name, flush=True)

    reason_payload = {
        "store": STORE,
        "store_slug": STORE,
        "session_id": SESSION,
        "cart_id": CART,
        "reason": "other",
        "custom_text": CUSTOM_TEXT,
        "customer_phone": PHONE,
        "checkout_url": CHECKOUT_URL,
        "cart_url": CHECKOUT_URL,
    }
    code_r, reason_body = http("POST", "/api/cartflow/reason", body=reason_payload)
    save(
        "03b_reason_arm.json",
        {"http": code_r, "body": reason_body, "recovery_key": RK},
    )
    print("reason_arm", code_r, reason_body, flush=True)
    if code_r != 200 or not (
        isinstance(reason_body, dict) and reason_body.get("ok") is True
    ):
        print("ABORT: reason arm failed — STOP no second cart", flush=True)
        return 3

    code_e0, ev0 = http(
        "GET",
        f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(RK)}",
    )
    save("04b_after_reason_evidence.json", {"http": code_e0, "body": ev0})
    sched = (ev0 or {}).get("schedule_rows") if isinstance(ev0, dict) else None
    print("after_reason schedules", sched, flush=True)

    wait_s = 110.0
    print(f"waiting {wait_s:.0f}s for scheduled recovery execution…", flush=True)
    time.sleep(wait_s)

    final_evidence: Any = None
    for i in range(16):
        code_e, evidence = http(
            "GET",
            f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(RK)}",
        )
        snap = {"http": code_e, "body": evidence, "t": time.time()}
        save(f"05_evidence_poll_{i:02d}.json", snap)
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
            (evidence or {}).get("providers_seen") if isinstance(evidence, dict) else None,
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
        _c, evidence = http(
            "GET",
            f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(RK)}",
        )
        final_evidence = evidence if isinstance(evidence, dict) else {"raw": evidence}

    _ct, timeline = http(
        "GET", f"/dev/recovery-truth?recovery_key={urllib.parse.quote(RK)}"
    )
    _co, operational = http(
        "GET",
        f"/dev/recovery-operational-truth?recovery_key={urllib.parse.quote(RK)}",
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
                "preview": (lg.get("message_preview") or "")[:120],
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
        "recovery_key": RK,
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
    report = {
        "pilot": "meta_first_real_recovery_journey_v2_final_execute",
        "recovery_key": RK,
        "session_id": SESSION,
        "cart_id": CART,
        "reason_arm": {"http": code_r, "body": reason_body},
        "summary": summary,
        "timeline": timeline,
        "operational": operational,
        "final_evidence": final_evidence,
        "no_retry": True,
        "no_button_clicks": True,
        "scheduler_preflight_line": (
            "[SCHEDULER META RUNTIME] role=scheduler whatsapp_provider=meta "
            "meta_template_name=cartflow_cart_reminder_ar_v2 "
            "access_token_configured=true phone_number_id_configured=true "
            "waba_id_configured=true ready_for_meta_recovery=true"
        ),
    }
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
