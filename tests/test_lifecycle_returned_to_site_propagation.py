# -*- coding: utf-8 -*-
"""
Verification: returned_to_site → lifecycle decision layer (v1).

Findings encoded as tests:
- Lifecycle reads ``returned=`` from ``_recovery_resolve_user_returned_for_send`` only
  (same gate as anti-spam), not merchant lifecycle precedence directly.
- Demo ``behavior=unknown`` / ``decision=FALLBACK`` means resolve returned False at
  observation time — not a wrong decision mapping when ``returned=True``.
- Common demo gaps: return qualification cooldown (45s), passive page visit without
  delay_waiting, memory-only commercial add before deferred DB, recovery_key mismatch.
"""
from __future__ import annotations

import asyncio
import io
import unittest
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import main
from extensions import db
from models import CartRecoveryLog, Store
from services.cartflow_merchant_lifecycle_precedence import lifecycle_returned_evidence
from services.lifecycle_intelligence import (
    BEHAVIOR_RETURNED_TO_SITE,
    BEHAVIOR_UNKNOWN,
    DECISION_FALLBACK,
    DECISION_STOP,
)
from tests.test_recovery_isolation import (
    _post_recovery_reason_for_session,
    _reset_recovery_memory,
)

_CUSTOMER_PHONE = "9665444777888"


def _lifecycle_probe_at_anti_spam_gate(
    *,
    recovery_key: str,
    store_slug: str,
    session_id: str,
    cart_id: str | None,
    reason_tag: str | None = "price",
    step_num: int = 1,
) -> tuple[bool, dict]:
    """Mirror production wiring: resolve return, then observe lifecycle."""
    returned = main._recovery_resolve_user_returned_for_send(
        recovery_key,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        log_recovery_check=False,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = main._observe_lifecycle_intelligence_decision(
            returned=bool(returned),
            purchased=bool(main._is_user_converted(recovery_key)),
            replied=False,
            reason_tag=reason_tag,
            attempt_count=int(step_num),
            session_id=session_id,
            recovery_key=recovery_key,
        )
    return returned, {"result": result, "stdout": buf.getvalue()}


class LifecycleReturnedPropagationContractTests(unittest.TestCase):
    def test_when_resolve_true_lifecycle_is_stop_no_send(self) -> None:
        _reset_recovery_memory()
        slug = "demo"
        sid = f"li-prop-ok-{uuid.uuid4().hex[:8]}"
        cid = f"cart-{sid}"
        key = main._recovery_key_from_payload(
            {"store": slug, "session_id": sid, "cart_id": cid}
        )
        main._mark_user_returned_in_memory_only(
            {"store": slug, "session_id": sid, "cart_id": cid}
        )
        returned, pack = _lifecycle_probe_at_anti_spam_gate(
            recovery_key=key,
            store_slug=slug,
            session_id=sid,
            cart_id=cid,
        )
        out = pack["stdout"]
        self.assertTrue(returned)
        self.assertEqual(pack["result"]["behavior"], BEHAVIOR_RETURNED_TO_SITE)
        self.assertEqual(pack["result"]["decision"], DECISION_STOP)
        self.assertEqual(pack["result"]["action"], "no_send")
        self.assertIn("behavior=returned_to_site", out)
        self.assertIn("decision=STOP", out)
        self.assertIn("action=no_send", out)

    def test_when_resolve_false_lifecycle_falls_back_unknown(self) -> None:
        _reset_recovery_memory()
        slug = "demo"
        sid = f"li-prop-fb-{uuid.uuid4().hex[:8]}"
        cid = f"cart-{sid}"
        key = main._recovery_key_from_payload(
            {"store": slug, "session_id": sid, "cart_id": cid}
        )
        returned, pack = _lifecycle_probe_at_anti_spam_gate(
            recovery_key=key,
            store_slug=slug,
            session_id=sid,
            cart_id=cid,
            reason_tag="shipping",
        )
        self.assertFalse(returned)
        self.assertEqual(pack["result"]["behavior"], BEHAVIOR_UNKNOWN)
        self.assertEqual(pack["result"]["decision"], DECISION_FALLBACK)
        self.assertIn("behavior=unknown", pack["stdout"])

    def test_durable_returned_to_site_log_resolves_stop_without_memory(self) -> None:
        _reset_recovery_memory()
        suffix = uuid.uuid4().hex[:8]
        slug = f"li-store-{suffix}"
        sid = f"li-sid-{suffix}"
        cid = f"li-cid-{suffix}"
        st = Store(zid_store_id=slug, recovery_delay=1, recovery_delay_unit="minutes")
        db.session.add(st)
        db.session.flush()
        t0 = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=cid,
                phone=None,
                message="return_to_site_detected",
                status="returned_to_site",
                step=None,
                created_at=t0,
                sent_at=None,
            )
        )
        db.session.commit()
        key = main._recovery_key_from_payload(
            {"store": slug, "session_id": sid, "cart_id": cid}
        )
        returned, pack = _lifecycle_probe_at_anti_spam_gate(
            recovery_key=key,
            store_slug=slug,
            session_id=sid,
            cart_id=cid,
        )
        self.assertTrue(returned, msg="durable log must feed resolve → lifecycle")
        self.assertEqual(pack["result"]["decision"], DECISION_STOP)

    def test_merchant_precedence_can_see_return_while_resolve_false_without_log(self) -> None:
        """Dashboard/lifecycle narrative can differ when only log_ss has return — probe uses resolve."""
        log_ss = frozenset({"queued"})
        bh: dict = {}
        self.assertTrue(
            lifecycle_returned_evidence(
                bh=bh,
                ls="queued",
                bk="",
                pk="pending_send",
                cr="pending",
                log_ss=frozenset({"returned_to_site", "queued"}),
                dashboard_return_track=False,
                dashboard_return_intel_panel=False,
            )
        )
        _reset_recovery_memory()
        slug = "demo"
        sid = "li-precedence-gap"
        cid = "li-cart-gap"
        key = main._recovery_key_from_payload(
            {"store": slug, "session_id": sid, "cart_id": cid}
        )
        returned, pack = _lifecycle_probe_at_anti_spam_gate(
            recovery_key=key,
            store_slug=slug,
            session_id=sid,
            cart_id=cid,
        )
        self.assertFalse(returned)
        self.assertEqual(pack["result"]["decision"], DECISION_FALLBACK)


