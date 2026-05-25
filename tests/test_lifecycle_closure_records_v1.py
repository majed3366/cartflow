# -*- coding: utf-8 -*-
"""Durable lifecycle closure records v1 — terminal outcomes."""
from __future__ import annotations

import io
from contextlib import redirect_stdout

import pytest

from extensions import db
from models import LifecycleClosureRecord
from schema_lifecycle_closure import reset_lifecycle_closure_schema_guard_for_tests
from services.lifecycle_closure_records_v1 import (
    CLOSURE_CUSTOMER_REPLIED,
    CLOSURE_FAILED,
    CLOSURE_MAX_ATTEMPTS,
    CLOSURE_PURCHASE_COMPLETED,
    CLOSURE_RETURNED_TO_SITE,
    get_durable_closure,
    maybe_record_closure_from_recovery_log,
    record_lifecycle_closure,
    reset_lifecycle_closure_records_for_tests,
)


def _reset() -> None:
    reset_lifecycle_closure_schema_guard_for_tests()
    reset_lifecycle_closure_records_for_tests()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset()
    db.create_all()
    yield
    _reset()


def test_scenario_a_return_to_site() -> None:
    rk = "demo:s-return"
    assert maybe_record_closure_from_recovery_log(
        recovery_key=rk,
        log_status="returned_to_site",
        store_slug="demo",
        session_id="s-return",
    )
    row = get_durable_closure(rk)
    assert row is not None
    assert row["closure_status"] == CLOSURE_RETURNED_TO_SITE
    assert row["store_slug"] == "demo"
    assert row["session_id"] == "s-return"


def test_scenario_b_customer_replied() -> None:
    rk = "demo:s-reply"
    maybe_record_closure_from_recovery_log(
        recovery_key=rk,
        log_status="skipped_followup_customer_replied",
        store_slug="demo",
        session_id="s-reply",
    )
    assert get_durable_closure(rk)["closure_status"] == CLOSURE_CUSTOMER_REPLIED


def test_scenario_c_attempt_limit() -> None:
    rk = "demo:s-limit"
    maybe_record_closure_from_recovery_log(
        recovery_key=rk,
        log_status="skipped_attempt_limit",
        store_slug="demo",
        session_id="s-limit",
    )
    assert get_durable_closure(rk)["closure_status"] == CLOSURE_MAX_ATTEMPTS


def test_scenario_d_whatsapp_failed_final() -> None:
    rk = "demo:s-fail"
    maybe_record_closure_from_recovery_log(
        recovery_key=rk,
        log_status="failed_final",
        store_slug="demo",
        session_id="s-fail",
    )
    assert get_durable_closure(rk)["closure_status"] == CLOSURE_FAILED


def test_scenario_e_purchase_beats_return() -> None:
    rk = "demo:s-pe"
    record_lifecycle_closure(
        rk,
        closure_status=CLOSURE_RETURNED_TO_SITE,
        closure_reason="return",
        closure_source="test",
        store_slug="demo",
        session_id="s-pe",
    )
    record_lifecycle_closure(
        rk,
        closure_status=CLOSURE_PURCHASE_COMPLETED,
        closure_reason="purchase",
        closure_source="test",
    )
    assert get_durable_closure(rk)["closure_status"] == CLOSURE_PURCHASE_COMPLETED


def test_scenario_f_restart_survives() -> None:
    rk = "demo:s-restart"
    record_lifecycle_closure(
        rk,
        closure_status=CLOSURE_CUSTOMER_REPLIED,
        closure_reason="replied",
        closure_source="test",
    )
    row = (
        db.session.query(LifecycleClosureRecord)
        .filter(LifecycleClosureRecord.recovery_key == rk)
        .first()
    )
    assert row is not None
    db.session.expire_all()
    assert get_durable_closure(rk)["closure_status"] == CLOSURE_CUSTOMER_REPLIED


def test_idempotent_same_status() -> None:
    rk = "demo:s-idem"
    assert record_lifecycle_closure(
        rk,
        closure_status=CLOSURE_FAILED,
        closure_reason="a",
        closure_source="t1",
    )
    assert not record_lifecycle_closure(
        rk,
        closure_status=CLOSURE_FAILED,
        closure_reason="b",
        closure_source="t2",
    )
    assert get_durable_closure(rk)["closure_reason"] == "a"


def test_record_emits_log() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        record_lifecycle_closure(
            "demo:s-log",
            closure_status=CLOSURE_RETURNED_TO_SITE,
            closure_reason="x",
            closure_source="y",
        )
    assert "[LIFECYCLE CLOSURE RECORDED]" in buf.getvalue()
