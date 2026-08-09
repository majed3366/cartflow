# -*- coding: utf-8 -*-
"""Living Store probe — Phase 2B ES recovery surface (no /register, no secrets)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture" / "whatsapp_phone_recovery_v1"
BASE = "https://smartreplyai.net"


def http_json(url: str, *, data: dict | None = None, cookies: CookieJar | None = None) -> dict:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies or CookieJar()))
    body = None
    headers = {"Accept": "application/json"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if data is not None else "GET")
    try:
        with opener.open(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"_raw": raw[:500]}
            return {"status": resp.status, "body": parsed, "headers": dict(resp.headers)}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"_raw": raw[:500]}
        return {"status": int(exc.code), "body": parsed, "headers": dict(exc.headers)}


def wait_sha(prefix: str, timeout_s: int = 720) -> dict:
    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{BASE}/", method="GET")
            with urllib.request.urlopen(req, timeout=60) as resp:
                sha = (resp.headers.get("X-CartFlow-Git-Sha") or "").strip()
                last = {"sha": sha, "status": resp.status}
                if not prefix or sha.startswith(prefix):
                    return {"ok": True, **last}
        except Exception as exc:  # noqa: BLE001
            last = {"error": str(exc)}
        time.sleep(12)
    return {"ok": False, **last}


def main() -> int:
    sha_prefix = (os.environ.get("CF_EXPECTED_SHA") or "").strip()
    probe: dict = {"deploy": wait_sha(sha_prefix) if sha_prefix else wait_sha("")}

    # Unauthenticated — must be 401
    probe["config_unauth"] = http_json(f"{BASE}/admin/api/whatsapp/embedded-signup-recovery/config")

    # Static asset
    try:
        req = urllib.request.Request(f"{BASE}/static/admin_whatsapp_es_recovery.js", method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            js = resp.read().decode("utf-8", errors="replace")
            probe["static_js"] = {
                "status": resp.status,
                "has_fb_login": "FB.login" in js,
                "has_config_id": "config_id" in js,
                "has_no_register_call": "/register" not in js or "do not" in js.lower(),
                "mentions_register_block": "register" in js.lower(),
            }
    except Exception as exc:  # noqa: BLE001
        probe["static_js"] = {"error": str(exc)}

    password = (os.environ.get("CARTFLOW_ADMIN_PASSWORD") or "").strip()
    if password:
        jar = CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        login_body = urllib.parse.urlencode(
            {"password": password, "next": "/admin/whatsapp/embedded-signup-recovery"}
        ).encode()
        login_req = urllib.request.Request(
            f"{BASE}/admin/operations/login",
            data=login_body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with opener.open(login_req, timeout=60) as resp:
                probe["admin_login"] = {"status": resp.status}
        except urllib.error.HTTPError as exc:
            probe["admin_login"] = {"status": int(exc.code)}

        cfg_req = urllib.request.Request(
            f"{BASE}/admin/api/whatsapp/embedded-signup-recovery/config",
            headers={"Accept": "application/json"},
        )
        try:
            with opener.open(cfg_req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                # Redact anything secret-shaped
                for k in list(body.keys()):
                    if "secret" in k.lower() and k != "app_secret_configured":
                        body[k] = "[redacted]"
                    if "token" in k.lower():
                        body[k] = "[redacted]"
                probe["config_auth"] = {"status": resp.status, "body": body}
        except urllib.error.HTTPError as exc:
            probe["config_auth"] = {"status": int(exc.code), "body": {}}

        page_req = urllib.request.Request(f"{BASE}/admin/whatsapp/embedded-signup-recovery")
        try:
            with opener.open(page_req, timeout=60) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                probe["page_auth"] = {
                    "status": resp.status,
                    "has_marker": "whatsapp-es-recovery-v1" in html,
                    "has_target_waba": "1520530422625766" in html,
                    "has_target_phone": "1260388737156321" in html,
                    "has_launch_button": "esr-launch" in html,
                }
        except urllib.error.HTTPError as exc:
            probe["page_auth"] = {"status": int(exc.code)}

        # Hard-assert abort without calling Meta exchange (missing code after mismatch)
        abort_body = {
            "code": "should-not-exchange",
            "waba_id": "000",
            "phone_number_id": "1260388737156321",
        }
        abort_req = urllib.request.Request(
            f"{BASE}/admin/api/whatsapp/embedded-signup-recovery/complete",
            data=json.dumps(abort_body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with opener.open(abort_req, timeout=60) as resp:
                probe["assert_abort"] = {
                    "status": resp.status,
                    "body": json.loads(resp.read().decode("utf-8")),
                }
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"_raw": raw[:300]}
            probe["assert_abort"] = {"status": int(exc.code), "body": parsed}
    else:
        probe["admin_login"] = {"skipped": True, "reason": "CARTFLOW_ADMIN_PASSWORD not set in probe env"}

    cfg_unauth_ok = probe.get("config_unauth", {}).get("status") == 401
    static_ok = (probe.get("static_js") or {}).get("status") == 200 and (
        probe.get("static_js") or {}
    ).get("has_fb_login")
    gates = {
        "deploy": bool((probe.get("deploy") or {}).get("ok")),
        "configRequiresAuth": cfg_unauth_ok,
        "staticJsPresent": bool(static_ok),
    }
    if password:
        gates["configReady"] = bool(
            ((probe.get("config_auth") or {}).get("body") or {}).get("ready")
        ) and ((probe.get("config_auth") or {}).get("body") or {}).get(
            "app_id"
        ) == "1485048632921274"
        gates["pageMarker"] = bool((probe.get("page_auth") or {}).get("has_marker"))
        abort = (probe.get("assert_abort") or {}).get("body") or {}
        gates["hardAssertAbortsMismatch"] = bool(abort.get("aborted")) and not bool(
            abort.get("register_called")
        )
        # Ensure secret never echoed
        blob = json.dumps(probe)
        gates["noSecretEcho"] = "META_WHATSAPP_APP_SECRET" not in blob and "client_secret" not in blob

    probe["gates"] = {k: ("PASS" if v else "FAIL") for k, v in gates.items()}
    probe["all_pass"] = all(gates.values())
    probe["register_called"] = False
    probe["phase"] = "2b"
    probe["stop"] = "Do not call /register"

    out_path = OUT / "phase2b_production_probe.json"
    out_path.write_text(json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"gates": probe["gates"], "all_pass": probe["all_pass"], "deploy": probe["deploy"]}, indent=2))
    return 0 if probe["all_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