class LifecycleReturnedDemoGapTests(unittest.TestCase):
    """Reproduce demo-style paths that leave resolve=False → lifecycle FALLBACK."""

    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(main.app)

    def test_passive_page_visit_without_delay_waiting_does_not_arm_return(self) -> None:
        sid = f"li-passive-{uuid.uuid4().hex[:8]}"
        cid = f"cart-{sid}"
        _post_recovery_reason_for_session(self.client, "demo", sid)
        key = main._recovery_key_from_payload(
            {"store": "demo", "session_id": sid, "cart_id": cid}
        )
        passive = {
            "return_visit_kind": "passive_return_visit",
            "passive_return_visit": True,
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "recovery_return_context": "page",
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=passive).status_code)
        self.assertFalse(main._is_user_returned(key))
        returned, pack = _lifecycle_probe_at_anti_spam_gate(
            recovery_key=key,
            store_slug="demo",
            session_id=sid,
            cart_id=cid,
        )
        self.assertFalse(returned)
        self.assertEqual(pack["result"]["decision"], DECISION_FALLBACK)

    def test_return_within_qualification_cooldown_skips_mark_and_lifecycle_fallback(
        self,
    ) -> None:
        sid = f"li-cooldown-{uuid.uuid4().hex[:8]}"
        cid = f"cart-{sid}"
        key = main._recovery_key_from_payload(
            {"store": "demo", "session_id": sid, "cart_id": cid}
        )
        main._test_set_recovery_flow_armed_at(key, datetime.now(timezone.utc))
        active = {
            "event_type": "user_returned_to_site",
            "user_returned_to_site": True,
            "active_commercial_reengagement": True,
            "return_visit_kind": "active_commercial_reengagement",
            "returned_checkout_page": True,
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "recovery_return_context": "checkout",
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=active).status_code)
        self.assertFalse(
            main._is_user_returned(key),
            msg="cooldown must block _mark_user_returned → lifecycle sees unknown",
        )
        returned, pack = _lifecycle_probe_at_anti_spam_gate(
            recovery_key=key,
            store_slug="demo",
            session_id=sid,
            cart_id=cid,
        )
        self.assertFalse(returned)
        self.assertEqual(pack["result"]["decision"], DECISION_FALLBACK)

    def test_commercial_cart_sync_add_after_cooldown_propagates_stop(self) -> None:
        sid = f"li-sync-{uuid.uuid4().hex[:8]}"
        cid = f"cart-{sid}"
        _post_recovery_reason_for_session(self.client, "demo", sid)
        abandon = {
            "event": "cart_abandoned",
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "cart": [{"name": "T", "price": 10.0}],
            "phone": _CUSTOMER_PHONE,
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=abandon).status_code)
        key = main._recovery_key_from_payload(
            {"store": "demo", "session_id": sid, "cart_id": cid}
        )
        main._test_set_recovery_flow_armed_at(
            key, datetime.now(timezone.utc) - timedelta(seconds=120)
        )
        sync = {
            "event": "cart_state_sync",
            "reason": "add",
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "cart_total": 25.0,
            "items_count": 1,
            "cart": [{"name": "T", "price": 25.0, "quantity": 1}],
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=sync).status_code)
        self.assertTrue(main._is_user_returned(key))
        returned, pack = _lifecycle_probe_at_anti_spam_gate(
            recovery_key=key,
            store_slug="demo",
            session_id=sid,
            cart_id=cid,
        )
        self.assertTrue(returned)
        self.assertEqual(pack["result"]["decision"], DECISION_STOP)
        self.assertIn("action=no_send", pack["stdout"])


