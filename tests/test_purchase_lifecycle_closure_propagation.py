# -*- coding: utf-8 -*-
"""
Verify purchase lifecycle closure log propagation (root-cause documentation).

Real WhatsApp ``تم الطلب`` can show:

- ``[RECOVERY REPLY INTENT] intent=other`` — legacy ``detect_recovery_reply_intent``
  (behavioral / recovery_transition); does not include purchase-complete phrases.
- ``[CONTINUATION STOPPED] intent=PURCHASE`` — ``classify_reply_lifecycle_intent_v1``
  (continuation_stabilization_v1); treats ``تم الطلب`` as PURCHASE.

Missing ``[REPLY INTENT]`` / ``[PURCHASE LIFECYCLE CLOSED]`` on production usually means:

1. Reply-intent hook did not run (deploy without ``562aeb4``+) or was skipped
   (``[REPLY INTENT SKIPPED]`` — check logs).
2. Continuation stopped via ``is_purchase_lifecycle_closed`` / ``_is_user_converted``
   without a prior ``record_purchase_lifecycle_closure`` in this process (idempotent
   skip — no second ``[PURCHASE LIFECYCLE CLOSED]`` line).
3. ``record_purchase_lifecycle_closure`` never ran because ``recovery_key`` was empty
   in the continuation path (rare store lookup failure).

PASS on real reply requires all three stdout lines from the webhook order:
hook → closure → behavioral continuation.
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from extensions import db
from models import AbandonedCart, CartRecoveryLog, Store
from services.purchase_lifecycle_closure import (
    is_purchase_lifecycle_closed,
    reset_purchase_lifecycle_closure_for_tests,
)
from services.recovery_reply_intent_detector import detect_recovery_reply_intent
from services.reply_intent_handling import (
    INTENT_PURCHASE,
    classify_reply_lifecycle_intent_v1,
)

_TAM_ALTALIB = "\u062a\u0645 \u0627\u0644\u0637\u0644\u0628"


def _reset_memory() -> None:
    reset_purchase_lifecycle_closure_for_tests()
    import main
    from tests.test_recovery_isolation import _reset_recovery_memory

    _reset_recovery_memory()
    main._session_recovery_converted.clear()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset_memory()
    yield
    _reset_memory()


def test_dual_classifier_tam_altalib_recovery_other_lifecycle_purchase() -> None:
    """Explains intent=other vs intent=PURCHASE in the same inbound reply."""
    assert detect_recovery_reply_intent(_TAM_ALTALIB) == "other"
    assert classify_reply_lifecycle_intent_v1(_TAM_ALTALIB) == INTENT_PURCHASE


def test_converted_flag_can_stop_continuation_without_purchase_closed_log() -> None:
    """
    Reproduces production gap: converted memory without closure log.

    Continuation emits [CONTINUATION STOPPED] but not [PURCHASE LIFECYCLE CLOSED].
    """
    import main
    from services.cartflow_reply_intent_engine import (
        process_continuation_after_customer_reply,
    )

    st = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
    assert st is not None
    sid = "s-conv-gap"
    cid = "c-conv-gap"
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
        customer_phone="+966501239999",
        status="abandoned",
        vip_mode=False,
    )
    db.session.add(ac)
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id=cid,
            phone="966501239999",
            message="sent",
            status="sent_real",
            step=1,
        )
    )
    db.session.commit()

    rk = main._recovery_key_from_payload(
        {"store": "demo", "session_id": sid, "cart_id": cid}
    )
    main._session_recovery_converted[rk] = True
    assert is_purchase_lifecycle_closed(rk)

    buf = io.StringIO()
    with redirect_stdout(buf):
        process_continuation_after_customer_reply(
            ac,
            inbound_body=_TAM_ALTALIB,
            customer_phone_key="966501239999",
        )
    out = buf.getvalue()
    assert "[CONTINUATION STOPPED]" in out
    assert "intent=PURCHASE" in out
    assert "[PURCHASE LIFECYCLE CLOSED]" not in out


def test_webhook_propagation_reply_intent_closed_continuation_stopped() -> None:
    """Full chain when reply-intent hook runs (expected production PASS)."""
    import os

    os.environ["CARTFLOW_CONTINUATION_AUTO_REPLY"] = "0"
    import main

    client = TestClient(main.app)
    st = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
    if st is None:
        st = Store(zid_store_id="demo", recovery_delay=1, recovery_delay_unit="minutes")
        db.session.add(st)
        db.session.flush()
    sid = "s-prop-wh"
    cid = "c-prop-wh"
    phone = "966501236666"
    db.session.query(CartRecoveryLog).filter(CartRecoveryLog.session_id == sid).delete(
        synchronize_session=False
    )
    db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).delete(
        synchronize_session=False
    )
    db.session.commit()
    db.session.add(
        AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=cid,
            recovery_session_id=sid,
            customer_phone=f"+{phone}",
            status="abandoned",
            vip_mode=False,
        )
    )
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
    assert "terminal_state=closed_purchase" in out
    assert "future_recovery_allowed=false" in out
    assert "future_continuation_allowed=false" in out
    assert "[CONTINUATION STOPPED]" in out
    assert is_purchase_lifecycle_closed("demo:s-prop-wh")


def test_continuation_records_closed_when_reply_intent_hook_skipped() -> None:
    """Hook skipped; continuation must still emit [PURCHASE LIFECYCLE CLOSED]."""
    import os

    os.environ["CARTFLOW_CONTINUATION_AUTO_REPLY"] = "0"
    import main

    client = TestClient(main.app)
    st = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
    assert st is not None
    sid = "s-prop-skip-hook"
    cid = "c-prop-skip-hook"
    phone = "966501235555"
    db.session.query(CartRecoveryLog).filter(CartRecoveryLog.session_id == sid).delete(
        synchronize_session=False
    )
    db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).delete(
        synchronize_session=False
    )
    db.session.commit()
    db.session.add(
        AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=cid,
            recovery_session_id=sid,
            customer_phone=f"+{phone}",
            status="abandoned",
            vip_mode=False,
        )
    )
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
    with patch(
        "services.reply_intent_handling.run_inbound_whatsapp_reply_intent_hook",
        return_value=None,
    ):
        with redirect_stdout(buf):
            r = client.post(
                "/webhook/whatsapp",
                data={"Body": _TAM_ALTALIB, "From": f"whatsapp:+{phone}"},
            )
    assert r.status_code == 200
    out = buf.getvalue()
    assert "[REPLY INTENT]" not in out
    assert "[PURCHASE LIFECYCLE CLOSED]" in out
    assert "terminal_state=closed_purchase" in out
    assert "[CONTINUATION STOPPED]" in out
    assert "[RECOVERY REPLY INTENT] intent=other" in out
