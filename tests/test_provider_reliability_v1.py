# -*- coding: utf-8 -*-
"""
Provider Reliability Implementation V1 — tests.

Covers Provider Reliability Governance contracts:
  * §3 deterministic failure disposition (PR-7, PR-9)
  * §2 reconciled truth, no cross-altitude inference (PR-1, PR-2, PR-5)
  * §4 durable retry ledger: budget, exhaustion, Retry-After, idempotency, claim (PR-4, PR-RT-*)
  * §7 denominator-based metrics (PR-10)
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from extensions import db
from models import CartRecoveryLog, ProviderRetryLedger, WhatsAppDeliveryTruth

from services.provider_reliability_truth_v1 import (
    ALT_ACCEPTANCE,
    ALT_CUSTOMER_DELIVERY,
    ALT_TERMINAL,
    DISPOSITION_NON_PROVIDER,
    DISPOSITION_RETRY,
    DISPOSITION_SUPPRESSED,
    DISPOSITION_TERMINAL,
    DISPOSITION_UNKNOWN,
    reconcile_provider_truth,
    resolve_failure_disposition,
)
from services.provider_retry_ledger_v1 import (
    STATUS_CANCELLED,
    STATUS_EXHAUSTED,
    STATUS_PENDING,
    STATUS_SUCCEEDED,
    cancel_retry,
    claim_due_retries,
    parse_retry_after,
    record_send_outcome,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clean() -> None:
    db.create_all()
    for model in (ProviderRetryLedger, WhatsAppDeliveryTruth, CartRecoveryLog):
        try:
            db.session.query(model).delete()
        except Exception:
            db.session.rollback()
    db.session.commit()


class FailureDispositionTests(unittest.TestCase):
    """§3 — every provider outcome maps deterministically to one axis."""

    def test_retryable_classes(self) -> None:
        self.assertEqual(resolve_failure_disposition(error="provider_timeout"), DISPOSITION_RETRY)
        self.assertEqual(
            resolve_failure_disposition(failure_class="provider_rate_limited"),
            DISPOSITION_RETRY,
        )
        self.assertEqual(
            resolve_failure_disposition(failure_class="provider_unavailable"),
            DISPOSITION_RETRY,
        )

    def test_terminal_classes(self) -> None:
        for fc in (
            "provider_rejected_message",
            "template_not_approved",
            "sandbox_recipient_not_joined",
            "provider_auth_failed",
            "provider_not_configured",
        ):
            self.assertEqual(
                resolve_failure_disposition(failure_class=fc),
                DISPOSITION_TERMINAL,
                fc,
            )

    def test_non_provider_and_suppressed(self) -> None:
        self.assertEqual(resolve_failure_disposition(error="empty_message"), DISPOSITION_NON_PROVIDER)
        self.assertEqual(resolve_failure_disposition(error="invalid_phone"), DISPOSITION_NON_PROVIDER)
        self.assertEqual(resolve_failure_disposition(marker="converted"), DISPOSITION_NON_PROVIDER)
        self.assertEqual(resolve_failure_disposition(marker="duplicate"), DISPOSITION_SUPPRESSED)

    def test_unknown_is_observable_not_silent(self) -> None:
        self.assertEqual(resolve_failure_disposition(), DISPOSITION_UNKNOWN)
        self.assertEqual(
            resolve_failure_disposition(failure_class="unknown_provider_failure"),
            DISPOSITION_UNKNOWN,
        )


class ProviderTruthReconciliationTests(unittest.TestCase):
    """§2 — acceptance never implies delivery; delivery only from delivery evidence."""

    def setUp(self) -> None:
        _clean()

    def _add_log(self, key: str, status: str) -> None:
        db.session.add(
            CartRecoveryLog(
                store_slug="s1",
                session_id="sess",
                cart_id="c1",
                phone="+966500000000",
                message="m",
                status=status,
                step=1,
                recovery_key=key,
                created_at=_utcnow(),
            )
        )
        db.session.commit()

    def _add_delivery(self, key: str, level: str, sid: str) -> None:
        db.session.add(
            WhatsAppDeliveryTruth(
                provider="twilio",
                message_sid=sid,
                recovery_key=key,
                truth_level=level,
                last_event_time=_utcnow(),
            )
        )
        db.session.commit()

    def test_acceptance_is_not_delivery(self) -> None:
        self._add_log("s1:acc", "sent_real")
        truth = reconcile_provider_truth("s1:acc")
        self.assertTrue(truth.accepted)
        self.assertFalse(truth.delivered)
        self.assertEqual(truth.altitude, ALT_ACCEPTANCE)
        self.assertEqual(truth.terminal_outcome, "")

    def test_delivery_only_from_delivery_evidence(self) -> None:
        self._add_log("s1:del", "sent_real")
        self._add_delivery("s1:del", "delivered_to_customer", "SID_DEL")
        truth = reconcile_provider_truth("s1:del")
        self.assertTrue(truth.delivered)
        self.assertEqual(truth.altitude, ALT_CUSTOMER_DELIVERY)
        self.assertEqual(truth.terminal_outcome, "delivered")

    def test_terminal_failure_from_either_store(self) -> None:
        self._add_log("s1:fail", "whatsapp_failed")
        truth = reconcile_provider_truth("s1:fail")
        self.assertTrue(truth.failed)
        self.assertEqual(truth.altitude, ALT_TERMINAL)
        self.assertEqual(truth.terminal_outcome, "failed")

    def test_delivery_failed_overrides_acceptance(self) -> None:
        self._add_log("s1:df", "sent_real")
        self._add_delivery("s1:df", "failed_delivery", "SID_DF")
        truth = reconcile_provider_truth("s1:df")
        self.assertTrue(truth.failed)
        self.assertEqual(truth.terminal_outcome, "failed")

    def test_missing_key(self) -> None:
        truth = reconcile_provider_truth("")
        self.assertEqual(truth.reason, "missing_correlation_key")


class RetryLedgerTests(unittest.TestCase):
    """§4 — durable, budget-aware, Retry-After compliant, idempotent, restart-safe."""

    def setUp(self) -> None:
        _clean()

    def test_retry_after_parsing(self) -> None:
        self.assertEqual(parse_retry_after("120"), 120.0)
        self.assertIsNone(parse_retry_after(""))
        self.assertIsNone(parse_retry_after(None))

    def test_retry_schedules_and_exhausts_within_budget(self) -> None:
        # budget 2: first failure -> pending(attempt 1); second -> exhausted(attempt 2)
        r1 = record_send_outcome(
            correlation_key="s1:r", disposition=DISPOSITION_RETRY,
            failure_class="provider_unavailable", max_attempts=2,
        )
        self.assertEqual(r1["status"], STATUS_PENDING)
        self.assertEqual(r1["attempt"], 1)
        self.assertIsNotNone(r1["next_attempt_at"])

        r2 = record_send_outcome(
            correlation_key="s1:r", disposition=DISPOSITION_RETRY,
            failure_class="provider_unavailable", max_attempts=2,
        )
        self.assertEqual(r2["status"], STATUS_EXHAUSTED)
        self.assertEqual(r2["attempt"], 2)
        self.assertIsNone(r2["next_attempt_at"])
        # exhaustion is durable + observable
        rows = db.session.query(ProviderRetryLedger).filter_by(correlation_key="s1:r").all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, STATUS_EXHAUSTED)

    def test_retry_after_is_honored(self) -> None:
        now = _utcnow()
        record_send_outcome(
            correlation_key="s1:ra", disposition=DISPOSITION_RETRY,
            failure_class="provider_rate_limited", retry_after="120",
            max_attempts=5, now=now,
        )
        row = db.session.query(ProviderRetryLedger).filter_by(correlation_key="s1:ra").first()
        self.assertIsNotNone(row.retry_after_until)
        # next attempt must be no earlier than Retry-After floor
        delta = (row.next_attempt_at.replace(tzinfo=timezone.utc) - now).total_seconds()
        self.assertGreaterEqual(delta, 119.0)

    def test_success_is_idempotent(self) -> None:
        record_send_outcome(correlation_key="s1:ok", disposition=DISPOSITION_RETRY, succeeded=True)
        record_send_outcome(correlation_key="s1:ok", disposition=DISPOSITION_RETRY, succeeded=True)
        rows = db.session.query(ProviderRetryLedger).filter_by(correlation_key="s1:ok").all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, STATUS_SUCCEEDED)

    def test_claim_is_restart_safe_single_dispatch(self) -> None:
        past = _utcnow() - timedelta(hours=1)
        record_send_outcome(
            correlation_key="s1:claim", disposition=DISPOSITION_RETRY,
            failure_class="provider_unavailable", max_attempts=5, now=past,
        )
        # row persists in DB (survives a simulated restart = fresh query)
        row = db.session.query(ProviderRetryLedger).filter_by(correlation_key="s1:claim").first()
        self.assertEqual(row.status, STATUS_PENDING)

        first = claim_due_retries(now=_utcnow())
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["correlation_key"], "s1:claim")
        # second claim must not double-dispatch the same due retry
        second = claim_due_retries(now=_utcnow())
        self.assertEqual(len(second), 0)

    def test_cancel_retry(self) -> None:
        record_send_outcome(
            correlation_key="s1:cx", disposition=DISPOSITION_RETRY,
            failure_class="provider_unavailable", max_attempts=5,
        )
        n = cancel_retry(correlation_key="s1:cx", reason="converted")
        self.assertEqual(n, 1)
        row = db.session.query(ProviderRetryLedger).filter_by(correlation_key="s1:cx").first()
        self.assertEqual(row.status, STATUS_CANCELLED)

    def test_terminal_disposition_never_schedules_retry(self) -> None:
        r = record_send_outcome(
            correlation_key="s1:term", disposition=DISPOSITION_TERMINAL,
            failure_class="provider_rejected_message",
        )
        self.assertIsNone(r["next_attempt_at"])


class ReliabilityMetricsTests(unittest.TestCase):
    """§7 — denominator-based rates; None when denominator is 0."""

    def setUp(self) -> None:
        _clean()

    def _add_log(self, status: str, key: str) -> None:
        db.session.add(
            CartRecoveryLog(
                store_slug="s1", session_id="sess", cart_id="c",
                phone="+966500000000", message="m", status=status, step=1,
                recovery_key=key, created_at=_utcnow(),
            )
        )
        db.session.commit()

    def test_rates_none_when_no_data(self) -> None:
        from services.provider_reliability_metrics_v1 import build_provider_reliability_report

        rep = build_provider_reliability_report()
        self.assertIsNone(rep["metrics"]["acceptance_rate"])
        self.assertEqual(rep["denominators"]["attempted"], 0)

    def test_acceptance_rate_has_denominator(self) -> None:
        from services.provider_reliability_metrics_v1 import build_provider_reliability_report

        self._add_log("sent_real", "s1:a1")
        self._add_log("sent_real", "s1:a2")
        self._add_log("sent_real", "s1:a3")
        self._add_log("whatsapp_failed", "s1:f1")
        rep = build_provider_reliability_report()
        self.assertEqual(rep["denominators"]["attempted"], 4)
        self.assertEqual(rep["denominators"]["accepted"], 3)
        self.assertEqual(rep["metrics"]["acceptance_rate"], 75.0)

    def test_report_shape(self) -> None:
        from services.provider_reliability_metrics_v1 import build_provider_reliability_report

        rep = build_provider_reliability_report()
        for key in ("status", "provider_health", "metrics", "denominators", "retry_queue"):
            self.assertIn(key, rep)
        for m in (
            "acceptance_rate", "delivery_rate", "retry_rate", "retry_success_rate",
            "retry_exhaustion_rate", "unknown_state_rate", "provider_availability",
            "provider_latency",
        ):
            self.assertIn(m, rep["metrics"])


if __name__ == "__main__":
    unittest.main()
