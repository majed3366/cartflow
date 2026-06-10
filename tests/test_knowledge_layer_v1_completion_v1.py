# -*- coding: utf-8 -*-
"""Knowledge Layer v1 completion conditions — KL-C1..KL-C4 tests."""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

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
from services.knowledge_health_v1 import build_knowledge_health
from services.knowledge_insights_v1 import build_all_insights
from services.knowledge_metrics_v1 import collect_knowledge_metrics
from services.knowledge_product_metrics_v1 import (
    ALLOWED_BRIDGE_TABLES,
    collect_knowledge_product_metrics,
)
from services.knowledge_purchase_attribution_v1 import count_knowledge_purchase_attribution

_ROOT = Path(__file__).resolve().parent.parent
_STORE_SLUG = "kl-completion-store"
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


def test_knowledge_health_endpoint_shape_and_fields() -> None:
    _ensure_store()
    client = TestClient(main.app)
    with mock.patch(
        "services.merchant_test_widget_store_v1.merchant_authenticated_store_slug",
        return_value=_STORE_SLUG,
    ):
        r = client.get("/api/knowledge/health")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["store_slug"] == _STORE_SLUG
    for key in (
        "knowledge_coverage",
        "evidence_coverage",
        "confidence_distribution",
        "stale_knowledge",
        "missing_inputs",
        "generated_at",
        "health_status",
        "diagnosis_codes",
        "product_foundation_bridge",
    ):
        assert key in body


def test_knowledge_health_unauthorized() -> None:
    client = TestClient(main.app)
    r = client.get("/api/knowledge/health")
    assert r.status_code == 401


