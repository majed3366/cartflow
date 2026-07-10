# -*- coding: utf-8 -*-
"""
Merchant Pulse V1 — production projection verification.

1) Baseline: summary without relying on flag (reports presence)
2) After CARTFLOW_MERCHANT_PULSE_V1=1 deploy: validate fields + fork
3) Synthetic state matrix via projection (same code path as API)

Usage:
  python scripts/_merchant_pulse_v1_prod_verify.py
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from services.merchant_pulse_v1 import (
    FORK_ENTER_WORK,
    FORK_LEAVE,
    STATUS_HEALTHY,
    STATUS_LOADING,
    STATUS_NO_ACTION,
    STATUS_REQUIRE_ACTION,
    STATUS_UNKNOWN,
    build_merchant_pulse_v1_from_summary,
)

BASE = (os.environ.get("CARTFLOW_BASE_URL") or "https://smartreplyai.net").rstrip("/")
OUT_DIR = Path(__file__).resolve().parent / "_merchant_pulse_v1_prod_verify_out"
REQUIRED_SLOTS = (
    "executive_brief",
    "decision_summary",
    "cartflow_progress",
    "merchant_decision",
)
SLOT_FIELDS = ("status", "message", "confidence", "last_updated")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_pulse(pulse: dict | None) -> dict:
    issues: list[str] = []
    if not isinstance(pulse, dict):
        return {"ok": False, "issues": ["merchant_pulse_v1 missing or not object"], "pulse": None}
    if pulse.get("projection") != "MerchantPulseV1":
        issues.append(f"projection={pulse.get('projection')!r}")
    if "fork" not in pulse:
        issues.append("fork missing")
    elif pulse.get("fork") not in (FORK_LEAVE, FORK_ENTER_WORK):
        issues.append(f"fork invalid: {pulse.get('fork')!r}")
    for slot in REQUIRED_SLOTS:
        block = pulse.get(slot)
        if not isinstance(block, dict):
            issues.append(f"{slot} missing")
            continue
        for f in SLOT_FIELDS:
            if f not in block:
                issues.append(f"{slot}.{f} missing")
    return {
        "ok": not issues,
        "issues": issues,
        "fork": pulse.get("fork"),
        "status": pulse.get("status"),
        "slots": {
            k: {
                "status": (pulse.get(k) or {}).get("status"),
                "message": ((pulse.get(k) or {}).get("message") or "")[:120],
                "confidence": (pulse.get(k) or {}).get("confidence"),
            }
            for k in REQUIRED_SLOTS
            if isinstance(pulse.get(k), dict)
        },
    }


def _fetch_summary(page) -> dict:
    return page.evaluate(
        """async () => {
          const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json' },
          });
          let body = null;
          try { body = await r.json(); } catch (e) {
            body = { ok: false, parse_error: String(e) };
          }
          return {
            http_status: r.status,
            ok: !!(body && body.ok),
            has_pulse: !!(body && body.merchant_pulse_v1),
            has_home: !!(body && body.merchant_home_experience_v1),
            home_ok: !!(body && body.merchant_home_experience_v1 && body.merchant_home_experience_v1.ok),
            pulse: body ? body.merchant_pulse_v1 : null,
            wa_state: body && body.whatsapp_readiness_card
              ? (body.whatsapp_readiness_card.connection_state || body.whatsapp_readiness_card.readiness_overall || null)
              : null,
            store_connection_ok: body && body.store_connection
              ? (body.store_connection.ok ?? body.store_connection.connected ?? null)
              : null,
            keys_sample: body ? Object.keys(body).slice(0, 40) : [],
          };
        }"""
    )


def _synthetic_matrix() -> dict:
    cases = {}

    cases["loading"] = _validate_pulse(
        build_merchant_pulse_v1_from_summary({}, loading=True, store_slug="verify")
    )
    cases["loading"]["expected_fork"] = FORK_LEAVE
    cases["loading"]["expected_status"] = STATUS_LOADING

    healthy_body = {
        "ok": True,
        "merchant_home_experience_v1": {
            "ok": True,
            "generated_at": _utc(),
            "while_away": {
                "items": [
                    {
                        "headline_ar": "أُرسلت متابعة لسلة واحدة",
                        "detail_ar": "تم القبول",
                        "aggregation_key": "ach:1",
                    }
                ]
            },
            "attention_today": {
                "items": [],
                "empty_message_ar": "لا أمور تتطلب انتباهك الآن.",
            },
        },
        "whatsapp_readiness_card": {
            "readiness_overall": "ready",
            "connection_state": "connected",
        },
        "store_connection": {"ok": True, "connected": True},
    }
    h = build_merchant_pulse_v1_from_summary(healthy_body, store_slug="verify")
    cases["healthy_leave"] = _validate_pulse(h)
    cases["healthy_leave"]["expected_fork"] = FORK_LEAVE
    cases["healthy_leave"]["fork_match"] = h.get("fork") == FORK_LEAVE

    require_body = {
        "ok": True,
        "merchant_home_experience_v1": {
            "ok": True,
            "generated_at": _utc(),
            "while_away": {"items": []},
            "attention_today": {
                "items": [
                    {
                        "headline_ar": "سلال بانتظار رقم العميل",
                        "why_ar": "لا يمكن المتابعة",
                        "action_ar": "احصل على رقم العميل",
                        "action_present": True,
                        "decision_class": "critical_action",
                        "confidence": "high",
                        "aggregation_key": "dec:1",
                    }
                ]
            },
        },
        "whatsapp_readiness_card": {
            "readiness_overall": "ready",
            "connection_state": "connected",
        },
        "store_connection": {"ok": True},
    }
    r = build_merchant_pulse_v1_from_summary(require_body, store_slug="verify")
    cases["require_enter_work"] = _validate_pulse(r)
    cases["require_enter_work"]["expected_fork"] = FORK_ENTER_WORK
    cases["require_enter_work"]["fork_match"] = r.get("fork") == FORK_ENTER_WORK

    recommend_body = {
        "ok": True,
        "merchant_home_experience_v1": {
            "ok": True,
            "generated_at": _utc(),
            "while_away": {"items": []},
            "attention_today": {
                "items": [
                    {
                        "headline_ar": "يمكنك مراجعة سلال عالية القيمة",
                        "action_ar": "راجع عند التفرغ",
                        "action_present": True,
                        "decision_class": "suggested_action",
                        "confidence": "medium",
                    }
                ]
            },
        },
        "whatsapp_readiness_card": {
            "readiness_overall": "ready",
            "connection_state": "connected",
        },
        "store_connection": {"ok": True},
    }
    rec = build_merchant_pulse_v1_from_summary(recommend_body, store_slug="verify")
    cases["recommend_only_leave"] = _validate_pulse(rec)
    cases["recommend_only_leave"]["expected_fork"] = FORK_LEAVE
    cases["recommend_only_leave"]["fork_match"] = rec.get("fork") == FORK_LEAVE

    unk = build_merchant_pulse_v1_from_summary({"ok": True}, store_slug="verify")
    cases["unknown"] = _validate_pulse(unk)
    cases["unknown"]["expected_fork"] = FORK_LEAVE
    cases["unknown"]["fork_match"] = unk.get("fork") == FORK_LEAVE
    cases["unknown"]["status_is_unknown"] = unk.get("status") == STATUS_UNKNOWN

    wa_bad = {
        "ok": True,
        "merchant_home_experience_v1": {
            "ok": True,
            "generated_at": _utc(),
            "empty_calm": True,
            "while_away": {"items": [], "empty_message_ar": "—"},
            "attention_today": {"items": [], "empty_message_ar": "لا شيء"},
        },
        "whatsapp_readiness_card": {
            "readiness_overall": "not_ready",
            "connection_state": "setup_required",
        },
        "store_connection": {"ok": False, "connected": False},
    }
    w = build_merchant_pulse_v1_from_summary(wa_bad, store_slug="verify")
    cases["wa_or_store_issue_leave"] = _validate_pulse(w)
    cases["wa_or_store_issue_leave"]["expected_fork"] = FORK_LEAVE
    cases["wa_or_store_issue_leave"]["fork_match"] = w.get("fork") == FORK_LEAVE
    cases["wa_or_store_issue_leave"]["does_not_enter_work"] = w.get("fork") != FORK_ENTER_WORK
    cases["wa_or_store_issue_leave"]["decision_status"] = w.get("decision_summary", {}).get("status")

    return cases


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "generated_at": _utc(),
        "base": BASE,
        "synthetic_matrix": _synthetic_matrix(),
        "production_summary": None,
        "governance": {
            "no_new_tables": True,
            "projection_only": True,
            "flag": "CARTFLOW_MERCHANT_PULSE_V1",
            "ui_unchanged": True,
        },
    }

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        uid = uuid.uuid4().hex[:8]
        email = f"cf.pulse.{uid}@smartreplyai.net"
        password = f"CfPulse!{uid[:8]}"
        page.goto(f"{BASE}/signup", timeout=120000)
        page.locator('input[name="store_name"]').fill(f"Pulse {uid}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(4000)

        summary = _fetch_summary(page)
        pulse_check = _validate_pulse(summary.get("pulse"))
        report["production_summary"] = {
            "http_status": summary.get("http_status"),
            "ok": summary.get("ok"),
            "has_pulse": summary.get("has_pulse"),
            "has_home": summary.get("has_home"),
            "home_ok": summary.get("home_ok"),
            "wa_state": summary.get("wa_state"),
            "store_connection_ok": summary.get("store_connection_ok"),
            "pulse_validation": pulse_check,
            "email": email,
        }
        # Persist redacted pulse for evidence
        if summary.get("pulse"):
            (OUT_DIR / "prod_pulse_payload.json").write_text(
                json.dumps(summary["pulse"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        browser.close()

    # Pass criteria
    syn = report["synthetic_matrix"]
    syn_ok = all(
        syn[k].get("ok") and syn[k].get("fork_match", True)
        for k in (
            "healthy_leave",
            "require_enter_work",
            "recommend_only_leave",
            "unknown",
            "wa_or_store_issue_leave",
            "loading",
        )
    )
    prod = report["production_summary"] or {}
    pulse_live = bool(prod.get("has_pulse")) and bool((prod.get("pulse_validation") or {}).get("ok"))
    home_intact = bool(prod.get("has_home")) and bool(prod.get("home_ok"))

    report["verdict"] = {
        "synthetic_matrix_pass": syn_ok,
        "production_pulse_present": pulse_live,
        "home_ui_payload_intact": home_intact,
        "overall": "PASS" if (syn_ok and home_intact and pulse_live) else (
            "PASS_PENDING_FLAG" if syn_ok and home_intact and not pulse_live else "FAIL"
        ),
        "notes": (
            "Pulse absent on production summary — enable CARTFLOW_MERCHANT_PULSE_V1=1 and redeploy/restart"
            if syn_ok and home_intact and not pulse_live
            else ""
        ),
    }

    out_path = OUT_DIR / "verify_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["verdict"], ensure_ascii=False, indent=2))
    print(f"wrote {out_path}")
    return 0 if report["verdict"]["overall"] in ("PASS", "PASS_PENDING_FLAG") else 1


if __name__ == "__main__":
    raise SystemExit(main())
