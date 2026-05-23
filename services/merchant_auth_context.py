# -*- coding: utf-8 -*-
"""Request-scoped merchant store slug for dashboard reads."""
from __future__ import annotations

import contextvars
from typing import Optional

merchant_auth_store_slug_cv: contextvars.ContextVar[Optional[str]] = (
    contextvars.ContextVar("merchant_auth_store_slug", default=None)
)


def set_merchant_auth_store_slug(slug: Optional[str]) -> contextvars.Token:
    return merchant_auth_store_slug_cv.set(
        (slug or "").strip()[:255] or None
    )


def reset_merchant_auth_store_slug(token: contextvars.Token) -> None:
    merchant_auth_store_slug_cv.reset(token)


def get_merchant_auth_store_slug() -> Optional[str]:
    return merchant_auth_store_slug_cv.get()


__all__ = [
    "get_merchant_auth_store_slug",
    "merchant_auth_store_slug_cv",
    "reset_merchant_auth_store_slug",
    "set_merchant_auth_store_slug",
]
