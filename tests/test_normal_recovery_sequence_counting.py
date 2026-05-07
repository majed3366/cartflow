# -*- coding: utf-8 -*-
"""Normal recovery sequence length from configured_message_count (store + multi-message templates)."""
from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import main
from extensions import db
from main import app
from tests.test_recovery_isolation import (
    _post_recovery_reason_for_session,
    _reset_recovery_memory,
)

_CUSTOMER_PHONE = "9665444555666"


def _abandon(store: str, session_id: str) -> dict:
    return {
        "event": "cart_abandoned",
        "store": store,
        "session_id": session_id,
        "cart": [{"name": "Item", "price": 10}],
    }


class NormalRecoverySequenceCountingTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)

    def _set_demo_recovery_attempts(self, n: int) -> tuple[int | None, str]:
        db.create_all()
        st = main._load_store_row_for_recovery("demo")
        self.assertIsNotNone(st)
        prev = getattr(st, "recovery_attempts", None)
        st.recovery_attempts = n
        db.session.commit()
        return prev, "ok"

    def _restore_demo_recovery_attempts(self, prev: int | None) -> None:
        st = main._load_store_row_for_recovery("demo")
        if st is not None:
            st.recovery_attempts = prev
            db.session.commit()

    @patch("main._second_attempt_delay_minutes_from_store", return_value=0)
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    def test_a_count_1_only_first_sends(
        self,
        _d: object,
        _ur: object,
        mock_send: object,
        _p: object,
        _sleep: object,
        _gap: object,
    ) -> None:
        mock_send.return_value = {"ok": True}
        prev, _ = self._set_demo_recovery_attempts(1)
        try:
            sid = "seq-ct-a"
            _post_recovery_reason_for_session(
                self.client, "demo", sid, customer_phone=_CUSTOMER_PHONE
            )
            r = self.client.post("/api/cart-event", json=_abandon("demo", sid))
            self.assertEqual(200, r.status_code, r.text)
            self.assertEqual(1, mock_send.call_count)
        finally:
            self._restore_demo_recovery_attempts(prev)

    @patch("main._second_attempt_delay_minutes_from_store", return_value=0)
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    def test_b_count_2_two_sends(
        self,
        _d: object,
        _ur: object,
        mock_send: object,
        _p: object,
        _sleep: object,
        _gap: object,
    ) -> None:
        mock_send.return_value = {"ok": True}
        prev, _ = self._set_demo_recovery_attempts(2)
        try:
            sid = "seq-ct-b"
            _post_recovery_reason_for_session(
                self.client, "demo", sid, customer_phone=_CUSTOMER_PHONE
            )
            r = self.client.post("/api/cart-event", json=_abandon("demo", sid))
            self.assertEqual(200, r.status_code, r.text)
            self.assertEqual(2, mock_send.call_count)
        finally:
            self._restore_demo_recovery_attempts(prev)

    @patch("main._second_attempt_delay_minutes_from_store", return_value=0)
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    def test_b_third_sequential_blocked_sequence_completed(
        self,
        _d: object,
        _ur: object,
        mock_send: object,
        _p: object,
        _sleep: object,
        _gap: object,
    ) -> None:
        mock_send.return_value = {"ok": True}
        prev, _ = self._set_demo_recovery_attempts(2)
        try:
            sid = "seq-ct-b3"
            k = f"demo:{sid}"
            _post_recovery_reason_for_session(
                self.client, "demo", sid, customer_phone=_CUSTOMER_PHONE
            )
            self.client.post("/api/cart-event", json=_abandon("demo", sid))
            self.assertEqual(2, mock_send.call_count)

            async def run_extra() -> None:
                await main._run_recovery_sequence_after_cart_abandoned(
                    k,
                    0.0,
                    "demo",
                    sid,
                    None,
                    _CUSTOMER_PHONE,
                    sequential_attempt_index=3,
                )

            asyncio.run(run_extra())
            self.assertEqual(
                2,
                mock_send.call_count,
                "configured_message_count=2 must block attempt_index=3",
            )
        finally:
            self._restore_demo_recovery_attempts(prev)

    @patch("main._second_attempt_delay_minutes_from_store", return_value=0)
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    def test_c_count_3_three_sends(
        self,
        _d: object,
        _ur: object,
        mock_send: object,
        _p: object,
        _sleep: object,
        _gap: object,
    ) -> None:
        mock_send.return_value = {"ok": True}
        prev, _ = self._set_demo_recovery_attempts(3)
        try:
            sid = "seq-ct-c"
            _post_recovery_reason_for_session(
                self.client, "demo", sid, customer_phone=_CUSTOMER_PHONE
            )
            r = self.client.post("/api/cart-event", json=_abandon("demo", sid))
            self.assertEqual(200, r.status_code, r.text)
            self.assertEqual(3, mock_send.call_count)
        finally:
            self._restore_demo_recovery_attempts(prev)

    @patch("main._second_attempt_delay_minutes_from_store", return_value=0)
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    def test_c_fourth_blocked(
        self,
        _d: object,
        _ur: object,
        mock_send: object,
        _p: object,
        _sleep: object,
        _gap: object,
    ) -> None:
        mock_send.return_value = {"ok": True}
        prev, _ = self._set_demo_recovery_attempts(3)
        try:
            sid = "seq-ct-c4"
            k = f"demo:{sid}"
            _post_recovery_reason_for_session(
                self.client, "demo", sid, customer_phone=_CUSTOMER_PHONE
            )
            self.client.post("/api/cart-event", json=_abandon("demo", sid))
            self.assertEqual(3, mock_send.call_count)

            async def run_extra() -> None:
                await main._run_recovery_sequence_after_cart_abandoned(
                    k,
                    0.0,
                    "demo",
                    sid,
                    None,
                    _CUSTOMER_PHONE,
                    sequential_attempt_index=4,
                )

            asyncio.run(run_extra())
            self.assertEqual(3, mock_send.call_count)
        finally:
            self._restore_demo_recovery_attempts(prev)

    @patch("main._second_attempt_delay_minutes_from_store", return_value=0)
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    def test_d_duplicate_attempt_index_no_second_send(
        self,
        _d: object,
        _ur: object,
        mock_send: object,
        _p: object,
        _sleep: object,
        _gap: object,
    ) -> None:
        mock_send.return_value = {"ok": True}
        prev, _ = self._set_demo_recovery_attempts(2)
        try:
            sid = "seq-ct-dup"
            k = f"demo:{sid}"
            _post_recovery_reason_for_session(
                self.client, "demo", sid, customer_phone=_CUSTOMER_PHONE
            )
            self.client.post("/api/cart-event", json=_abandon("demo", sid))
            self.assertEqual(2, mock_send.call_count)

            async def run_dup() -> None:
                await main._run_recovery_sequence_after_cart_abandoned(
                    k,
                    0.0,
                    "demo",
                    sid,
                    None,
                    _CUSTOMER_PHONE,
                    sequential_attempt_index=2,
                )

            asyncio.run(run_dup())
            self.assertEqual(2, mock_send.call_count)
        finally:
            self._restore_demo_recovery_attempts(prev)

    @patch("main._second_attempt_delay_minutes_from_store", return_value=0)
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    def test_e_purchase_completed_blocks_second(
        self,
        _d: object,
        _ur: object,
        mock_send: object,
        _p: object,
        _sleep: object,
        _gap: object,
    ) -> None:

        def after_first(*_a: object, **_kw: object) -> dict:
            main._mark_session_converted("demo", "seq-ct-e")
            return {"ok": True}

        mock_send.side_effect = after_first
        prev, _ = self._set_demo_recovery_attempts(2)
        try:
            sid = "seq-ct-e"
            _post_recovery_reason_for_session(
                self.client, "demo", sid, customer_phone=_CUSTOMER_PHONE
            )
            self.client.post("/api/cart-event", json=_abandon("demo", sid))
            self.assertEqual(1, mock_send.call_count)
        finally:
            self._restore_demo_recovery_attempts(prev)

    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    def test_multi_message_uses_template_count_not_store_attempts(
        self,
        mock_send: object,
        _p: object,
        _sleep: object,
        _d: object,
        _ur: object,
    ) -> None:
        """Store recovery_attempts=1 but template has 2 slots → two sends."""
        mock_send.return_value = {"ok": True, "sid": "SM"}
        db.create_all()
        st = main._load_store_row_for_recovery("demo")
        self.assertIsNotNone(st)
        prev_att = getattr(st, "recovery_attempts", None)
        prev_tpl = getattr(st, "reason_templates_json", None)
        st.recovery_attempts = 1
        st.reason_templates_json = json.dumps(
            {
                "price": {
                    "enabled": True,
                    "message": "أساسية",
                    "message_count": 2,
                    "messages": [
                        {"delay": 1, "unit": "minute", "text": "أولى"},
                        {"delay": 1, "unit": "minute", "text": "ثانية"},
                    ],
                }
            }
        )
        db.session.commit()
        try:
            sid = "seq-multi-cap"
            _post_recovery_reason_for_session(
                self.client, "demo", sid, reason_tag="price", customer_phone=_CUSTOMER_PHONE
            )
            r = self.client.post("/api/cart-event", json=_abandon("demo", sid))
            self.assertEqual(200, r.status_code, r.text)
            self.assertEqual(2, mock_send.call_count, mock_send.call_args_list)
        finally:
            st2 = main._load_store_row_for_recovery("demo")
            if st2 is not None:
                st2.recovery_attempts = prev_att
                st2.reason_templates_json = prev_tpl
                db.session.commit()


if __name__ == "__main__":
    unittest.main()
