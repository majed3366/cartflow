# -*- coding: utf-8 -*-
"""Zid webhook auth: documented Basic Auth plus legacy HMAC."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import unittest
from types import SimpleNamespace

from starlette.datastructures import Headers

from integrations.zid_client import verify_webhook_signature, webhook_shared_secret


def _req(**headers: str) -> SimpleNamespace:
    return SimpleNamespace(headers=Headers(headers))


def _basic(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


class ZidWebhookAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {
            k: os.environ.get(k)
            for k in ("ZID_WEBHOOK_SECRET", "ZID_CLIENT_SECRET", "ZID_WEBHOOK_BASIC_USER")
        }

    def tearDown(self) -> None:
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_documented_basic_auth_accepted(self) -> None:
        os.environ["ZID_WEBHOOK_SECRET"] = "hook-secret"
        os.environ.pop("ZID_CLIENT_SECRET", None)
        req = _req(Authorization=_basic("cartflow", "hook-secret"))
        self.assertTrue(verify_webhook_signature(req, raw_body=b'{"event":"order.payment_status.update"}'))

    def test_client_secret_used_when_webhook_secret_unset(self) -> None:
        os.environ.pop("ZID_WEBHOOK_SECRET", None)
        os.environ["ZID_CLIENT_SECRET"] = "client-secret"
        req = _req(Authorization=_basic("cartflow", "client-secret"))
        self.assertTrue(verify_webhook_signature(req, raw_body=b"{}"))
        self.assertEqual(webhook_shared_secret(), "client-secret")

    def test_wrong_basic_password_rejected(self) -> None:
        os.environ["ZID_WEBHOOK_SECRET"] = "hook-secret"
        req = _req(Authorization=_basic("cartflow", "nope"))
        self.assertFalse(verify_webhook_signature(req, raw_body=b"{}"))

    def test_unsigned_rejected(self) -> None:
        os.environ["ZID_WEBHOOK_SECRET"] = "hook-secret"
        self.assertFalse(verify_webhook_signature(_req(), raw_body=b"{}"))

    def test_legacy_hmac_still_accepted(self) -> None:
        os.environ["ZID_WEBHOOK_SECRET"] = "hook-secret"
        body = b'{"event":"order.payment_status.update"}'
        digest = hmac.new(b"hook-secret", body, hashlib.sha256).hexdigest()
        req = _req(**{"X-Zid-Signature": digest})
        self.assertTrue(verify_webhook_signature(req, raw_body=body))


if __name__ == "__main__":
    unittest.main()
