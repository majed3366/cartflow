# -*- coding: utf-8 -*-
"""
Reliability Program v1 — verification gate runner (read-only on production behavior).

Run: python scripts/reliability_v1_verification_gate.py

Emits JSON to stdout; use output to populate docs/reliability_v1_verification_gate.md.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

# Ensure project root on path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import main  # noqa: E402, F401

from extensions import db  # noqa: E402
from models import CartRecoveryLog, RecoverySchedule  # noqa: E402
from services.recovery_execution_boundary import execute_recovery_schedule  # noqa: E402
from services.recovery_restart_survival import (  # noqa: E402
    STATUS_COMPLETED,
    STATUS_FAILED_RESUME_STALE,
    STATUS_RUNNING,
    STATUS_SCHEDULED,
    STATUS_SKIPPED_DUPLICATE,
    claim_recovery_schedule_execution,
    finalize_recovery_schedule_durable,
    persist_recovery_schedule_durable,
    repair_stale_running_recovery_schedules,
    resume_one_schedule,
    run_recovery_resume_scan_sync,
)
from services.recovery_whatsapp_idempotency import (  # noqa: E402
    check_whatsapp_recovery_send_idempotency,
)


def _clear_tables() -> None:
    db.create_all()
    for model in (RecoverySchedule, CartRecoveryLog):
        for row in db.session.query(model).all():
            db.session.delete(row)
    db.session.commit()


def _row_snapshot(row: RecoverySchedule) -> Dict[str, Any]:
    return {
        "id": int(row.id),
        "recovery_key": row.recovery_key,
        "status": row.status,
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _find_logs(buf: str, tags: List[str]) -> Dict[str, bool]:
    return {t: (f"[{t}]" in buf or t in buf) for t in tags}


def _persist_demo_row(
    tag: str,
    *,
    delay_s: float = 60.0,
    phone: str = "+966501112233",
) -> RecoverySchedule:
    rk = f"demo:gate-{tag}-{uuid.uuid4().hex[:6]}"
    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id=f"sess-{tag}",
        cart_id=f"cart-{tag}",
        reason_tag="other",
        abandon_event_phone=phone,
        delay_seconds_scheduled=delay_s,
        schedule_timing={
            "effective_delay_seconds": delay_s,
            "source": "reason_templates.messages",
        },
        recovery_context={"recovery_key": rk, "store_slug": "demo"},
    )
    assert row is not None
    return row


def scenario_1_restart_during_delay() -> Dict[str, Any]:
    """Simulate restart: durable scheduled row, due past, resume executes."""
    _clear_tables()
    buf = io.StringIO()
    row = _persist_demo_row("s1-restart", delay_s=120.0)
    before = _row_snapshot(row)
    row.due_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db.session.commit()

    with redirect_stdout(buf):
        scan_dry = run_recovery_resume_scan_sync(
            max_dispatch=10, dry_run=True, force=True
        )
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "main.send_whatsapp",
                return_value={"ok": True},
            ):
                asyncio.run(
                    resume_one_schedule(row, dispatch=True)
                )
                db.session.expire_all()
                row2 = db.session.get(RecoverySchedule, int(row.id))

    after = _row_snapshot(row2) if row2 else {}
    logs = buf.getvalue()
    tags = [
        "RECOVERY RESUME SCAN",
        "RECOVERY RESUME CANDIDATE",
        "RECOVERY EXECUTION ENTRY",
        "RECOVERY CLAIM ATTEMPT",
        "RECOVERY CLAIMED",
        "RECOVERY EXECUTION CLAIMED",
        "RECOVERY EXECUTION FINISHED",
        "RECOVERY TERMINAL UPDATE",
    ]
    found = _find_logs(logs, tags)
    pass_ok = (
        before["status"] == STATUS_SCHEDULED
        and scan_dry.get("due_processed", 0) >= 1
        and after.get("status") not in (STATUS_RUNNING, STATUS_SCHEDULED)
        and found.get("RECOVERY EXECUTION ENTRY")
        and found.get("RECOVERY CLAIMED")
    )
    return {
        "scenario": 1,
        "name": "Restart during active delay (simulated)",
        "setup": "scheduled row 120s; due_at backdated; no live asyncio task; resume_one_schedule dispatch",
        "db_before": before,
        "db_after": after,
        "scan_dry": scan_dry,
        "logs_found": found,
        "log_excerpt": logs[-4000:] if len(logs) > 4000 else logs,
        "pass": pass_ok,
    }


def scenario_2_duplicate_dispatch() -> Dict[str, Any]:
    _clear_tables()
    buf = io.StringIO()
    row = _persist_demo_row("s2-dup")
    with redirect_stdout(buf):
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
        ) as mock_run:
            asyncio.run(
                execute_recovery_schedule(schedule_id=int(row.id), source="gate_dup_a")
            )
            asyncio.run(
                execute_recovery_schedule(schedule_id=int(row.id), source="gate_dup_b")
            )
            mock_run_count = mock_run.call_count
    logs = buf.getvalue()
    found = _find_logs(
        logs,
        [
            "RECOVERY CLAIM ATTEMPT",
            "RECOVERY CLAIMED",
            "RECOVERY CLAIM SKIPPED",
            "RECOVERY EXECUTION SKIPPED",
        ],
    )
    db.session.expire_all()
    row_f = db.session.get(RecoverySchedule, int(row.id))
    after = _row_snapshot(row_f) if row_f else {}
    pass_ok = (
        mock_run_count == 1
        and found.get("RECOVERY CLAIMED")
        and (
            found.get("RECOVERY CLAIM SKIPPED")
            or found.get("RECOVERY EXECUTION SKIPPED")
        )
    )
    return {
        "scenario": 2,
        "name": "Duplicate dispatch prevention",
        "db_after": after,
        "mock_run_count": mock_run_count,
        "logs_found": found,
        "log_excerpt": logs[-3000:],
        "pass": pass_ok,
    }


def scenario_3_resume_after_restart() -> Dict[str, Any]:
    _clear_tables()
    buf = io.StringIO()
    row = _persist_demo_row("s3-resume", delay_s=0.0)
    row.due_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()
    with redirect_stdout(buf):
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
            return_value=None,
        ):
            out = asyncio.run(
                execute_recovery_schedule(
                    schedule_id=int(row.id), source="resume_scan"
                )
            )
    db.session.expire_all()
    row_f = db.session.get(RecoverySchedule, int(row.id))
    logs = buf.getvalue()
    found = _find_logs(
        logs,
        [
            "RECOVERY EXECUTION ENTRY",
            "RECOVERY EXECUTION CLAIMED",
            "RECOVERY EXECUTION FINISHED",
            "RECOVERY TERMINAL UPDATE",
        ],
    )
    pass_ok = (
        out.get("ok") is True
        and row_f is not None
        and row_f.status not in (STATUS_RUNNING, STATUS_SCHEDULED)
        and all(found.get(t) for t in found)
    )
    return {
        "scenario": 3,
        "name": "Resume after restart",
        "execute_out": out,
        "db_after": _row_snapshot(row_f) if row_f else {},
        "logs_found": found,
        "log_excerpt": logs[-3000:],
        "pass": pass_ok,
    }


def scenario_4_stale_running() -> Dict[str, Any]:
    _clear_tables()
    buf = io.StringIO()
    row = _persist_demo_row("s4-stale")
    row.status = STATUS_RUNNING
    row.updated_at = datetime.now(timezone.utc) - timedelta(seconds=900)
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id=row.session_id,
            cart_id=row.cart_id,
            phone="+966501112233",
            message="sent",
            status="mock_sent",
            step=1,
            sent_at=datetime.now(timezone.utc),
        )
    )
    db.session.commit()
    before = _row_snapshot(row)
    with redirect_stdout(buf):
        repair = repair_stale_running_recovery_schedules(max_age_seconds=600)
    db.session.expire_all()
    row_f = db.session.get(RecoverySchedule, int(row.id))
    after = _row_snapshot(row_f) if row_f else {}
    logs = buf.getvalue()
    found = _find_logs(
        logs,
        [
            "RECOVERY STALE CHECK",
            "RECOVERY STALE DETECTED",
            "RECOVERY STALE FINALIZED",
            "RECOVERY STALE REPAIRED",
        ],
    )
    pass_ok = (
        before["status"] == STATUS_RUNNING
        and after.get("status") == STATUS_COMPLETED
        and repair.get("finalized", 0) >= 1
    )
    return {
        "scenario": 4,
        "name": "Stale running recovery",
        "db_before": before,
        "db_after": after,
        "repair_stats": repair,
        "logs_found": found,
        "log_excerpt": logs[-3000:],
        "pass": pass_ok,
    }


def scenario_5_whatsapp_duplicate() -> Dict[str, Any]:
    _clear_tables()
    buf = io.StringIO()
    rk = f"demo:gate-wa-{uuid.uuid4().hex[:6]}"
    sid = rk.split(":", 1)[1]
    with redirect_stdout(buf):
        dup1, _, _ = check_whatsapp_recovery_send_idempotency(
            recovery_key=rk,
            step=1,
            store_slug="demo",
            session_id=sid,
            cart_id="cart-wa",
            customer_phone="+966501112233",
        )
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id="cart-wa",
                phone="+966501112233",
                message="hi",
                status="mock_sent",
                step=1,
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()
        dup2, st2, _ = check_whatsapp_recovery_send_idempotency(
            recovery_key=rk,
            step=1,
            store_slug="demo",
            session_id=sid,
            cart_id="cart-wa",
            customer_phone="+966501112233",
        )
    logs = buf.getvalue()
    pass_ok = (
        dup1 is False
        and dup2 is True
        and st2 == "mock_sent"
        and "WA IDEMPOTENCY MISS" in logs
        and "WA IDEMPOTENCY HIT" in logs
    )
    return {
        "scenario": 5,
        "name": "WhatsApp duplicate prevention",
        "idempotency_first": dup1,
        "idempotency_second": dup2,
        "idempotency_second_status": st2,
        "schedule_integration": (
            "Full send-path skipped_duplicate verified in "
            "tests/test_recovery_whatsapp_idempotency.py (mocked execute omits WA gate)"
        ),
        "logs_found": _find_logs(logs, ["WA IDEMPOTENCY CHECK", "WA IDEMPOTENCY MISS", "WA IDEMPOTENCY HIT"]),
        "log_excerpt": logs[-2500:],
        "pass": pass_ok,
    }


def scenario_6_schedule_lifecycle() -> Dict[str, Any]:
    _clear_tables()
    buf = io.StringIO()
    row = _persist_demo_row("s6-life")
    with redirect_stdout(buf):
        c1, _, _ = claim_recovery_schedule_execution(
            recovery_key=row.recovery_key, path="life1"
        )
        finalize_recovery_schedule_durable(
            row.recovery_key, status=STATUS_COMPLETED
        )
        ok_overwrite = finalize_recovery_schedule_durable(
            row.recovery_key,
            status=STATUS_SKIPPED_DUPLICATE,
            detail="should_not_apply",
        )
        c2, reason2, _ = claim_recovery_schedule_execution(
            recovery_key=row.recovery_key, path="life2"
        )
    db.session.expire_all()
    row_f = db.session.get(RecoverySchedule, int(row.id))
    logs = buf.getvalue()
    pass_ok = (
        c1 is True
        and row_f is not None
        and row_f.status == STATUS_COMPLETED
        and ok_overwrite is False
        and c2 is False
        and "already_terminal" in reason2
    )
    return {
        "scenario": 6,
        "name": "Schedule lifecycle verification",
        "db_after": _row_snapshot(row_f) if row_f else {},
        "claim_after_complete_reason": reason2,
        "overwrite_blocked": ok_overwrite is False,
        "logs_found": _find_logs(
            logs, ["RECOVERY TERMINAL UPDATE", "RECOVERY CLAIM SKIPPED"]
        ),
        "log_excerpt": logs[-2500:],
        "pass": pass_ok,
    }


def scenario_7_multi_trigger() -> Dict[str, Any]:
    _clear_tables()
    buf = io.StringIO()
    rk = f"demo:gate-mt-{uuid.uuid4().hex[:6]}"
    row1 = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id="sess-mt",
        cart_id="cart-mt",
        reason_tag="other",
        abandon_event_phone="+966501112233",
        delay_seconds_scheduled=60.0,
        schedule_timing={"effective_delay_seconds": 60.0, "source": "reason_templates.messages"},
        recovery_context={"recovery_key": rk},
    )
    assert row1 is not None
    row2 = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id="sess-mt",
        cart_id="cart-mt",
        reason_tag="other",
        abandon_event_phone="+966501112233",
        delay_seconds_scheduled=60.0,
        schedule_timing={"effective_delay_seconds": 60.0, "source": "reason_templates.messages"},
        recovery_context={"recovery_key": rk},
    )
    count = db.session.query(RecoverySchedule).filter(
        RecoverySchedule.recovery_key == rk
    ).count()
    with redirect_stdout(buf):
        c1, _, _ = claim_recovery_schedule_execution(recovery_key=rk, path="mt1")
        c2, reason2, _ = claim_recovery_schedule_execution(recovery_key=rk, path="mt2")
    logs = buf.getvalue()
    pass_ok = count == 1 and c1 is True and c2 is False
    return {
        "scenario": 7,
        "name": "Multi-trigger same session",
        "schedule_row_count": count,
        "claim_second_reason": reason2,
        "db_row": _row_snapshot(row2) if row2 else {},
        "logs_found": _find_logs(logs, ["RECOVERY CLAIM ATTEMPT", "RECOVERY CLAIM SKIPPED"]),
        "log_excerpt": logs[-2000:],
        "pass": pass_ok,
        "notes": "Upsert keeps one durable row; second claim sees already_running",
    }


def main() -> int:
    import sys

    os.environ.setdefault("CARTFLOW_RECOVERY_RESUME_ON_STARTUP", "0")
    # Keep gate runner logs off stdout so JSON is parseable.
    _real_stdout = sys.stdout
    sys.stdout = sys.stderr
    results = [
        scenario_1_restart_during_delay(),
        scenario_2_duplicate_dispatch(),
        scenario_3_resume_after_restart(),
        scenario_4_stale_running(),
        scenario_5_whatsapp_duplicate(),
        scenario_6_schedule_lifecycle(),
        scenario_7_multi_trigger(),
    ]
    all_pass = all(r["pass"] for r in results)
    payload = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "all_pass": all_pass,
        "scenarios": results,
    }
    out_path = os.path.join(_ROOT, "scripts", "_gate_results.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    sys.stdout = _real_stdout
    print(json.dumps(payload, indent=2, default=str))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
