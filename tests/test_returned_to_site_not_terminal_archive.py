# -*- coding: utf-8 -*-
"""Return-to-site must not move merchant carts to terminal history archive."""
from __future__ import annotations

from extensions import db
from main import (
    _normal_recovery_group_is_terminal_archived,
    _normal_recovery_recovery_log_statuses_lower_group,
)
from models import AbandonedCart


def test_returned_to_site_log_not_terminal_archived_group() -> None:
    db.create_all()
    ac = AbandonedCart(
        recovery_session_id="sess-ret-arch",
        zid_cart_id="cart-ret-arch",
        cart_value=199.0,
        status="abandoned",
    )
    db.session.add(ac)
    db.session.commit()
    log_u = frozenset({"mock_sent", "returned_to_site"})
    bh = {"user_returned_to_site": True, "customer_returned_to_site": True}
    assert (
        _normal_recovery_group_is_terminal_archived(
            [ac],
            behavioral_override=bh,
            recovery_log_statuses=log_u,
            phase_key="customer_returned",
        )
        is False
    )
