# -*- coding: utf-8 -*-
"""Recovery Checkout Click Tracking V1 — redirect + governed evidence."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from services.meta_recovery_template_contract_v1 import TEMPLATE_CHECKOUT_URL_EXAMPLE
from services.recovery_checkout_redirect_v1 import (
    ERROR_ARCHIVED,
    ERROR_EXPIRED,
    ERROR_INVALID,
    ERROR_MALFORMED,
    ERROR_MISSING,
    mint_checkout_redirect_token,
    resolve_checkout_redirect_token,
)
from services.recovery_click_tracking_v1 import (
    EVENT_TYPE_CHECKOUT_BUTTON_CLICKED,
    build_checkout_click_payload,
    record_checkout_button_click,
)


class TokenTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["SECRET_KEY"] = "unit-test-checkout-click-secret-key-32b"

    def test_mint_and_resolve(self) -> None:
        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-click-1",
            store_slug="store-a",
            template_name="cartflow_cart_reminder_ar_v1",
            provider="meta",
            now_ts=1_700_000_000,
        )
        self.assertIsNotNone(token)
        self.assertTrue(str(token).startswith("v1."))
        # Destination must not appear in cleartext token
        self.assertNotIn("merchant.com", token or "")
        self.assertNotIn("cart/restore", token or "")

        resolved = resolve_checkout_redirect_token(
            token, now_ts=1_700_000_000, check_archived=False
        )
        self.assertTrue(resolved.ok)
        assert resolved.claims is not None
        self.assertEqual(resolved.claims.destination_url, TEMPLATE_CHECKOUT_URL_EXAMPLE)
        self.assertEqual(resolved.claims.recovery_key, "rk-click-1")
        safe = resolved.claims.to_safe_dict()
        self.assertNotIn("destination_url", safe)

    def test_missing_token(self) -> None:
        r = resolve_checkout_redirect_token("", check_archived=False)
        self.assertFalse(r.ok)
        self.assertEqual(r.error_code, ERROR_MISSING)

    def test_malformed_token(self) -> None:
        r = resolve_checkout_redirect_token("v1.not-valid", check_archived=False)
        self.assertFalse(r.ok)
        self.assertIn(r.error_code, (ERROR_MALFORMED, ERROR_INVALID))

    def test_invalid_signature(self) -> None:
        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk",
            now_ts=1_700_000_000,
        )
        assert token is not None
        bad = token[:-4] + "XXXX"
        r = resolve_checkout_redirect_token(bad, now_ts=1_700_000_000, check_archived=False)
        self.assertFalse(r.ok)
        self.assertEqual(r.error_code, ERROR_INVALID)

    def test_expired_token(self) -> None:
        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-exp",
            ttl_seconds=60,
            now_ts=1_700_000_000,
        )
        r = resolve_checkout_redirect_token(
            token, now_ts=1_700_000_000 + 120, check_archived=False
        )
        self.assertFalse(r.ok)
        self.assertEqual(r.error_code, ERROR_EXPIRED)

    @patch("services.recovery_checkout_redirect_v1.is_recovery_archived", return_value=True)
    def test_archived_recovery(self, _arch: MagicMock) -> None:
        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-archived",
            now_ts=1_700_000_000,
        )
        r = resolve_checkout_redirect_token(token, now_ts=1_700_000_000, check_archived=True)
        self.assertFalse(r.ok)
        self.assertEqual(r.error_code, ERROR_ARCHIVED)


class ClickTrackingTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["SECRET_KEY"] = "unit-test-checkout-click-secret-key-32b"

    def test_event_contents_and_no_purchase_inferred(self) -> None:
        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-ev",
            store_slug="slug",
            template_name="cartflow_cart_reminder_ar_v1",
            message_id="mid-1",
            customer_phone="966501234567",
            provider="meta",
            provider_message_id="wamid.1",
            now_ts=1_700_000_000,
        )
        claims = resolve_checkout_redirect_token(
            token, now_ts=1_700_000_000, check_archived=False
        ).claims
        assert claims is not None
        payload = build_checkout_click_payload(
            claims=claims,
            redirect_token=token or "",
            user_agent="UA-Test",
            ip_address="1.2.3.4",
            referer="https://wa.me/",
        )
        self.assertEqual(payload["event"], EVENT_TYPE_CHECKOUT_BUTTON_CLICKED)
        self.assertEqual(payload["recovery_key"], "rk-ev")
        self.assertEqual(payload["template_name"], "cartflow_cart_reminder_ar_v1")
        self.assertEqual(payload["destination_url"], TEMPLATE_CHECKOUT_URL_EXAMPLE)
        self.assertEqual(payload["message_id"], "mid-1")
        self.assertEqual(payload["store_slug"], "slug")
        self.assertEqual(payload["customer_phone"], "966501234567")
        self.assertEqual(payload["provider"], "meta")
        self.assertEqual(payload["provider_message_id"], "wamid.1")
        self.assertFalse(payload["purchase_inferred"])
        self.assertFalse(payload["recovered_inferred"])
        self.assertFalse(payload["completed_inferred"])
        self.assertIn("clicked_at", payload)
        self.assertIn("redirect_token_fingerprint", payload)

    def test_record_once(self) -> None:
        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-once",
            now_ts=1_700_000_000,
        )
        claims = resolve_checkout_redirect_token(
            token, now_ts=1_700_000_000, check_archived=False
        ).claims
        assert claims is not None

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.session = mock_session
        mock_db.create_all = MagicMock()
        with patch("extensions.db", mock_db):
            with patch("models.RecoveryEvent") as MockEvent:
                row = MagicMock()
                row.id = 42
                MockEvent.return_value = row
                mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
                out = record_checkout_button_click(
                    claims=claims,
                    redirect_token=token or "",
                    user_agent="ua",
                    ip_address="127.0.0.1",
                    referer="",
                )
        self.assertTrue(out["ok"])
        self.assertEqual(out["event_type"], EVENT_TYPE_CHECKOUT_BUTTON_CLICKED)
        self.assertFalse(out["purchase_inferred"])
        self.assertEqual(out["recovery_key"], "rk-once")
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_tracking_failure_still_ok_for_caller(self) -> None:
        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-fail",
            now_ts=1_700_000_000,
        )
        claims = resolve_checkout_redirect_token(
            token, now_ts=1_700_000_000, check_archived=False
        ).claims
        assert claims is not None
        with patch("extensions.db") as mock_db:
            mock_db.create_all.side_effect = RuntimeError("db down")
            out = record_checkout_button_click(
                claims=claims,
                redirect_token=token or "",
            )
        self.assertFalse(out["ok"])
        self.assertFalse(out["purchase_inferred"])


class RedirectRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["SECRET_KEY"] = "unit-test-checkout-click-secret-key-32b"
        os.environ.setdefault("CARTFLOW_ADMIN_PASSWORD", "x")

    def test_valid_redirect_records_click(self) -> None:
        from main import app

        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-route",
            store_slug="s1",
            template_name="cartflow_cart_reminder_ar_v1",
            now_ts=1_700_000_000,
        )
        client = TestClient(app)
        with patch(
            "routes.wa_checkout_redirect_v1.record_checkout_button_click",
            return_value={"ok": True, "purchase_inferred": False},
        ) as mock_rec:
            with patch(
                "routes.wa_checkout_redirect_v1.resolve_checkout_redirect_token",
                wraps=resolve_checkout_redirect_token,
            ):
                # freeze time via resolve wrapper
                with patch(
                    "services.recovery_checkout_redirect_v1.time.time",
                    return_value=1_700_000_000,
                ):
                    r = client.get(
                        f"/wa/checkout/{token}",
                        follow_redirects=False,
                        headers={"User-Agent": "ClickTestUA", "Referer": "https://x"},
                    )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers.get("location"), TEMPLATE_CHECKOUT_URL_EXAMPLE)
        mock_rec.assert_called_once()
        body = r.content.decode("utf-8", errors="ignore")
        self.assertNotIn("merchant.com", body)

    def test_invalid_token_no_destination_leak(self) -> None:
        from main import app

        client = TestClient(app)
        r = client.get("/wa/checkout/not-a-valid-token!!!", follow_redirects=False)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertFalse(data.get("ok"))
        self.assertNotIn("destination", json.dumps(data).lower())
        self.assertNotIn("http", json.dumps(data).lower())

    def test_redirect_succeeds_if_tracking_fails(self) -> None:
        from main import app

        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-track-fail",
            now_ts=1_700_000_000,
        )
        client = TestClient(app)
        with patch(
            "routes.wa_checkout_redirect_v1.record_checkout_button_click",
            side_effect=RuntimeError("boom"),
        ):
            with patch(
                "services.recovery_checkout_redirect_v1.time.time",
                return_value=1_700_000_000,
            ):
                r = client.get(f"/wa/checkout/{token}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers.get("location"), TEMPLATE_CHECKOUT_URL_EXAMPLE)

    def test_duplicate_click_still_redirects(self) -> None:
        from main import app

        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-dup",
            now_ts=1_700_000_000,
        )
        client = TestClient(app)
        with patch(
            "routes.wa_checkout_redirect_v1.record_checkout_button_click",
            return_value={"ok": True, "is_duplicate_click": True},
        ) as mock_rec:
            with patch(
                "services.recovery_checkout_redirect_v1.time.time",
                return_value=1_700_000_000,
            ):
                r1 = client.get(f"/wa/checkout/{token}", follow_redirects=False)
                r2 = client.get(f"/wa/checkout/{token}", follow_redirects=False)
        self.assertEqual(r1.status_code, 302)
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(mock_rec.call_count, 2)

    def test_safe_logging_no_full_url(self) -> None:
        token = mint_checkout_redirect_token(
            checkout_url=TEMPLATE_CHECKOUT_URL_EXAMPLE,
            recovery_key="rk-log",
            now_ts=1_700_000_000,
        )
        claims = resolve_checkout_redirect_token(
            token, now_ts=1_700_000_000, check_archived=False
        ).claims
        assert claims is not None
        with patch("extensions.db") as mock_db:
            mock_session = MagicMock()
            mock_db.session = mock_session
            mock_db.create_all = MagicMock()
            with patch("models.RecoveryEvent") as MockEvent:
                row = MagicMock()
                row.id = 7
                MockEvent.return_value = row
                mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
                buf = []
                with patch("builtins.print", side_effect=lambda *a, **k: buf.append(" ".join(map(str, a)))):
                    record_checkout_button_click(claims=claims, redirect_token=token or "")
        joined = "\n".join(buf)
        self.assertNotIn(TEMPLATE_CHECKOUT_URL_EXAMPLE, joined)
        self.assertNotIn("/cart/restore/", joined)


class LegacyCompatTests(unittest.TestCase):
    def test_legacy_base64_url_still_redirects(self) -> None:
        from main import app
        from services.meta_recovery_template_contract_v1 import (
            encode_checkout_url_button_param,
        )

        legacy = encode_checkout_url_button_param(TEMPLATE_CHECKOUT_URL_EXAMPLE)
        client = TestClient(app)
        with patch(
            "routes.wa_checkout_redirect_v1.record_checkout_button_click",
            return_value={"ok": True},
        ):
            r = client.get(f"/wa/checkout/{legacy}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers.get("location"), TEMPLATE_CHECKOUT_URL_EXAMPLE)


if __name__ == "__main__":
    unittest.main()
