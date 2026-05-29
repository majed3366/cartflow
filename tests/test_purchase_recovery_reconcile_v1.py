# -*- coding: utf-8 -*-
"""
Reconcile checkout purchase with the active recovery cart.

Bug: a customer returns from a recovery flow and completes checkout, but the
conversion recovery_key (store:session captured at checkout) differs from the
active cart's canonical recovery_key (store:session captured at abandon). Purchase
truth then lands under a key the dashboard never reads, so the cart stays under
"تحتاج تدخل" (needs intervention).

Fix: ``ingest_purchase_truth`` reconciles matched active carts — bridging durable
purchase truth + lifecycle closure to each cart's canonical recovery_key and
marking the cart recovered. Matching is by cart_id OR session_id (store-scoped).
"""
from __future__ import annotations

import os

import pytest

from extensions import db
from models import AbandonedCart, Store
from services.cartflow_purchase_truth import (
    has_purchase,
    reset_purchase_truth_foundation_for_tests,
)
from services.purchase_lifecycle_closure import (
    is_purchase_lifecycle_closed,
    reset_purchase_lifecycle_closure_for_tests,
)
from services.purchase_truth import ingest_purchase_truth_payload


def _reset() -> None:
    reset_purchase_truth_foundation_for_tests()
    reset_purchase_lifecycle_closure_for_tests()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset()
    yield
    _reset()


def _demo_store() -> Store:
    st = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
    if st is None:
        st = Store(zid_store_id="demo", recovery_delay=1, recovery_delay_unit="minutes")
        db.session.add(st)
        db.session.commit()
    return st


def _fresh_cart(*, sid: str, cid: str, store_id: int) -> AbandonedCart:
    db.session.query(AbandonedCart).filter(
        AbandonedCart.zid_cart_id == cid
    ).delete(synchronize_session=False)
    db.session.query(AbandonedCart).filter(
        AbandonedCart.recovery_session_id == sid
    ).delete(synchronize_session=False)
    db.session.commit()
    ac = AbandonedCart(
        store_id=store_id,
        zid_cart_id=cid,
        recovery_session_id=sid,
        customer_phone="+966500000001",
        status="abandoned",
        vip_mode=False,
    )
    db.session.add(ac)
    db.session.commit()
    return ac


def test_cartid_match_bridges_to_dashboard_key_and_recovers() -> None:
    """Conversion session drifts (S2) but cart_id (C1) matches → bridge to demo:S1."""
    st = _demo_store()
    ac = _fresh_cart(sid="recon-s1", cid="recon-c1", store_id=int(st.id))
    aid = int(ac.id)

    key = ingest_purchase_truth_payload(
        {
            "store_slug": "demo",
            "store": "demo",
            "session_id": "recon-s2",
            "cart_id": "recon-c1",
            "purchase_completed": True,
        }
    )
    assert key == "demo:recon-s2"

    # purchase truth bridged to the cart's canonical (dashboard) key
    assert has_purchase("demo:recon-s2")
    assert has_purchase("demo:recon-s1")
    assert is_purchase_lifecycle_closed("demo:recon-s1")

    db.session.expire_all()
    refreshed = db.session.get(AbandonedCart, aid)
    assert refreshed is not None
    assert str(refreshed.status or "").strip().lower() == "recovered"
    assert refreshed.recovered_at is not None


def test_session_match_marks_active_cart_recovered() -> None:
    """Same session → key already matches, but cart status must still flip to recovered."""
    st = _demo_store()
    ac = _fresh_cart(sid="recon-s3", cid="recon-c3", store_id=int(st.id))
    aid = int(ac.id)

    key = ingest_purchase_truth_payload(
        {
            "store_slug": "demo",
            "store": "demo",
            "session_id": "recon-s3",
            "purchase_completed": True,
        }
    )
    assert key == "demo:recon-s3"
    assert has_purchase("demo:recon-s3")

    db.session.expire_all()
    refreshed = db.session.get(AbandonedCart, aid)
    assert refreshed is not None
    assert str(refreshed.status or "").strip().lower() == "recovered"


def test_reconcile_helper_idempotent_on_already_recovered() -> None:
    """Re-ingesting a purchase for an already-recovered cart does not error or duplicate."""
    import main

    st = _demo_store()
    ac = _fresh_cart(sid="recon-s4", cid="recon-c4", store_id=int(st.id))
    aid = int(ac.id)

    first = main.reconcile_purchase_with_active_recovery_carts(
        recovery_key="demo:recon-s4",
        store_slug="demo",
        session_id="recon-s4",
        cart_id="recon-c4",
        purchase_source="purchase_completed",
    )
    assert first["carts_marked_recovered"] == 1

    second = main.reconcile_purchase_with_active_recovery_carts(
        recovery_key="demo:recon-s4",
        store_slug="demo",
        session_id="recon-s4",
        cart_id="recon-c4",
        purchase_source="purchase_completed",
    )
    # already recovered → not flipped again
    assert second["carts_marked_recovered"] == 0
    db.session.expire_all()
    refreshed = db.session.get(AbandonedCart, aid)
    assert str(refreshed.status or "").strip().lower() == "recovered"


def test_purchase_truth_trace_endpoint() -> None:
    """Dev trace endpoint surfaces matched carts + per-cart purchase detection."""
    from fastapi.testclient import TestClient

    import main

    st = _demo_store()
    _fresh_cart(sid="recon-s5", cid="recon-c5", store_id=int(st.id))

    ingest_purchase_truth_payload(
        {
            "store_slug": "demo",
            "store": "demo",
            "session_id": "recon-s6",
            "cart_id": "recon-c5",
            "purchase_completed": True,
        }
    )

    # Diagnostic must respond even outside development mode (production parity):
    # allowlisted in middleware + no in-endpoint dev-only 404 guard.
    prev_env = os.environ.get("ENV")
    os.environ["ENV"] = "production"
    try:
        client = TestClient(main.app)
        r = client.get(
            "/dev/purchase-truth-trace",
            params={"store_slug": "demo", "session_id": "recon-s6", "cart_id": "recon-c5"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["recovery_key"] == "demo:recon-s6"
        assert body["purchase_detected"] is True
        matched = body["matched_active_carts"]
        assert any(
            m.get("recovery_key") == "demo:recon-s5" and m.get("purchase_detected") is True
            for m in matched
        )
    finally:
        if prev_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = prev_env


def test_purchase_truth_trace_route_allowlisted_for_production() -> None:
    """Route is registered and allowed in production (no 404 gate)."""
    import main

    assert "/dev/purchase-truth-trace" in main._DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT
    assert any(
        getattr(r, "path", None) == "/dev/purchase-truth-trace"
        for r in main.app.router.routes
    )
