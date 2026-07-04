# -*- coding: utf-8 -*-
"""
Provider Reliability Implementation V1 — verification harness.

Demonstrates the Provider Reliability Governance contracts end-to-end against a
throwaway SQLite DB:
  * deterministic failure disposition (no silent failure) — §3 / PR-7, PR-9
  * reconciled truth, acceptance != delivery, correlation integrity — §2 / PR-1, PR-2, PR-14
  * delivery-truth integrity via webhook advancement — §2
  * durable retry: persistence, restart safety, Retry-After, budget exhaustion,
    idempotency, single-dispatch claim, cancellation — §4 / PR-4, PR-RT-*
  * denominator-based metrics, live dispatch OFF (no behavior change) — §7 / PR-10
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_db_path = os.path.join(tempfile.gettempdir(), "cartflow_provider_reliability_verify.db")
if os.path.exists(_db_path):
    os.remove(_db_path)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.replace("\\", "/")
os.environ.pop("PROVIDER_RETRY_ACTIVE", None)

import models  # noqa: E402,F401
from extensions import db, init_database  # noqa: E402

init_database()
db.create_all()

from models import CartRecoveryLog, ProviderRetryLedger  # noqa: E402
from services.provider_reliability_truth_v1 import (  # noqa: E402
    DISPOSITION_NON_PROVIDER,
    DISPOSITION_RETRY,
    DISPOSITION_SUPPRESSED,
    DISPOSITION_TERMINAL,
    DISPOSITION_UNKNOWN,
    reconcile_provider_truth,
    resolve_failure_disposition,
)
from services.provider_retry_ledger_v1 import (  # noqa: E402
    STATUS_EXHAUSTED,
    STATUS_PENDING,
    cancel_retry,
    claim_due_retries,
    record_send_outcome,
    retry_active,
)
from services.whatsapp_delivery_truth_v1 import (  # noqa: E402
    ingest_twilio_status_callback,
    record_provider_acceptance_from_send,
)
from services.provider_reliability_metrics_v1 import (  # noqa: E402
    build_provider_reliability_report,
)


def _now():
    return datetime.now(timezone.utc)


def _p(label, ok, detail=""):
    print(f"  [{'OK' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    return ok


def main() -> None:
    print("=" * 72)
    print("PROVIDER RELIABILITY IMPLEMENTATION V1 — VERIFICATION")
    print("=" * 72)
    results = []

    # ---- §3 deterministic disposition (no silent failure) ----
    print("\n[§3] Failure disposition is deterministic — every outcome has an axis")
    taxonomy = {
        "provider_timeout(err)": (resolve_failure_disposition(error="provider_timeout"), DISPOSITION_RETRY),
        "rate_limited": (resolve_failure_disposition(failure_class="provider_rate_limited"), DISPOSITION_RETRY),
        "unavailable": (resolve_failure_disposition(failure_class="provider_unavailable"), DISPOSITION_RETRY),
        "rejected": (resolve_failure_disposition(failure_class="provider_rejected_message"), DISPOSITION_TERMINAL),
        "auth": (resolve_failure_disposition(failure_class="provider_auth_failed"), DISPOSITION_TERMINAL),
        "template": (resolve_failure_disposition(failure_class="template_not_approved"), DISPOSITION_TERMINAL),
        "empty_message": (resolve_failure_disposition(error="empty_message"), DISPOSITION_NON_PROVIDER),
        "duplicate": (resolve_failure_disposition(marker="duplicate"), DISPOSITION_SUPPRESSED),
        "unknown": (resolve_failure_disposition(), DISPOSITION_UNKNOWN),
    }
    for name, (got, exp) in taxonomy.items():
        results.append(_p(f"{name} -> {got}", got == exp, f"expected {exp}"))

    # ---- §2 truth reconciliation + correlation integrity ----
    print("\n[§2] Reconciled truth — acceptance != delivery; correlation via recovery_key")
    rk = "s1:corr"
    db.session.add(CartRecoveryLog(
        store_slug="s1", session_id="sess", cart_id="c1", phone="+966500000000",
        message="m", status="sent_real", step=1, recovery_key=rk, created_at=_now(),
    ))
    db.session.commit()
    # PR-14: acceptance persists correlation key on the delivery-truth row
    record_provider_acceptance_from_send(
        provider="twilio", message_sid="SID_CORR", send_status="queued",
        customer_phone="+966500000000", store_slug="s1", session_id="sess", recovery_key=rk,
    )
    t_acc = reconcile_provider_truth(rk)
    results.append(_p("accepted, NOT delivered (no inference)", t_acc.accepted and not t_acc.delivered, t_acc.reason))

    # webhook advances the SAME correlated row to delivered
    ingest_twilio_status_callback({"MessageSid": "SID_CORR", "MessageStatus": "delivered"})
    t_del = reconcile_provider_truth(rk)
    results.append(_p("delivery advances only via webhook evidence", t_del.delivered and t_del.terminal_outcome == "delivered", t_del.reason))

    # ---- §4 durable retry ----
    print("\n[§4] Durable retry — persistence, restart safety, Retry-After, budget, idempotency")
    now = _now()
    r1 = record_send_outcome(correlation_key="s1:retry", disposition=DISPOSITION_RETRY,
                             failure_class="provider_unavailable", max_attempts=3, now=now)
    results.append(_p("retryable failure -> pending + scheduled", r1["status"] == STATUS_PENDING and r1["next_attempt_at"], str(r1)))

    # restart safety: close session, re-open, row persists in the file DB
    db.session.close()
    persisted = db.session.query(ProviderRetryLedger).filter_by(correlation_key="s1:retry").first()
    results.append(_p("retry state survives session restart (durable)", persisted is not None and persisted.status == STATUS_PENDING))

    # Retry-After honored
    ra = record_send_outcome(correlation_key="s1:ra", disposition=DISPOSITION_RETRY,
                             failure_class="provider_rate_limited", retry_after="120", max_attempts=5, now=now)
    ra_row = db.session.query(ProviderRetryLedger).filter_by(correlation_key="s1:ra").first()
    ra_delta = (ra_row.next_attempt_at.replace(tzinfo=timezone.utc) - now).total_seconds()
    results.append(_p("Retry-After floor honored (>=120s)", ra_delta >= 119.0, f"delta={ra_delta:.0f}s"))

    # budget exhaustion is terminal + observable
    record_send_outcome(correlation_key="s1:ex", disposition=DISPOSITION_RETRY, failure_class="provider_unavailable", max_attempts=2)
    ex = record_send_outcome(correlation_key="s1:ex", disposition=DISPOSITION_RETRY, failure_class="provider_unavailable", max_attempts=2)
    results.append(_p("budget exhaustion -> terminal EXHAUSTED", ex["status"] == STATUS_EXHAUSTED))

    # idempotency: repeated success -> single row
    record_send_outcome(correlation_key="s1:ok", disposition=DISPOSITION_RETRY, succeeded=True)
    record_send_outcome(correlation_key="s1:ok", disposition=DISPOSITION_RETRY, succeeded=True)
    ok_rows = db.session.query(ProviderRetryLedger).filter_by(correlation_key="s1:ok").count()
    results.append(_p("idempotent success (no duplicate rows)", ok_rows == 1, f"rows={ok_rows}"))

    # single-dispatch claim (no duplicate sends across restart/workers)
    record_send_outcome(correlation_key="s1:claim", disposition=DISPOSITION_RETRY,
                        failure_class="provider_unavailable", max_attempts=5, now=_now() - timedelta(hours=1))
    first = claim_due_retries(now=_now())
    second = claim_due_retries(now=_now())
    results.append(_p("due retry claimed exactly once", len(first) == 1 and len(second) == 0, f"first={len(first)} second={len(second)}"))

    # cancellation (conversion / opt-out)
    n = cancel_retry(correlation_key="s1:retry", reason="converted")
    results.append(_p("retry cancellable (conversion/opt-out)", n == 1))

    # ---- no silent failure: every recorded failure has an observable status ----
    open_or_terminal = db.session.query(ProviderRetryLedger).count()
    silent = db.session.query(ProviderRetryLedger).filter(ProviderRetryLedger.status == "").count()
    results.append(_p("no silent failure (every ledger row has a status)", silent == 0, f"rows={open_or_terminal}"))

    # ---- §7 denominator-based metrics + live dispatch OFF ----
    print("\n[§7] Denominator-based metrics; live re-dispatch OFF (no behavior change)")
    rep = build_provider_reliability_report()
    m = rep["metrics"]
    d = rep["denominators"]
    print(f"  status={rep['status']} attempted={d['attempted']} accepted={d['accepted']} failed={d['failed']}")
    print(f"  acceptance_rate={m['acceptance_rate']} delivery_rate={m['delivery_rate']} "
          f"retry_rate={m['retry_rate']} retry_exhaustion_rate={m['retry_exhaustion_rate']} "
          f"unknown_state_rate={m['unknown_state_rate']}")
    print(f"  retry_queue={rep['retry_queue']}")
    results.append(_p("metrics are denominator-based (dict of rates + denominators)", "acceptance_rate" in m and "attempted" in d))
    results.append(_p("live retry dispatch is OFF by default (behavior-neutral)", retry_active() is False and rep["notes"]["retry_live_dispatch_active"] is False))

    print("\n" + "=" * 72)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"OVERALL: {'PASS' if passed == total else 'FAIL'}  ({passed}/{total} checks)")
    print("=" * 72)


if __name__ == "__main__":
    main()
