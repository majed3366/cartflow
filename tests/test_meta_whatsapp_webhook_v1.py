# -*- coding: utf-8 -*-
"""Meta WhatsApp Cloud API webhook verification and event parsing."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services.meta_whatsapp_webhook_v1 import (
    clear_webhook_state_for_tests,
    get_webhook_diagnostics,
    process_webhook_payload,
    verify_subscription,
)


def _status_payload(wamid: str, status: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": "PHONE_NUMBER_ID",
                            },
                            "statuses": [
                                {
                                    "id": wamid,
                                    "status": status,
                                    "timestamp": "1710000000",
                                    "recipient_id": "966501234567",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _inbound_payload(
    wamid: str,
    from_id: str,
    text: str,
) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": "PHONE_NUMBER_ID",
                            },
                            "messages": [
                                {
                                    "from": from_id,
                                    "id": wamid,
                                    "timestamp": "1710000001",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


class MetaWhatsappWebhookServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_webhook_state_for_tests()

    def tearDown(self) -> None:
        clear_webhook_state_for_tests()

    @patch.dict("os.environ", {"META_WEBHOOK_VERIFY_TOKEN": "meta-verify-token"}, clear=True)
    def test_challenge_verification(self) -> None:
        ok, err, challenge = verify_subscription(
            "subscribe",
            "meta-verify-token",
            "1234567890",
        )
        self.assertTrue(ok)
        self.assertEqual(err, "")
        self.assertEqual(challenge, "1234567890")

    @patch.dict("os.environ", {"META_WEBHOOK_VERIFY_TOKEN": "meta-verify-token"}, clear=True)
    def test_challenge_verification_fails_on_token(self) -> None:
        ok, err, challenge = verify_subscription(
            "subscribe",
            "wrong-token",
            "1234567890",
        )
        self.assertFalse(ok)
        self.assertEqual(err, "verify_token_mismatch")
        self.assertIsNone(challenge)

    def test_delivered_event(self) -> None:
        wamid = "wamid.DELIVERED123"
        out = process_webhook_payload(_status_payload(wamid, "delivered"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["parsed_counts"]["delivered"], 1)
        diag = get_webhook_diagnostics()
        self.assertEqual(diag["last_delivered"]["wamid"], wamid)
        self.assertEqual(diag["last_delivered"]["status"], "delivered")

    def test_read_event(self) -> None:
        wamid = "wamid.READ123"
        out = process_webhook_payload(_status_payload(wamid, "read"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["parsed_counts"]["read"], 1)
        diag = get_webhook_diagnostics()
        self.assertEqual(diag["last_read"]["wamid"], wamid)
        self.assertEqual(diag["last_read"]["status"], "read")

    def test_inbound_message_event(self) -> None:
        wamid = "wamid.INBOUND123"
        out = process_webhook_payload(
            _inbound_payload(wamid, "966501234567", "مرحبا")
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["parsed_counts"]["inbound"], 1)
        diag = get_webhook_diagnostics()
        self.assertEqual(diag["last_inbound"]["message_id"], wamid)
        self.assertEqual(diag["last_inbound"]["from"], "966501234567")
        self.assertEqual(diag["last_inbound"]["text"], "مرحبا")


class MetaWhatsappWebhookRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev = os.environ.get("META_WEBHOOK_VERIFY_TOKEN")
        clear_webhook_state_for_tests()
        os.environ["META_WEBHOOK_VERIFY_TOKEN"] = "route-verify-token"

    def tearDown(self) -> None:
        clear_webhook_state_for_tests()
        if self._prev is not None:
            os.environ["META_WEBHOOK_VERIFY_TOKEN"] = self._prev
        else:
            os.environ.pop("META_WEBHOOK_VERIFY_TOKEN", None)

    def test_get_challenge_route(self) -> None:
        client = TestClient(app)
        r = client.get(
            "/webhooks/meta/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "route-verify-token",
                "hub.challenge": "999888777",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, "999888777")

    def test_post_delivered_route(self) -> None:
        client = TestClient(app)
        wamid = "wamid.ROUTE_DELIVERED"
        r = client.post(
            "/webhooks/meta/whatsapp",
            json=_status_payload(wamid, "delivered"),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, "OK")
        diag = get_webhook_diagnostics()
        self.assertEqual(diag["last_delivered"]["wamid"], wamid)


if __name__ == "__main__":
    unittest.main()
