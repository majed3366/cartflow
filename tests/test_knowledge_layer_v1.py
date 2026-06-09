# -*- coding: utf-8 -*-
"""Knowledge Layer v1 — standalone foundation tests."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from extensions import db
from models import (
    AbandonedCart,
    CartRecoveryLog,
    CartRecoveryReason,
    PurchaseTruthRecord,
    RecoveryTruthTimelineEvent,
    Store,
)
from services.knowledge_layer_v1 import build_knowledge_report
from services.knowledge_types_v1 import (
    CONFIDENCE_INSUFFICIENT,
    FORBIDDEN_ADVICE_PHRASES,
)

_ROOT = Path(__file__).resolve().parent.parent
_STORE_SLUG = "kl-test-store"
_NOW = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)


def _reset_db() -> None:
    for model in (
        RecoveryTruthTimelineEvent,
        PurchaseTruthRecord,
        CartRecoveryLog,
        CartRecoveryReason,
        AbandonedCart,
        Store,
    ):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()


@pytest.fixture(autouse=True)
def _isolate_db() -> None:
    _reset_db()
    db.create_all()
    yield
    _reset_db()


def _ensure_store(*, slug: str = _STORE_SLUG) -> Store:
    row = Store(zid_store_id=slug, access_token="t", is_active=True)
    db.session.add(row)
    db.session.commit()
    return row


def _report_text(report_dict: dict) -> str:
    return json.dumps(report_dict, ensure_ascii=False)


def test_empty_store_returns_insufficient_data_no_fake_advice() -> None:
    report = build_knowledge_report(
        db.session, "empty-store-xyz", window_days=7, now=_NOW
    )
    assert report.ok is True
    assert report.insights
    keys = {i.insight_key for i in report.insights}
    assert "traffic_visitor_unavailable" in keys
    assert "conversion_funnel_gaps" in keys or "conversion_no_carts" in keys

    blob = _report_text(report.to_dict())
    for phrase in FORBIDDEN_ADVICE_PHRASES:
        assert phrase not in blob

    insufficient = [i for i in report.insights if i.confidence == CONFIDENCE_INSUFFICIENT]
    assert len(insufficient) >= 3


def test_hesitation_reasons_top_and_distribution() -> None:
    _ensure_store()
    base = _NOW - timedelta(days=1)
    for idx, reason in enumerate(
        ("price_high", "price_high", "shipping_delay", "quality", "other")
    ):
        db.session.add(
            CartRecoveryReason(
                store_slug=_STORE_SLUG,
                session_id=f"s-{idx}",
                reason=reason,
                created_at=base + timedelta(hours=idx),
            )
        )
    db.session.commit()

    report = build_knowledge_report(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    keys = {i.insight_key for i in report.insights}
    assert "hesitation_top_reason" in keys
    assert "hesitation_distribution" in keys

    top = next(i for i in report.insights if i.insight_key == "hesitation_top_reason")
    assert top.evidence["top_reason"] == "price"
    assert top.evidence["top_count"] == 2
    assert top.evidence["distribution"]["price"] == 2
    assert "price" in top.message_ar
    assert top.confidence != CONFIDENCE_INSUFFICIENT


def test_recovery_activity_counts_and_sample_gate() -> None:
    _ensure_store()
    base = _NOW - timedelta(hours=2)
    for st in ("sent_real", "sent_real", "mock_sent"):
        db.session.add(
            CartRecoveryLog(
                store_slug=_STORE_SLUG,
                session_id=f"rs-{st}",
                status=st,
                message="m",
                created_at=base,
            )
        )
    db.session.add(
        RecoveryTruthTimelineEvent(
            recovery_key=f"{_STORE_SLUG}:s1",
            store_slug=_STORE_SLUG,
            session_id="s1",
            status="customer_reply",
            source="test",
            created_at=base,
        )
    )
    db.session.add(
        PurchaseTruthRecord(
            recovery_key=f"{_STORE_SLUG}:s1",
            purchase_time=base,
            purchase_source="test",
            store_slug=_STORE_SLUG,
            session_id="s1",
        )
    )
    db.session.commit()

    report = build_knowledge_report(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    recovery = next(
        i for i in report.insights if i.insight_key == "recovery_activity_summary"
    )
    assert recovery.evidence["messages_sent"] == 3
    assert recovery.evidence["replies"] == 1
    assert recovery.evidence["purchases"] == 1
    assert recovery.confidence != CONFIDENCE_INSUFFICIENT


def test_recovery_insufficient_sample_when_too_few_events() -> None:
    _ensure_store()
    db.session.add(
        CartRecoveryLog(
            store_slug=_STORE_SLUG,
            session_id="solo",
            status="sent_real",
            message="m",
            created_at=_NOW - timedelta(hours=1),
        )
    )
    db.session.commit()

    report = build_knowledge_report(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    keys = {i.insight_key for i in report.insights}
    assert "recovery_insufficient_sample" in keys


def test_missing_visitor_data_traffic_insight() -> None:
    report = build_knowledge_report(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    traffic = next(
        i for i in report.insights if i.insight_key == "traffic_visitor_unavailable"
    )
    assert traffic.confidence == CONFIDENCE_INSUFFICIENT
    assert "visitor" in traffic.evidence.get("note", "") or "زوار" in traffic.message_ar
    assert traffic.evidence["visitor_data_available"] is False


def test_safety_wording_no_marketing_advice() -> None:
    _ensure_store()
    base = _NOW - timedelta(days=1)
    db.session.add(
        CartRecoveryReason(
            store_slug=_STORE_SLUG,
            session_id="s-price",
            reason="price_high",
            created_at=base,
        )
    )
    db.session.commit()

    report = build_knowledge_report(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    blob = _report_text(report.to_dict())
    for phrase in FORBIDDEN_ADVICE_PHRASES:
        assert phrase not in blob


def test_architecture_no_business_logic_in_main() -> None:
    main_src = (_ROOT / "main.py").read_text(encoding="utf-8")
    assert "knowledge_layer_v1" not in main_src
    assert "knowledge_insights_v1" not in main_src
    assert "knowledge_metrics_v1" not in main_src
    assert "build_knowledge_report" not in main_src

    route_src = (_ROOT / "routes" / "knowledge.py").read_text(encoding="utf-8")
    assert "from services.knowledge_layer_v1 import build_knowledge_report" in route_src
    assert "db.session.add" not in route_src
    assert "db.session.commit" not in route_src


def test_api_route_unauthorized_without_auth() -> None:
    client = TestClient(main.app)
    r = client.get("/api/knowledge/report")
    assert r.status_code == 401


def test_startup_import_and_route_registered() -> None:
    from main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/knowledge/report" in paths
    assert len(app.routes) >= 1
