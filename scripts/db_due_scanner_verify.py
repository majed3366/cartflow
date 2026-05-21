# -*- coding: utf-8 -*-
"""
Visible verification report for the manual DB due recovery scanner.

Run:
  python scripts/db_due_scanner_verify.py
  python scripts/db_due_scanner_verify.py --json

Does not change production runtime, scanner, or recovery execution paths.
Mocks only ``main._run_recovery_sequence_after_cart_abandoned`` so WhatsApp is not sent.
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import sys
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, patch

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import main  # noqa: E402, F401

from extensions import db  # noqa: E402
from models import CartRecoveryLog, RecoverySchedule  # noqa: E402
from services.recovery_db_due_scanner import scan_due_recovery_schedules  # noqa: E402
from services.recovery_restart_survival import (  # noqa: E402
    STATUS_SCHEDULED,
    _TERMINAL,
    persist_recovery_schedule_durable,
)

RUN1_LOG_TAGS = [
    "DB DUE SCANNER START",
    "DB DUE SCANNER FOUND",
    "DB DUE SCANNER DISPATCH",
    "RECOVERY EXECUTION ENTRY",
    "RECOVERY CLAIM ATTEMPT",
    "RECOVERY CLAIMED",
    "RECOVERY TERMINAL UPDATE",
    "DB DUE SCANNER DONE",
]

WA_SUCCESS_STATUSES = frozenset({"mock_sent", "sent_real", "queued", "sent"})


def _utc_now_cmp() -> datetime:
    return datetime.now(timezone.utc)


def _is_due(due_at: Optional[datetime]) -> bool:
    if due_at is None:
        return False
    now = _utc_now_cmp()
    if due_at.tzinfo is None:
        return due_at <= now.replace(tzinfo=None)
    return due_at <= now


def _row_snapshot(row: Optional[RecoverySchedule]) -> Dict[str, Any]:
    if row is None:
        return {}
    status = str(row.status or "")
    return {
        "schedule_id": int(row.id),
        "recovery_key": row.recovery_key,
        "step": int(row.step),
        "status": status,
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "is_due": _is_due(row.due_at),
        "is_terminal": status in _TERMINAL,
        "terminal_evidence": {
            "status_in_terminal_set": status in _TERMINAL,
            "last_error": (row.last_error or None),
        },
    }


def _whatsapp_log_snapshot(row: Optional[RecoverySchedule]) -> Dict[str, Any]:
    if row is None:
        return {"send_log_count": 0, "successful_send_count": 0}
    q = db.session.query(CartRecoveryLog).filter(
        CartRecoveryLog.session_id == row.session_id,
        CartRecoveryLog.cart_id == row.cart_id,
        CartRecoveryLog.step == int(row.step),
    )
    logs = q.all()
    success = [
        lg
        for lg in logs
        if str(getattr(lg, "status", "") or "").lower() in WA_SUCCESS_STATUSES
    ]
    return {
        "send_log_count": len(logs),
        "successful_send_count": len(success),
        "statuses": sorted({str(getattr(lg, "status", "") or "") for lg in logs}),
    }


def _find_logs(buf: str, tags: List[str]) -> Dict[str, bool]:
    return {t: (f"[{t}]" in buf) for t in tags}


def _scanner_summary(
    out: Dict[str, Any], *, pass_ok: bool, logs_found: Dict[str, bool]
) -> Dict[str, Any]:
    stale = out.get("stale_running_repair") if isinstance(out.get("stale_running_repair"), dict) else {}
    finalized = int(stale.get("finalized", 0)) + int(stale.get("repaired", 0))
    outcomes = out.get("outcomes") if isinstance(out.get("outcomes"), list) else []
    terminal_from_outcomes = sum(
        1 for o in outcomes if isinstance(o, dict) and o.get("dispatched")
    )
    return {
        "found": int(out.get("found", 0)),
        "dispatched": int(out.get("dispatched", 0)),
        "skipped": int(out.get("skipped", 0)),
        "stale_running_finalized": finalized,
        "outcomes_count": len(outcomes),
        "terminal_or_dispatched_count": terminal_from_outcomes,
        "logs_required": logs_found,
        "logs_all_present": all(logs_found.values()) if logs_found else False,
        "pass": pass_ok,
    }


def _locate_or_create_due_row() -> Tuple[RecoverySchedule, str]:
    now = _utc_now_cmp()
    existing = (
        db.session.query(RecoverySchedule)
        .filter(
            RecoverySchedule.status == STATUS_SCHEDULED,
            RecoverySchedule.due_at <= now,
        )
        .order_by(RecoverySchedule.due_at.asc())
        .first()
    )
    if existing is not None:
        return existing, "reused_existing_due_row"

    rk = f"demo:db-scanner-{uuid.uuid4().hex[:8]}"
    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id=f"sess-{uuid.uuid4().hex[:6]}",
        cart_id=f"cart-{uuid.uuid4().hex[:6]}",
        reason_tag="other",
        abandon_event_phone="+966501112233",
        delay_seconds_scheduled=0.0,
        schedule_timing={
            "effective_delay_seconds": 0.0,
            "source": "reason_templates.messages",
        },
        recovery_context={"recovery_key": rk, "store_slug": "demo"},
    )
    assert row is not None
    row.due_at = now - timedelta(seconds=5)
    db.session.commit()
    return row, "created_test_due_row"


def _run_scanner_once() -> Tuple[Dict[str, Any], str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
            return_value=None,
        ):
            out = asyncio.run(
                scan_due_recovery_schedules(limit=25, source="db_due_scanner")
            )
    return out, buf.getvalue()


def _evaluate_run1(
    *,
    before: Optional[RecoverySchedule],
    out1: Dict[str, Any],
    after1: Optional[RecoverySchedule],
    logs1: str,
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if before is None or before.status != STATUS_SCHEDULED:
        errors.append("before_status_not_scheduled")
    if before is not None and not _is_due(before.due_at):
        errors.append("before_not_due")
    found1 = _find_logs(logs1, RUN1_LOG_TAGS)
    if out1.get("found", 0) < 1:
        errors.append("run1_found_zero")
    if out1.get("dispatched", 0) < 1:
        errors.append("run1_not_dispatched")
    if after1 is None or after1.status not in _TERMINAL:
        errors.append("run1_not_terminal")
    if not all(found1.values()):
        missing = [k for k, v in found1.items() if not v]
        errors.append(f"run1_missing_logs:{','.join(missing)}")
    return (len(errors) == 0, errors)


def _evaluate_run2(
    *,
    out2: Dict[str, Any],
    after1: Optional[RecoverySchedule],
    after2: Optional[RecoverySchedule],
    wa_before: Dict[str, Any],
    wa_after: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    status_unchanged = (
        after1 is not None
        and after2 is not None
        and after2.status == after1.status
    )
    no_redispatch = out2.get("dispatched", 0) == 0 and (
        out2.get("found", 0) == 0 or status_unchanged
    )
    if not no_redispatch:
        errors.append("run2_redispatch_or_found_due_again")
    if after2 is None or after2.status not in _TERMINAL:
        errors.append("run2_not_terminal")
    if wa_after.get("successful_send_count", 0) > wa_before.get("successful_send_count", 0):
        errors.append("run2_duplicate_whatsapp_log")
    return (len(errors) == 0, errors)


def build_verification_report() -> Dict[str, Any]:
    db.create_all()
    row, setup_action = _locate_or_create_due_row()
    schedule_id = int(row.id)

    db.session.expire_all()
    before_row = db.session.get(RecoverySchedule, schedule_id)
    before = _row_snapshot(before_row)
    wa_before = _whatsapp_log_snapshot(before_row)

    out1, logs1 = _run_scanner_once()
    db.session.expire_all()
    after1_row = db.session.get(RecoverySchedule, schedule_id)
    after1 = _row_snapshot(after1_row)
    wa_after_run1 = _whatsapp_log_snapshot(after1_row)
    found1 = _find_logs(logs1, RUN1_LOG_TAGS)
    run1_ok, run1_errors = _evaluate_run1(
        before=before_row, out1=out1, after1=after1_row, logs1=logs1
    )

    out2, logs2 = _run_scanner_once()
    db.session.expire_all()
    after2_row = db.session.get(RecoverySchedule, schedule_id)
    after2 = _row_snapshot(after2_row)
    wa_after_run2 = _whatsapp_log_snapshot(after2_row)
    run2_ok, run2_errors = _evaluate_run2(
        out2=out2,
        after1=after1_row,
        after2=after2_row,
        wa_before=wa_after_run1,
        wa_after=wa_after_run2,
    )

    verdict = "PASS" if run1_ok and run2_ok else "FAIL"
    return {
        "meta": {
            "script": "db_due_scanner_verify",
            "setup_action": setup_action,
            "schedule_id": schedule_id,
            "mocked_recovery_send": True,
            "scanner_source": "db_due_scanner",
        },
        "before": {**before, "whatsapp_logs": wa_before},
        "run1": {
            "scanner_out": out1,
            "summary": _scanner_summary(out1, pass_ok=run1_ok, logs_found=found1),
            "logs_found": found1,
            "errors": run1_errors,
        },
        "after": {
            "run1": {**after1, "whatsapp_logs": wa_after_run1},
        },
        "run2": {
            "scanner_out": out2,
            "summary": {
                "found": int(out2.get("found", 0)),
                "dispatched": int(out2.get("dispatched", 0)),
                "skipped": int(out2.get("skipped", 0)),
                "idempotent_safe": run2_ok,
                "status_unchanged": (
                    after1_row is not None
                    and after2_row is not None
                    and after1_row.status == after2_row.status
                ),
                "no_duplicate_whatsapp": wa_after_run2.get("successful_send_count", 0)
                <= wa_after_run1.get("successful_send_count", 0),
                "errors": run2_errors,
                "pass": run2_ok,
            },
            "row": {**after2, "whatsapp_logs": wa_after_run2},
            "logs_excerpt_lines": logs2.strip().splitlines()[-12:],
        },
        "verdict": verdict,
        "pass": verdict == "PASS",
    }


def _print_section(title: str) -> None:
    line = "=" * 72
    print(line, flush=True)
    print(title, flush=True)
    print(line, flush=True)


def _print_kv(label: str, value: Any, indent: int = 0) -> None:
    pad = " " * indent
    print(f"{pad}{label}: {value}", flush=True)


def print_human_report(report: Dict[str, Any]) -> None:
    _print_section("DB DUE SCANNER - MANUAL VERIFICATION REPORT")
    meta = report.get("meta") or {}
    _print_kv("Setup", meta.get("setup_action"))
    _print_kv("Schedule id", meta.get("schedule_id"))
    _print_kv("Recovery send", "MOCKED (no real WhatsApp)")
    print(flush=True)

    _print_section("1. BEFORE SCAN (run 1)")
    before = report.get("before") or {}
    for key in (
        "schedule_id",
        "recovery_key",
        "step",
        "status",
        "due_at",
        "updated_at",
        "is_due",
    ):
        _print_kv(key, before.get(key), indent=2)
    _print_kv("WhatsApp send logs (step)", before.get("whatsapp_logs"), indent=2)

    _print_section("2. RUN 1 - SCANNER SUMMARY")
    run1 = report.get("run1") or {}
    summary = run1.get("summary") or {}
    _print_kv("found", summary.get("found"), indent=2)
    _print_kv("dispatched", summary.get("dispatched"), indent=2)
    _print_kv("skipped", summary.get("skipped"), indent=2)
    _print_kv("stale_running_finalized", summary.get("stale_running_finalized"), indent=2)
    _print_kv("terminal_or_dispatched_count", summary.get("terminal_or_dispatched_count"), indent=2)
    _print_kv("required logs present", summary.get("logs_all_present"), indent=2)
    logs = summary.get("logs_required") or {}
    for tag, ok in logs.items():
        _print_kv(tag, "yes" if ok else "MISSING", indent=4)
    _print_kv("RUN 1 PASS", "yes" if summary.get("pass") else "no", indent=2)
    if run1.get("errors"):
        _print_kv("errors", run1.get("errors"), indent=2)

    _print_section("3. AFTER SCAN (run 1)")
    after_run1 = (report.get("after") or {}).get("run1") or {}
    for key in (
        "schedule_id",
        "recovery_key",
        "step",
        "status",
        "updated_at",
        "is_terminal",
    ):
        _print_kv(key, after_run1.get(key), indent=2)
    _print_kv("terminal_evidence", after_run1.get("terminal_evidence"), indent=2)
    _print_kv("WhatsApp send logs (step)", after_run1.get("whatsapp_logs"), indent=2)

    _print_section("4. RUN 2 - IDEMPOTENCY CHECK")
    run2 = report.get("run2") or {}
    r2s = run2.get("summary") or {}
    _print_kv("found", r2s.get("found"), indent=2)
    _print_kv("dispatched", r2s.get("dispatched"), indent=2)
    _print_kv("skipped", r2s.get("skipped"), indent=2)
    _print_kv("idempotent_safe (found=0 or no re-dispatch)", r2s.get("idempotent_safe"), indent=2)
    _print_kv("status unchanged", r2s.get("status_unchanged"), indent=2)
    _print_kv("no duplicate WhatsApp log", r2s.get("no_duplicate_whatsapp"), indent=2)
    _print_kv("RUN 2 PASS", "yes" if r2s.get("pass") else "no", indent=2)
    if r2s.get("errors"):
        _print_kv("errors", r2s.get("errors"), indent=2)

    _print_section("5. FINAL VERDICT")
    verdict = report.get("verdict", "FAIL")
    print(f"  {verdict}", flush=True)
    print(flush=True)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="DB due scanner visible verification")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full report as JSON (stdout only)",
    )
    args = parser.parse_args(argv)

    report = build_verification_report()
    if args.json:
        print(json.dumps(report, indent=2, default=str), flush=True)
    else:
        print_human_report(report)

    return 0 if report.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