def test_knowledge_health_degraded_when_attribution_unknown() -> None:
    _ensure_store()
    base = _NOW - timedelta(hours=1)
    db.session.add(
        PurchaseTruthRecord(
            recovery_key=f"{_STORE_SLUG}:organic",
            purchase_time=base,
            purchase_source="test",
            store_slug=_STORE_SLUG,
            session_id="organic",
        )
    )
    db.session.commit()

    health = build_knowledge_health(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    assert health.health_status in ("degraded", "unhealthy")
    assert "purchase_attribution_unknown" in health.missing_inputs
    assert "KL_ATTRIBUTION_UNKNOWN" in health.diagnosis_codes


def test_knowledge_health_does_not_run_insights_twice() -> None:
    _ensure_store()
    with mock.patch(
        "services.knowledge_health_v1.build_all_insights",
        wraps=build_all_insights,
    ) as spy:
        build_knowledge_health(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    assert spy.call_count == 1


def test_attribution_honesty_purchase_count_without_recovery_claim() -> None:
    _ensure_store()
    base = _NOW - timedelta(hours=1)
    db.session.add(
        PurchaseTruthRecord(
            recovery_key=f"{_STORE_SLUG}:no-recovery",
            purchase_time=base,
            purchase_source="test",
            store_slug=_STORE_SLUG,
            session_id="no-recovery",
        )
    )
    db.session.commit()

    counts = count_knowledge_purchase_attribution(
        db.session,
        _STORE_SLUG,
        window_start=_NOW - timedelta(days=7),
        window_end=_NOW + timedelta(hours=1),
    )
    assert counts.purchase_count == 1
    assert counts.attributed_recovery_purchase_count == 0
    assert counts.purchase_attribution_unknown_count == 1

    metrics = collect_knowledge_metrics(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    assert metrics.purchase_count == 1
    assert metrics.attributed_recovery_purchase_count == 0
    assert "recovery_purchases" not in metrics.to_dict()


def test_attribution_honesty_with_recovery_evidence() -> None:
    _ensure_store()
    base = _NOW - timedelta(hours=2)
    for st in ("sent_real", "sent_real", "mock_sent"):
        db.session.add(
            CartRecoveryLog(
                store_slug=_STORE_SLUG,
                session_id="s1",
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
            created_at=base + timedelta(minutes=30),
        )
    )
    db.session.add(
        PurchaseTruthRecord(
            recovery_key=f"{_STORE_SLUG}:s1",
            purchase_time=base + timedelta(hours=1),
            purchase_source="test",
            store_slug=_STORE_SLUG,
            session_id="s1",
        )
    )
    db.session.commit()

    metrics = collect_knowledge_metrics(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    assert metrics.purchase_count == 1
    assert metrics.attributed_recovery_purchase_count >= 1

    insights = build_all_insights(metrics)
    recovery = next(i for i in insights if i.insight_key == "recovery_activity_summary")
    assert recovery.evidence["purchase_count"] == 1
    assert recovery.evidence["attributed_recovery_purchase_count"] >= 1
    assert "purchases" not in recovery.evidence


def test_product_bridge_reads_allowed_tables_only() -> None:
    src = (_ROOT / "services" / "knowledge_product_metrics_v1.py").read_text(encoding="utf-8")
    assert "raw_payload" not in src
    assert "line_items_from_abandoned_cart" not in src
    assert "recovery_product_context" not in src
    assert "assess_foundation_health" in src

    bridge = collect_knowledge_product_metrics(
        db.session,
        _STORE_SLUG,
        window_days=7,
        now=_NOW,
    )
    assert set(bridge.source_tables) == set(ALLOWED_BRIDGE_TABLES)


def test_product_bridge_attached_to_health() -> None:
    _ensure_store()
    health = build_knowledge_health(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    bridge = health.product_foundation_bridge
    assert bridge.get("bridge_module") == "knowledge_product_metrics_v1"
    assert bridge.get("source_tables") == sorted(ALLOWED_BRIDGE_TABLES)


def test_vip_isolation_normal_lane_excludes_vip_carts() -> None:
    store = _ensure_store()
    base = _NOW - timedelta(days=1)
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id="normal-cart",
            recovery_session_id="normal-sess",
            vip_mode=False,
            first_seen_at=base,
            last_seen_at=base,
        )
    )
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id="vip-cart",
            recovery_session_id="vip-sess",
            vip_mode=True,
            first_seen_at=base,
            last_seen_at=base,
        )
    )
    db.session.add(
        CartRecoveryReason(
            store_slug=_STORE_SLUG,
            session_id="normal-sess",
            reason="price_high",
            created_at=base,
        )
    )
    db.session.add(
        CartRecoveryReason(
            store_slug=_STORE_SLUG,
            session_id="vip-sess",
            reason="price_high",
            created_at=base,
        )
    )
    db.session.add(
        CartRecoveryLog(
            store_slug=_STORE_SLUG,
            session_id="normal-sess",
            status="sent_real",
            message="m",
            created_at=base,
        )
    )
    db.session.add(
        CartRecoveryLog(
            store_slug=_STORE_SLUG,
            session_id="vip-sess",
            status="sent_real",
            message="m",
            created_at=base,
        )
    )
    db.session.commit()

    metrics = collect_knowledge_metrics(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    assert metrics.cart_count == 1
    assert metrics.vip_cart_count == 1
    assert metrics.hesitation_total == 1
    assert metrics.recovery_messages_sent == 1
    assert metrics.vip_evidence["isolated"] is True
    assert metrics.vip_evidence["cart_count"] == 1
    assert metrics.vip_evidence["hesitation_total"] == 1
    assert metrics.vip_evidence["recovery_messages_sent"] == 1


def test_vip_merchant_alert_logs_do_not_contaminate_normal_recovery() -> None:
    _ensure_store()
    base = _NOW - timedelta(hours=1)
    db.session.add(
        CartRecoveryLog(
            store_slug=_STORE_SLUG,
            session_id="vip-alert",
            status="vip_merchant_alert_accepted",
            reason_tag="vip_merchant_alert",
            message="alert",
            created_at=base,
        )
    )
    db.session.commit()

    metrics = collect_knowledge_metrics(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    assert metrics.recovery_messages_sent == 0
    assert metrics.vip_evidence["merchant_alert_logs"] == 1


def test_mixed_vip_non_vip_store_health_still_reports() -> None:
    store = _ensure_store()
    base = _NOW - timedelta(days=1)
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id="mix-normal",
            recovery_session_id="mix-n",
            vip_mode=False,
            first_seen_at=base,
            last_seen_at=base,
        )
    )
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id="mix-vip",
            recovery_session_id="mix-v",
            vip_mode=True,
            first_seen_at=base,
            last_seen_at=base,
        )
    )
    db.session.commit()

    health = build_knowledge_health(db.session, _STORE_SLUG, window_days=7, now=_NOW)
    assert health.ok is True
    assert health.metrics_snapshot["cart_count"] == 1
    assert health.metrics_snapshot["vip_cart_count"] == 1
    assert "vip_isolation_failed" not in health.missing_inputs


def test_architecture_health_route_not_in_main() -> None:
    main_src = (_ROOT / "main.py").read_text(encoding="utf-8")
    assert "build_knowledge_health" not in main_src
    assert "knowledge_health_v1" not in main_src

    route_src = (_ROOT / "routes" / "knowledge.py").read_text(encoding="utf-8")
    assert "build_knowledge_health" in route_src
    assert "/health" in route_src


def test_knowledge_metrics_module_has_no_raw_payload_reads() -> None:
    for mod in (
        "services.knowledge_metrics_v1",
        "services.knowledge_insights_v1",
        "services.knowledge_layer_v1",
        "services.knowledge_health_v1",
    ):
        import importlib

        module = importlib.import_module(mod)
        src = inspect.getsourcefile(module)
        assert src
        text = Path(src).read_text(encoding="utf-8")
        assert "raw_payload" not in text
