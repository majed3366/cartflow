# -*- coding: utf-8 -*-
"""One live Meta pilot to capture wire-level dispatch evidence. No retry."""
from __future__ import annotations

import json
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
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
    mask_phone_digits,
)

BASE = "https://smartreplyai.net"
EVIDENCE_DIR = (
    ROOT / "docs" / "architecture" / "meta_dispatch_request_evidence_v1"
)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
JOURNEY_DIR = (
    ROOT
    / "docs"
    / "architecture"
    / "meta_production_pilot_v1"
    / "evidence"
    / "journey_v2_wire_capture_once"
)
JOURNEY_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE = "cartflow_cart_reminder_ar_v2"
DEPLOY_PREFIX = "d"  # any post-wire deploy; tightened after push


def http(method: str, path: str, body: dict | None = None, timeout: float = 60.0):
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
                return int(resp.status), json.loads(raw) if raw else None
            except json.JSONDecodeError:
                return int(resp.status), {"_raw": raw[:2000]}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return int(exc.code), json.loads(raw) if raw else {"error": str(exc)}
        except json.JSONDecodeError:
            return int(exc.code), {"_raw": raw[:2000]}


def save(path: Path, name: str, payload: Any) -> None:
    (path / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> int:
    # Discover expected SHA from homepage
    req = urllib.request.Request(BASE + "/", method="GET", headers={"Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        sha = resp.headers.get("X-CartFlow-Git-Sha") or ""
    print("api_git_sha", sha, flush=True)
    save(JOURNEY_DIR, "00_deploy_sha.json", {"sha": sha})

    code_pf, pf = http("GET", "/dev/meta-pilot-preflight")
    save(JOURNEY_DIR, "01_preflight.json", pf)
    if code_pf != 200 or not isinstance(pf, dict) or not pf.get("provider_is_meta"):
        print("ABORT preflight", flush=True)
        return 2

    token = uuid.uuid4().hex[:12]
    session_id = f"meta_wire_cap_{token}"
    cart_id = f"cf_cart_meta_wire_cap_{token}"
    recovery_key = f"{PILOT_STORE}:{cart_id}"
    print("recovery_key", recovery_key, flush=True)

    code_a, ab = http(
        "POST",
        "/api/cart-event",
        build_abandon_payload(session_id=session_id, cart_id=cart_id),
    )
    save(JOURNEY_DIR, "03_abandon.json", {"http": code_a, "body": ab})
    code_r, rs = http(
        "POST",
        "/api/cartflow/reason",
        build_cartflow_reason_payload(
            session_id=session_id,
            cart_id=cart_id,
            customer_phone=PILOT_PHONE_E164,
            checkout_url=PILOT_CHECKOUT_URL,
        ),
    )
    save(JOURNEY_DIR, "04_reason.json", {"http": code_r, "body": rs})
    if code_r != 200:
        return 3

    schedule_id = None
    due_at = None
    expected_mask = mask_phone_digits(PILOT_PHONE_DIGITS)
    for i in range(40):
        _c, ev = http(
            "GET",
            f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(recovery_key)}",
        )
        save(JOURNEY_DIR, f"05_pre_due_{i:02d}.json", ev)
        if isinstance(ev, dict):
            ac = ev.get("abandoned_cart") or {}
            crr = ev.get("cart_recovery_reason") or {}
            sched = ev.get("schedule_rows") or []
            cart_ok = (ac.get("cart_url") or "") == PILOT_CHECKOUT_URL
            if sched:
                schedule_id = sched[0].get("id")
                due_at = sched[0].get("due_at")
            print("pre_due", i, ac.get("phone_masked"), cart_ok, schedule_id, flush=True)
            if (
                ac.get("phone_masked") == expected_mask
                and crr.get("phone_masked") == expected_mask
                and cart_ok
                and schedule_id
            ):
                break
        time.sleep(1)

    if due_at:
        dt = datetime.fromisoformat(str(due_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        wait_s = min(200.0, max(5.0, (dt.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds() + 50.0))
    else:
        wait_s = 100.0
    print(f"waiting {wait_s:.0f}s", flush=True)
    time.sleep(wait_s)

    final = None
    for i in range(24):
        _c, ev = http(
            "GET",
            f"/dev/meta-pilot-evidence?recovery_key={urllib.parse.quote(recovery_key)}",
        )
        save(JOURNEY_DIR, f"07_exec_{i:02d}.json", ev)
        if isinstance(ev, dict):
            logs = ev.get("recovery_logs") or []
            if ev.get("meta_path_used") or any(
                str(x.get("status")) in ("whatsapp_failed", "sent_real") for x in logs if isinstance(x, dict)
            ):
                final = ev
                break
        time.sleep(10)
    if final is None:
        final = ev if isinstance(ev, dict) else {}
    save(JOURNEY_DIR, "10_final_evidence.json", final)

    code_d, dispatch = http(
        "GET",
        f"/dev/meta-dispatch-request?recovery_key={urllib.parse.quote(recovery_key)}",
    )
    save(JOURNEY_DIR, "11_dispatch_request.json", {"http": code_d, "body": dispatch})
    evidence = (dispatch or {}).get("evidence") if isinstance(dispatch, dict) else None
    if isinstance(evidence, dict):
        save(EVIDENCE_DIR, "request_payload.json", evidence)
        # summary md from fields
        req = evidence.get("request") or {}
        tpl = req.get("template") or {}
        resp = evidence.get("response") or {}
        md = [
            "# Meta Dispatch Request Evidence V1",
            "",
            f"- recovery_key: `{recovery_key}`",
            f"- schedule_id: `{schedule_id}`",
            f"- api_git_sha: `{sha}`",
            f"- phone_number_id: `{evidence.get('resolved_phone_number_id')}`",
            f"- template: `{tpl.get('name')}`",
            f"- language: `{(tpl.get('language') or {}).get('code')}`",
            f"- to: `{req.get('to')}`",
            f"- graph_endpoint: `{req.get('graph_endpoint')}`",
            f"- verification: `{evidence.get('verification')}`",
            "",
            "## Graph response",
            "",
            f"```json\n{json.dumps(resp, ensure_ascii=False, indent=2)}\n```",
            "",
        ]
        (EVIDENCE_DIR / "request_summary.md").write_text("\n".join(md), encoding="utf-8")

    fail = None
    for lg in (final or {}).get("recovery_logs") or []:
        if isinstance(lg, dict) and lg.get("status") == "whatsapp_failed":
            fail = lg
    summary = {
        "recovery_key": recovery_key,
        "schedule_id": schedule_id,
        "api_git_sha": sha,
        "dispatch_http": code_d,
        "dispatch_evidence": evidence,
        "failed_log": fail,
        "meta_path_used": (final or {}).get("meta_path_used"),
        "twilio_path_used": (final or {}).get("twilio_path_used"),
    }
    save(JOURNEY_DIR, "12_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)
    print("STOP", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
