# -*- coding: utf-8 -*-
"""Reality Validation: Workspace must auth demo Living Store review sessions."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from services.cart_workspace.merchant_api_v1 import _auth_slug


def test_workspace_auth_accepts_demo_living_store_primary() -> None:
    req = MagicMock()
    req.cookies = {"cf_merchant_session": "test"}
    with patch(
        "services.merchant_auth_v1.resolve_authenticated_store_slug",
        return_value="demo",
    ):
        assert _auth_slug(req) == "demo"


def test_workspace_auth_rejects_missing_session() -> None:
    req = MagicMock()
    req.cookies = {}
    with patch(
        "services.merchant_auth_v1.resolve_authenticated_store_slug",
        return_value=None,
    ):
        assert _auth_slug(req) is None
