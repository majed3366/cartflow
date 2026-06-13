# -*- coding: utf-8 -*-
"""Production verify: Meta WhatsApp connection status (admin session required)."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = "https://smartreplyai.net"
OUT = os.path.join(
    os.path.dirname(__file__),
    "_meta_connection_verify_prod_v1_out",
    "verify_report.json",
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _login_session(password: str) -> urllib.request.OpenerDirector:
    jar = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(jar)
    data = urllib.parse.urlencode(
        {"password": password, "next": "/admin/whatsapp"}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/admin/operations/login",
        data=data,
        method="POST",
    )
    opener.open(req, timeout=30)
    return opener


def _fetch_meta_status(opener: urllib.request.OpenerDirector) -> dict:
    req = urllib.request.Request(f"{BASE}/admin/api/whatsapp/meta-status")
    with opener.open(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def main() -> int:
    password = (os.environ.get("CARTFLOW_ADMIN_PASSWORD") or "").strip()
    if not password:
        print("CARTFLOW_ADMIN_PASSWORD required", file=sys.stderr)
        return 1

    report: dict = {
        "audit": "meta_connection_verification_prod_v1",
        "captured_at_utc": _utc(),
        "base": BASE,
        "pass": False,
        "checks": {},
        "response": None,
    }

    try:
        opener = _login_session(password)
        body = _fetch_meta_status(opener)
        report["response"] = body
        text = json.dumps(body)
        report["checks"] = {
            "connected": body.get("connected") is True,
            "meta_response_ok": body.get("meta_response_ok") is True,
            "display_phone_number": bool(body.get("display_phone_number")),
            "verified_name": bool(body.get("verified_name")),
            "phone_number_id": bool(body.get("phone_number_id")),
            "waba_id": bool(body.get("waba_id")),
            "verified_at": bool(body.get("verified_at")),
            "no_token_leak": "access_token" not in body and password not in text,
            "error_shown_if_any": body.get("error") is None or isinstance(body.get("error"), str),
        }
        report["pass"] = all(report["checks"].values())
    except urllib.error.HTTPError as exc:
        report["error"] = f"http_{exc.code}"
        try:
            report["response"] = json.loads(exc.read().decode("utf-8", "replace"))
        except Exception:
            report["response"] = None
    except Exception as exc:
        report["error"] = str(exc)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print(json.dumps({"pass": report["pass"], "checks": report.get("checks"), "out": OUT}, indent=2))
    return 0 if report.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
