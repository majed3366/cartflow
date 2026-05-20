# -*- coding: utf-8 -*-
"""Scoped store cache invalidation after commit — fresh reason_templates for recovery."""

from __future__ import annotations

from services.cart_event_request_scope import (
    cart_event_request_begin,
    cart_event_request_end,
    cart_event_scope_invalidate_after_commit,
    scoped_store_contains,
    scoped_store_get,
    scoped_store_set,
)


def test_after_commit_clears_scoped_store_cache() -> None:
    cart_event_request_begin()
    try:
        scoped_store_set("zid:demo", {"reason_templates_json": "{}"})
        assert scoped_store_contains("zid:demo")
        cart_event_scope_invalidate_after_commit()
        assert not scoped_store_contains("zid:demo")
    finally:
        cart_event_request_end()
