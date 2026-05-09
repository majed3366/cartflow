# -*- coding: utf-8 -*-
"""Operational observability runtime — diagnostics only (no recovery behavior changes)."""

from __future__ import annotations

import io
import unittest
import uuid
from contextlib import redirect_stdout

from extensions import db
from main import (
    _normal_recovery_phase_steps_payload,
    _persist_cart_recovery_log,
)
from models import AbandonedCart, CartRecoveryLog, Store
from services.cartflow_identity import IDENTITY_TRUST_FAILED_KEY
from services.cartflow_observability_runtime import (
    RecoveryLifecycleEvent,
    detect_recovery_runtime_conflicts,
    emit_structured_runtime_line,
    log_runtime_conflicts,
    PREFIX_DIAGNOSTIC,
    runtime_health_snapshot_readonly,
    trace_recovery_lifecycle,
    trace_recovery_lifecycle_from_log_status,
)
from services.recovery_blocker_display import get_recovery_blocker_display_state


class CartflowObservabilityHelpersTests(unittest.TestCase):
    def test_emit_structured_line_uses_prefix(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            emit_structured_runtime_line(
                PREFIX_DIAGNOSTIC, "state_transition", "test", code="x"
            )
        self.assertIn("[CARTFLOW DIAGNOSTIC]", buf.getvalue())
        self.assertIn("code=x", buf.getvalue())

    def test_trace_recovery_lifecycle_prefix(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            trace_recovery_lifecycle(
                RecoveryLifecycleEvent.SKIPPED_DUPLICATE,
                session_id="s1",
                cart_id="c1",
                store_slug="st",
            )
        self.assertIn("[CARTFLOW RECOVERY]", buf.getvalue())
        self.assertIn("skipped_duplicate", buf.getvalue())

    def test_log_status_maps_to_lifecycle(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            trace_recovery_lifecycle_from_log_status(
                status="skipped_duplicate",
                session_id="s",
                cart_id="c",
                store_slug="slug",
            )
        self.assertIn("skipped_duplicate", buf.getvalue())

    def test_detect_conflicts_identity_trust_with_send(self) -> None:
        c = detect_recovery_runtime_conflicts(
            abandoned_status="abandoned",
            behavioral={IDENTITY_TRUST_FAILED_KEY: True},
            latest_log_status="sent_real",
            identity_trust_failed=True,
            sent_ok_latest_log=True,
        )
        self.assertIn("identity_trust_failed_with_send_success_log", c)

    def test_detect_conflicts_anti_spam_drift(self) -> None:
        c = detect_recovery_runtime_conflicts(
            abandoned_status="abandoned",
            behavioral={},
            latest_log_status="skipped_anti_spam",
            identity_trust_failed=False,
            sent_ok_latest_log=False,
        )
        self.assertIn("anti_spam_skip_without_behavioral_return", c)

    def test_log_runtime_conflicts_emits_diagnostic(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            log_runtime_conflicts(
                ["identity_trust_failed_with_send_success_log"],
                session_id="s",
                cart_id="c",
            )
        self.assertIn("[CARTFLOW DIAGNOSTIC]", buf.getvalue())
        self.assertIn("runtime_conflict", buf.getvalue())

    def test_runtime_health_snapshot_keys(self) -> None:
        h = runtime_health_snapshot_readonly()
        for k in (
            "duplicate_prevention_active",
            "identity_resolution_ok",
            "whatsapp_provider_ready",
            "recovery_runtime_active",
            "dashboard_runtime_active",
        ):
            self.assertIn(k, h)
            self.assertIsInstance(h[k], bool)


class CartflowObservabilityIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:12]

    def tearDown(self) -> None:
        try:
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_persist_cart_log_emits_recovery_trace(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            _persist_cart_recovery_log(
                store_slug=f"slug_{self._suffix}",
                session_id=f"sid_{self._suffix}",
                cart_id=f"cid_{self._suffix}",
                phone=None,
                message="m",
                status="skipped_duplicate",
            )
        self.assertIn("[CARTFLOW RECOVERY]", buf.getvalue())

    def test_normal_recovery_payload_has_operational_hint(self) -> None:
        st = Store(
            zid_store_id=f"z_obs_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        sid = f"sid_obs_{self._suffix}"
        zid = f"zid_obs_{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=10.0,
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=sid,
                cart_id=zid,
                phone="+966500000000",
                message="x",
                status="whatsapp_failed",
                step=1,
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(
            payload.get("normal_recovery_operational_hint_ar"), "فشل إرسال واتساب"
        )

    def test_blocker_state_has_operational_hint_ar(self) -> None:
        d = get_recovery_blocker_display_state("duplicate_attempt_blocked")
        self.assertEqual(d.get("operational_hint_ar"), "تم منع محاولة مكررة")


if __name__ == "__main__":
    unittest.main()
