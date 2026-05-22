# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import io
from contextlib import redirect_stdout
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from extensions import db
from models import AbandonedCart, CartRecoveryLog, Store
from services.purchase_lifecycle_closure import (
    TERMINAL_STATE_CLOSED_PURCHASE,
    block_recovery_if_purchase_lifecycle_closed,
    is_purchase_lifecycle_closed,
    record_purchase_lifecycle_closure,
    reset_purchase_lifecycle_closure_for_tests,
)
from services.reply_intent_handling import INTENT_PURCHASE

_TAM_ALTALIB = "\u062a\u0645 \u0627\u0644\u0637\u0644\u0628"


def _reset_all() -> None:
    reset_purchase_lifecycle_closure_for_tests()
    import main
    from tests.test_recovery_isolation import _reset_recovery_memory

    _reset_recovery_memory()
    main._session_recovery_converted.clear()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset_all()
    yield
    _reset_all()


def test_record_logs_purchase_lifecycle_closed() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        record_purchase_lifecycle_closure(
            "demo:s-closed",
            session_id="s-closed",
            cart_id="c-closed",
            source="test",
        )
    out = buf.getvalue()
    assert "[PURCHASE LIFECYCLE CLOSED]" in out
    assert "terminal_state=closed_purchase" in out
    assert "future_recovery_allowed=false" in out
    assert "future_continuation_allowed=false" in out
    assert is_purchase_lifecycle_closed("demo:s-closed")


def test_block_recovery_after_closure() -> None:
    record_purchase_lifecycle_closure("demo:s-block", session_id="s-block")
    buf = io.StringIO()
    with redirect_stdout(buf):
        blocked = block_recovery_if_purchase_lifecycle_closed(
            "demo:s-block",
            session_id="s-block",
            cart_id="c-block",
        )
    assert blocked is True
    assert "[RECOVERY BLOCKED]" in buf.getvalue()
    assert "reason=lifecycle_closed_purchase" in buf.getvalue()


def test_conversion_marks_closed() -> None:
    import main

    buf = io.StringIO()
    with redirect_stdout(buf):
        main._mark_user_converted_for_payload(
            {"store": "demo", "session_id": "s-conv", "cart_id": "c-conv"}
        )
    out = buf.getvalue()
    assert "[PURCHASE LIFECYCLE CLOSED]" in out
    assert main._is_user_converted("demo:s-conv")


def test_tam_altalib_reply_closes_and_blocks_continuation() -> None:
    from services.cartflow_reply_intent_engine import (
        decide_continuation,
        process_continuation_after_customer_reply,
    )

    st = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
    if st is None:
        st = Store(zid_store_id="demo", recovery_delay=1, recovery_delay_unit="minutes")
        db.session.add(st)
        db.session.flush()
    db.session.query(CartRecoveryLog).filter(CartRecoveryLog.session_id == "s-pur").delete(
        synchronize_session=False
    )
    db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == "c-pur").delete(
        synchronize_session=False
    )
    db.session.commit()
    ac = AbandonedCart(
        store_id=int(st.id),
        zid_cart_id="c-pur",
        recovery_session_id="s-pur",
        customer_phone="+966501238888",
        status="abandoned",
        vip_mode=False,
    )
    db.session.add(ac)
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id="s-pur",
            cart_id="c-pur",
            phone="966501238888",
            message="sent",
            status="sent_real",
            step=1,
        )
    )
    db.session.commit()

    buf = io.StringIO()
    with redirect_stdout(buf):
        d = decide_continuation(
            inbound_body=_TAM_ALTALIB,
            behavioral={},
            reason_tag="price",
            ac=ac,
        )
        process_continuation_after_customer_reply(
            ac,
            inbound_body=_TAM_ALTALIB,
            customer_phone_key="966501238888",
        )
    out = buf.getvalue()
    assert d.lifecycle_intent == INTENT_PURCHASE
    assert d.stop_continuation is True
    assert d.should_send is False
    assert "[PURCHASE LIFECYCLE CLOSED]" in out
    assert "[CONTINUATION STOPPED]" in out
    assert "intent=PURCHASE" in out
    assert is_purchase_lifecycle_closed("demo:s-pur")


def test_recovery_impl_blocked_after_closure() -> None:
    import main

    record_purchase_lifecycle_closure(
        "demo:s-impl",
        session_id="s-impl",
        cart_id="c-impl",
    )
    buf = io.StringIO()

    async def _run() -> None:
        with redirect_stdout(buf):
            await main._run_recovery_sequence_after_cart_abandoned_impl(
                "demo:s-impl",
                0.0,
                "demo",
                "s-impl",
                "c-impl",
                None,
                recovery_context={"recovery_post_delay_only": True, "reason_tag": "price"},
            )

    with patch.object(main.asyncio, "sleep", new_callable=AsyncMock):
        asyncio.run(_run())
    out = buf.getvalue()
    assert "[RECOVERY BLOCKED]" in out
    assert "lifecycle_closed_purchase" in out


def test_webhook_tam_altalib_full_chain() -> None:
    import os

    os.environ["CARTFLOW_CONTINUATION_AUTO_REPLY"] = "0"
    import main

    client = TestClient(main.app)
    st = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
    if st is None:
        st = Store(zid_store_id="demo", recovery_delay=1, recovery_delay_unit="minutes")
        db.session.add(st)
        db.session.flush()
    sid = "s-wh-pur"
    cid = "c-wh-pur"
    phone = "966501237777"
    db.session.query(CartRecoveryLog).filter(CartRecoveryLog.session_id == sid).delete(
        synchronize_session=False
    )
    db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).delete(
        synchronize_session=False
    )
    db.session.commit()
    ac = AbandonedCart(
        store_id=int(st.id),
        zid_cart_id=cid,
        recovery_session_id=sid,
        customer_phone=f"+{phone}",
        status="abandoned",
        vip_mode=False,
    )
    db.session.add(ac)
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id=cid,
            phone=phone,
            message="recovery",
            status="sent_real",
            step=1,
        )
    )
    db.session.commit()

    buf = io.StringIO()
    with redirect_stdout(buf):
        r = client.post(
            "/webhook/whatsapp",
            data={"Body": _TAM_ALTALIB, "From": f"whatsapp:+{phone}"},
        )
    assert r.status_code == 200
    out = buf.getvalue()
    assert "[REPLY INTENT]" in out
    assert "intent=PURCHASE" in out
    assert "[PURCHASE LIFECYCLE CLOSED]" in out
    assert "[CONTINUATION STOPPED]" in out
    assert is_purchase_lifecycle_closed("demo:s-wh-pur")