class LifecycleReturnedRecoverySequenceTests(unittest.TestCase):
    """Post-delay recovery sequence: return evidence must log STOP and block send."""

    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(main.app)

    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    @patch("main.should_send_whatsapp", return_value=True)
    def test_post_delay_send_with_return_marked_logs_stop_and_no_whatsapp(
        self,
        _ss: object,
        _gd: object,
        _ur: object,
        mock_send: object,
        _pcl: object,
        _sleep: object,
    ) -> None:
        mock_send.return_value = {"ok": True}
        sid = f"li-seq-{uuid.uuid4().hex[:8]}"
        cid = f"cart-{sid}"
        slug = "demo"
        _post_recovery_reason_for_session(
            self.client, slug, sid, customer_phone=_CUSTOMER_PHONE
        )
        key = main._recovery_key_from_payload(
            {"store": slug, "session_id": sid, "cart_id": cid}
        )
        main._test_set_recovery_flow_armed_at(
            key, datetime.now(timezone.utc) - timedelta(seconds=120)
        )
        main._mark_user_returned_for_payload(
            {"store": slug, "session_id": sid, "cart_id": cid}
        )

        buf = io.StringIO()

        async def _run() -> None:
            with redirect_stdout(buf):
                await main._run_recovery_sequence_after_cart_abandoned_impl(
                    key,
                    0.0,
                    slug,
                    sid,
                    cid,
                    _CUSTOMER_PHONE,
                    recovery_context={
                        "recovery_post_delay_only": True,
                        "reason_tag": "price",
                    },
                )

        asyncio.run(_run())
        out = buf.getvalue()
        self.assertIn("[LIFECYCLE DECISION]", out)
        self.assertIn("behavior=returned_to_site", out)
        self.assertIn("decision=STOP", out)
        self.assertIn("action=no_send", out)
        self.assertRegex(out, r"should_send=\s*False")
        mock_send.assert_not_called()

    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    @patch("main.should_send_whatsapp", return_value=True)
    def test_post_delay_without_return_mark_logs_fallback_and_sends(
        self,
        _ss: object,
        _gd: object,
        _ur: object,
        mock_send: object,
        _pcl: object,
        _sleep: object,
    ) -> None:
        mock_send.return_value = {"ok": True}
        sid = f"li-seq-send-{uuid.uuid4().hex[:8]}"
        slug = "demo"
        _post_recovery_reason_for_session(
            self.client, slug, sid, customer_phone=_CUSTOMER_PHONE
        )
        key = main._recovery_key_from_payload({"store": slug, "session_id": sid})

        buf = io.StringIO()

        async def _run() -> None:
            with redirect_stdout(buf):
                await main._run_recovery_sequence_after_cart_abandoned_impl(
                    key,
                    0.0,
                    slug,
                    sid,
                    None,
                    _CUSTOMER_PHONE,
                    recovery_context={
                        "recovery_post_delay_only": True,
                        "reason_tag": "price",
                    },
                )

        asyncio.run(_run())
        out = buf.getvalue()
        self.assertIn("behavior=unknown", out)
        self.assertIn("decision=FALLBACK", out)
        mock_send.assert_called()


if __name__ == "__main__":
    unittest.main()
