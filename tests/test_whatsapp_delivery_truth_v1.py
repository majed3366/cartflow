# -*- coding: utf-8 -*-
"""WhatsApp Delivery Truth v1 — acceptance ≠ delivery; webhook is observability only."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from services.whatsapp_delivery_truth_v1 import (
    TRUTH_ACCEPTED,
    TRUTH_DELIVERED,
    TRUTH_FAILED,
    TRUTH_UNKNOWN,
    get_delivery_truth,
    ingest_twilio_status_callback,
    normalize_twilio_message_status,
    persist_delivery_truth,
    record_provider_acceptance_from_send,
    resolve_truth_without_callback,
    DeliveryTruth,
)


class WhatsappDeliveryTruthNormalizeTests(unittest.TestCase):
    def test_queued_maps_to_accepted_by_provider(self) -> None:
        self.assertEqual(
            normalize_twilio_message_status("queued"), TRUTH_ACCEPTED
        )

    def test_delivered_maps_to_delivered_to_customer(self) -> None:
        self.assertEqual(
            normalize_twilio_message_status("delivered"), TRUTH_DELIVERED
        )

    def test_failed_maps_to_failed_delivery(self) -> None:
        self.assertEqual(
            normalize_twilio_message_status("failed"), TRUTH_FAILED
        )
        self.assertEqual(
            normalize_twilio_message_status("undelivered"), TRUTH_FAILED
        )


class WhatsappDeliveryTruthPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        from extensions import db
        from schema_widget import ensure_whatsapp_delivery_truth_schema

        ensure_whatsapp_delivery_truth_schema(db)
        db.create_all()

    def tearDown(self) -> None:
        try:
            from extensions import db
            from models import WhatsAppDeliveryTruth

            db.session.query(WhatsAppDeliveryTruth).delete()
            db.session.commit()
        except Exception:
            pass

    def test_record_send_acceptance(self) -> None:
        record_provider_acceptance_from_send(
            provider="twilio",
            message_sid="SM_test_accept_1",
            send_status="queued",
            customer_phone="+966500000001",
            store_slug="demo",
            session_id="sess-a",
        )
        truth = get_delivery_truth("SM_test_accept_1")
        self.assertIsNotNone(truth)
        assert truth is not None
        self.assertEqual(truth.truth_level, TRUTH_ACCEPTED)
        self.assertEqual(truth.send_status, "queued")

    def test_callback_delivered(self) -> None:
        record_provider_acceptance_from_send(
            provider="twilio",
            message_sid="SM_test_del_1",
            send_status="queued",
        )
        ingest_twilio_status_callback(
            {"MessageSid": "SM_test_del_1", "MessageStatus": "delivered"}
        )
        truth = get_delivery_truth("SM_test_del_1")
        self.assertIsNotNone(truth)
        assert truth is not None
        self.assertEqual(truth.truth_level, TRUTH_DELIVERED)

    def test_callback_failed(self) -> None:
        ingest_twilio_status_callback(
            {
                "MessageSid": "SM_test_fail_1",
                "MessageStatus": "failed",
                "ErrorCode": "63016",
            }
        )
        truth = get_delivery_truth("SM_test_fail_1")
        self.assertIsNotNone(truth)
        assert truth is not None
        self.assertEqual(truth.truth_level, TRUTH_FAILED)

    def test_missing_callback_unknown(self) -> None:
        resolved = resolve_truth_without_callback("SM_never_seen")
        self.assertEqual(resolved.truth_level, TRUTH_UNKNOWN)

    def test_missing_callback_after_send_accepted(self) -> None:
        record_provider_acceptance_from_send(
            provider="twilio",
            message_sid="SM_no_cb_1",
            send_status="queued",
        )
        resolved = resolve_truth_without_callback("SM_no_cb_1")
        self.assertEqual(resolved.truth_level, TRUTH_ACCEPTED)

    def test_duplicate_callback_idempotent(self) -> None:
        ingest_twilio_status_callback(
            {"MessageSid": "SM_dup_1", "MessageStatus": "delivered"}
        )
        ingest_twilio_status_callback(
            {"MessageSid": "SM_dup_1", "MessageStatus": "delivered"}
        )
        truth = get_delivery_truth("SM_dup_1")
        self.assertIsNotNone(truth)
        assert truth is not None
        self.assertEqual(truth.truth_level, TRUTH_DELIVERED)
        ingest_twilio_status_callback(
            {"MessageSid": "SM_dup_1", "MessageStatus": "queued"}
        )
        truth2 = get_delivery_truth("SM_dup_1")
        self.assertIsNotNone(truth2)
        assert truth2 is not None
        self.assertEqual(truth2.truth_level, TRUTH_DELIVERED)

    def test_advance_rank_only(self) -> None:
        persist_delivery_truth(
            DeliveryTruth(
                provider="twilio",
                message_sid="SM_rank_1",
                truth_level=TRUTH_DELIVERED,
                last_event_time=None,
            )
        )
        persist_delivery_truth(
            DeliveryTruth(
                provider="twilio",
                message_sid="SM_rank_1",
                truth_level=TRUTH_ACCEPTED,
            )
        )
        truth = get_delivery_truth("SM_rank_1")
        assert truth is not None
        self.assertEqual(truth.truth_level, TRUTH_DELIVERED)


class TwilioStatusCallbackWiringTests(unittest.TestCase):
    def test_resolve_explicit_env(self) -> None:
        from services.whatsapp_send import resolve_twilio_status_callback_url

        with patch.dict(
            os.environ,
            {
                "TWILIO_STATUS_CALLBACK_URL": "https://app.example/cb/",
                "CARTFLOW_PUBLIC_BASE_URL": "https://ignored.example",
            },
            clear=False,
        ):
            self.assertEqual(
                resolve_twilio_status_callback_url(),
                "https://app.example/cb",
            )

    def test_resolve_public_base_fallback(self) -> None:
        from services.whatsapp_send import resolve_twilio_status_callback_url

        env = os.environ.copy()
        env.pop("TWILIO_STATUS_CALLBACK_URL", None)
        with patch.dict(
            os.environ,
            {"CARTFLOW_PUBLIC_BASE_URL": "https://cartflow.railway.app"},
            clear=False,
        ):
            os.environ.pop("TWILIO_STATUS_CALLBACK_URL", None)
            self.assertEqual(
                resolve_twilio_status_callback_url(),
                "https://cartflow.railway.app/webhook/whatsapp/status",
            )

    def test_resolve_none_when_unset(self) -> None:
        from services.whatsapp_send import resolve_twilio_status_callback_url

        with patch.dict(os.environ, {}, clear=False):
            for key in (
                "TWILIO_STATUS_CALLBACK_URL",
                "CARTFLOW_PUBLIC_BASE_URL",
                "PUBLIC_BASE_URL",
            ):
                os.environ.pop(key, None)
            self.assertIsNone(resolve_twilio_status_callback_url())

    @patch.dict(
        os.environ,
        {
            "TWILIO_ACCOUNT_SID": "ACtest",
            "TWILIO_AUTH_TOKEN": "tok",
            "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
            "TWILIO_STATUS_CALLBACK_URL": "https://app.example/webhook/whatsapp/status",
        },
        clear=False,
    )
    @patch("services.whatsapp_send.Client")
    def test_send_passes_status_callback(self, mock_client_cls: MagicMock) -> None:
        from services.whatsapp_send import send_whatsapp

        mock_msg = MagicMock()
        mock_msg.sid = "SM_cb_wire_1"
        mock_msg.status = "queued"
        mock_client_cls.return_value.messages.create.return_value = mock_msg

        result = send_whatsapp("+966500000001", "test body")
        self.assertTrue(result.get("ok"))
        kwargs = mock_client_cls.return_value.messages.create.call_args.kwargs
        self.assertEqual(
            kwargs.get("status_callback"),
            "https://app.example/webhook/whatsapp/status",
        )
        self.assertEqual(kwargs.get("status_callback_method"), "POST")

    def test_status_webhook_emits_callback_received_log(self) -> None:
        client = TestClient(app)
        with patch("builtins.print") as mock_print:
            resp = client.post(
                "/webhook/whatsapp/status",
                data={
                    "MessageSid": "SM_log_1",
                    "MessageStatus": "delivered",
                },
            )
        self.assertEqual(resp.status_code, 200)
        printed = " ".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("[WA STATUS CALLBACK RECEIVED]", printed)
        self.assertIn("SM_log_1", printed)
        self.assertIn("delivered", printed)


class WhatsappDeliveryStatusWebhookTests(unittest.TestCase):
    @patch("main.handle_cart_abandoned")
    @patch("services.whatsapp_queue.enqueue_recovery_and_wait")
    def test_status_webhook_does_not_run_recovery(
        self, mock_enqueue: object, mock_abandon: object
    ) -> None:
        client = TestClient(app)
        resp = client.post(
            "/webhook/whatsapp/status",
            data={
                "MessageSid": "SM_webhook_iso_1",
                "MessageStatus": "delivered",
                "To": "whatsapp:+966500000099",
            },
        )
        self.assertEqual(resp.status_code, 200)
        mock_abandon.assert_not_called()
        mock_enqueue.assert_not_called()

    @patch("services.recovery_execution_boundary.execute_recovery_schedule")
    def test_status_webhook_does_not_execute_scheduled_recovery(
        self, mock_execute: object
    ) -> None:
        client = TestClient(app)
        client.post(
            "/webhook/whatsapp/status",
            json={
                "MessageSid": "SM_webhook_iso_2",
                "MessageStatus": "sent",
            },
        )
        mock_execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
