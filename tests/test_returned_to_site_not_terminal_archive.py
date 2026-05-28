# -*- coding: utf-8 -*-
"""Return-to-site must not move merchant carts to terminal history archive."""
from __future__ import annotations

import uuid

from extensions import db
from main import _normal_recovery_group_is_terminal_archived
from models import AbandonedCart


def test_returned_to_site_log_not_terminal_archived_group() -> None:
    db.create_all()
    suffix = uuid.uuid4().hex[:8]
    ac = AbandonedCart(
        recovery_session_id=f"sess-ret-arch-{suffix}",
        zid_cart_id=f"cart-ret-arch-{suffix}",
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
