# -*- coding: utf-8 -*-
"""Continuation decision trace v1 — reason→path mapping and acceptance."""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from services.cartflow_reply_intent_engine import (
    CONTINUATION_ACTION_REASSURANCE,
    decide_continuation,
    process_continuation_after_customer_reply,
    reset_continuation_engine_for_tests,
)
from services.continuation_decision_trace_v1 import (
    CHOSEN_PATH_FALLBACK,
    CHOSEN_PATH_PRICE,
    CHOSEN_PATH_QUALITY,
    CHOSEN_PATH_SHIPPING,
    build_continuation_trace_v1,
    dashboard_explanation_ar,
    resolve_chosen_path,
)
from services.continuation_stabilization_v1 import PRICE_REASSURANCE_MESSAGE_AR


def _mock_ac() -> MagicMock:
    ac = MagicMock()
    ac.zid_cart_id = "c-trace"
    ac.recovery_session_id = "s-trace"
    ac.cart_url = ""
    ac.store_id = None
    ac.raw_payload = None
    ac.vip_mode = False
    return ac


def test_resolve_chosen_path_by_reason() -> None:
    assert (
        resolve_chosen_path("price", action=CONTINUATION_ACTION_REASSURANCE)
        == CHOSEN_PATH_PRICE
    )
    assert (
        resolve_chosen_path("shipping", action=CONTINUATION_ACTION_REASSURANCE)
        == CHOSEN_PATH_SHIPPING
    )
    assert (
        resolve_chosen_path("quality", action=CONTINUATION_ACTION_REASSURANCE)
        == CHOSEN_PATH_QUALITY
    )
    assert (
        resolve_chosen_path(
            "other",
            action="wait_for_customer_reply",
            contextual_intent="unknown_reply",
        )
        == CHOSEN_PATH_FALLBACK
    )


def test_price_reason_nam_acceptance_path_and_explanation() -> None:
    """Acceptance: السعر abandonment + نعم → price_handling + dashboard explanation."""
    d = decide_continuation(
        inbound_body="نعم",
        behavioral={"recovery_previous_offer_strategy": ""},
        reason_tag="price",
        ac=_mock_ac(),
        prior_behavioral_before_reply={},
    )
    assert d.contextual_intent == "yes_to_cheaper_alternative"
    assert d.chosen_path == CHOSEN_PATH_PRICE
    assert d.template_name == "price_reassurance_v1"
    assert d.fallback_used is False
    assert PRICE_REASSURANCE_MESSAGE_AR in d.message_to_send
    assert dashboard_explanation_ar("price", d.chosen_path) == (
        "اختار النظام هذا الرد لأن الاعتراض = السعر"
    )
    assert d.dashboard_explanation_ar == dashboard_explanation_ar("price", d.chosen_path)


def test_continuation_trace_log_before_send() -> None:
    reset_continuation_engine_for_tests()
    ac = _mock_ac()
    phone_key = "966501112233"
    merged: dict = {}

    def _merge(_ac: MagicMock, **kwargs: object) -> None:
        merged.update(kwargs)

    buf = io.StringIO()
    with redirect_stdout(buf), patch(
        "services.behavioral_recovery.state_store.normal_recovery_message_was_sent_for_abandoned",
        return_value=True,
    ), patch(
        "services.behavioral_recovery.state_store.behavioral_dict_for_abandoned_cart",
        side_effect=lambda _ac: dict(merged),
    ), patch(
        "services.behavioral_recovery.state_store.merge_behavioral_state",
        side_effect=_merge,
    ), patch(
        "services.cartflow_reply_intent_engine._reason_tag_for_abandoned_cart",
        return_value="price",
    ), patch(
        "services.cartflow_reply_intent_engine._inbound_duplicate_recent",
        return_value=False,
    ), patch(
        "services.whatsapp_send.send_whatsapp_real",
        return_value={"ok": True},
    ), patch(
        "services.cartflow_reply_intent_engine.continuation_auto_reply_enabled",
        return_value=True,
    ), patch(
        "services.cartflow_reply_intent_engine.continuation_cooldown_seconds",
        return_value=15.0,
    ), patch(
        "services.cartflow_reply_intent_engine._resolve_outbound_e164_for_continuation",
        return_value="+966501112233",
    ), patch(
        "services.cartflow_reply_intent_engine._continuation_wa_trace_store_slug",
        return_value="demo",
    ), patch(
        "main._recovery_key_from_payload",
        return_value="demo:s-trace",
    ), patch(
        "main._normalize_store_slug",
        return_value="demo",
    ), patch(
        "services.recovery_truth_timeline_v1.record_recovery_truth_event",
        return_value=True,
    ) as rec:
        process_continuation_after_customer_reply(
            ac,
            inbound_body="نعم",
            customer_phone_key=phone_key,
            prior_behavioral_before_reply={},
        )

    out = buf.getvalue()
    assert "[CONTINUATION TRACE]" in out
    assert "chosen_path=price_handling" in out
    assert "reason_tag=price" in out
    assert merged.get("continuation_chosen_path") == CHOSEN_PATH_PRICE
    assert "السعر" in str(merged.get("continuation_dashboard_explanation_ar") or "")
    assert rec.called
    src = rec.call_args.kwargs.get("source") or rec.call_args[1].get("source", "")
    assert "cp=price_handling" in str(src)


def test_trace_builder_template_name() -> None:
    t = build_continuation_trace_v1(
        recovery_key="demo:s1",
        reason_tag="shipping",
        customer_reply="نعم",
        action="explain_shipping",
        continuation_state="customer_asking_shipping",
        store_slug="demo",
    )
    assert t.chosen_path == CHOSEN_PATH_SHIPPING
    assert t.template_name == "explain_shipping"
    assert "cp=shipping_handling" in t.timeline_source_suffix("proc")
