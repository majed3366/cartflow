# -*- coding: utf-8 -*-
"""Integration Health Foundation v1 tests."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pytest

from extensions import db
from models import (
    AbandonedCart,
    CartLineSnapshot,
    CartRecoveryReason,
    RecoveryEvent,
    RecoveryTruthTimelineEvent,
    Store,
)
from services.admin_operational_health_json_v1 import build_admin_operational_health_json
from services.integration_health_v1 import (
    DIAG_META_PRODUCTION_BLOCKED,
    DIAG_PLATFORM_ADAPTER_SCAFFOLD,
    DIAG_WIDGET_RUNTIME_MISSING,
    DIAG_ZID_CART_EVENTS_MISSING,
    DIAG_ZID_NOT_CONNECTED,
    DIAG_ZID_OAUTH_MISSING,
    DIAG_ZID_WEBHOOK_STALE,
    INTEGRATION_PATH_LEGACY_ZID,
    STATUS_DISCONNECTED,
    STATUS_HEALTHY,
    STATUS_NOT_IMPLEMENTED,
    STATUS_PRODUCTION_BLOCKED,
    build_integration_health,
)

_ROOT = Path(__file__).resolve().parent.parent
_STORE = "ih-test-store"
_NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def _reset() -> None:
    for model in (
        RecoveryTruthTimelineEvent,
        CartLineSnapshot,
        CartRecoveryReason,
        RecoveryEvent,
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
    _reset()
    db.create_all()
    yield
    _reset()


def _store(*, token: str = "", widget_status: str | None = None) -> Store:
    row = Store(
        zid_store_id=_STORE,
        access_token=token,
        is_active=True,
        widget_installation_status=widget_status,
        connected_at=_NOW.replace(tzinfo=None) if token else None,
    )
    db.session.add(row)
    db.session.commit()
    return row


def _required_keys(record: dict) -> None:
    for key in (
        "name",
        "status",
        "diagnosis_codes",
        "action_owner",
        "last_success_at",
        "last_failure_at",
        "evidence",
        "health_source",
    ):
        assert key in record


def test_healthy_zid_store() -> None:
    store = _store(token="oauth-token", widget_status="installed")
    base = _NOW - timedelta(days=1)
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id="c1",
            recovery_session_id="s1",
            vip_mode=False,
            first_seen_at=base.replace(tzinfo=None),
            last_seen_at=base.replace(tzinfo=None),
        )
    )
    db.session.add(
        CartLineSnapshot(
            store_slug=_STORE,
            session_id="s1",
            cart_id="c1",
            capture_source="widget",
            capture_confidence="high",
            content_hash="h1",
            captured_at=base.replace(tzinfo=None),
        )
    )
    db.session.add(
        RecoveryEvent(
            store_id=store.id,
            event_type="zid.webhook",
            payload="{}",
            created_at=base.replace(tzinfo=None),
        )
    )
    os.environ["ZID_WEBHOOK_SECRET"] = "test-secret"
    db.session.commit()

    with mock.patch(
        "services.integration_health_v1._widget_rows_for_stores",
        return_value={
            _STORE: {
                "store_slug": _STORE,
                "status": "healthy",
                "issue_kinds": [],
            }
        },
    ):
        health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)
    store_row = health["stores"][0]
    _required_keys(store_row["zid"])
    assert store_row["zid"]["health_source"] == INTEGRATION_PATH_LEGACY_ZID
    assert store_row["zid"]["evidence"]["integration_path"] == INTEGRATION_PATH_LEGACY_ZID
    assert store_row["zid"]["status"] == STATUS_HEALTHY
    assert DIAG_ZID_OAUTH_MISSING not in store_row["zid"]["diagnosis_codes"]


def test_zid_disconnected() -> None:
    _store(token="")
    health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)
    zid = health["stores"][0]["zid"]
    assert zid["status"] == STATUS_DISCONNECTED
    assert DIAG_ZID_OAUTH_MISSING in zid["diagnosis_codes"]
    assert health["platform"]["zid"]["status"] == STATUS_DISCONNECTED
    assert DIAG_ZID_NOT_CONNECTED in health["platform"]["zid"]["diagnosis_codes"]


def test_zid_webhook_stale() -> None:
    _store(token="oauth")
    os.environ["ZID_WEBHOOK_SECRET"] = "secret"
    health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)
    assert DIAG_ZID_WEBHOOK_STALE in health["platform"]["zid"]["diagnosis_codes"]


def test_widget_runtime_missing() -> None:
    _store(token="oauth", widget_status="installed")
    with mock.patch(
        "services.integration_health_v1._widget_rows_for_stores",
        return_value={
            _STORE: {
                "store_slug": _STORE,
                "status": "warning",
                "issue_kinds": ["runtime_beacon_missing"],
            }
        },
    ):
        health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)
    assert DIAG_WIDGET_RUNTIME_MISSING in health["stores"][0]["zid"]["diagnosis_codes"]
    assert DIAG_WIDGET_RUNTIME_MISSING in health["widget_event_flow"]["diagnosis_codes"]


def test_meta_production_blocked() -> None:
    health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)
    meta = health["platform"]["meta_production"]
    _required_keys(meta)
    assert meta["status"] == STATUS_PRODUCTION_BLOCKED
    assert DIAG_META_PRODUCTION_BLOCKED in meta["diagnosis_codes"]
    assert meta["status"] != STATUS_DISCONNECTED


def test_twilio_ready_meta_blocked_independently() -> None:
    with mock.patch(
        "services.cartflow_provider_readiness.get_twilio_readiness",
        return_value={
            "provider": "twilio",
            "configured": True,
            "ready": True,
            "ready_env_credentials": True,
            "failure_class": "ok",
            "mode": "sandbox",
        },
    ), mock.patch(
        "services.cartflow_provider_readiness.get_meta_readiness",
        return_value={"configured": False, "ready": False, "note": "meta_path_not_active"},
    ):
        health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)

    wa = health["platform"]["whatsapp_architecture"]
    meta = health["platform"]["meta_production"]
    assert wa["evidence"]["twilio_send_ready"] is True
    assert meta["status"] == STATUS_PRODUCTION_BLOCKED
    assert DIAG_META_PRODUCTION_BLOCKED in meta["diagnosis_codes"]


def test_salla_scaffold_only() -> None:
    health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)
    salla = health["platform"]["salla"]
    assert salla["status"] == STATUS_NOT_IMPLEMENTED
    assert DIAG_PLATFORM_ADAPTER_SCAFFOLD in salla["diagnosis_codes"]
    assert salla["status"] not in ("failed", "broken", "degraded")


def test_shopify_scaffold_only() -> None:
    health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)
    shopify = health["platform"]["shopify"]
    assert shopify["status"] == STATUS_NOT_IMPLEMENTED
    assert DIAG_PLATFORM_ADAPTER_SCAFFOLD in shopify["diagnosis_codes"]


def test_per_store_isolation() -> None:
    good = Store(
        zid_store_id="good-store",
        access_token="good-token",
        is_active=True,
        connected_at=_NOW.replace(tzinfo=None),
        widget_installation_status="installed",
        widget_last_seen_at=_NOW.replace(tzinfo=None),
    )
    bad = Store(zid_store_id="bad-store", access_token="", is_active=True)
    db.session.add(good)
    db.session.flush()
    db.session.add(bad)
    base = _NOW - timedelta(hours=1)
    db.session.add(
        AbandonedCart(
            store_id=good.id,
            zid_cart_id="gc1",
            recovery_session_id="gs1",
            first_seen_at=base.replace(tzinfo=None),
            last_seen_at=base.replace(tzinfo=None),
        )
    )
    db.session.add(
        CartLineSnapshot(
            store_slug="good-store",
            session_id="gs1",
            cart_id="gc1",
            capture_source="widget",
            capture_confidence="high",
            content_hash="gh1",
            captured_at=base.replace(tzinfo=None),
        )
    )
    db.session.commit()

    def _mock_widget_rows(stores: list[Store]) -> dict[str, dict]:
        return {
            (s.zid_store_id or ""): {
                "store_slug": s.zid_store_id or "",
                "status": "healthy",
                "issue_kinds": [],
            }
            for s in stores
        }

    with mock.patch(
        "services.integration_health_v1._widget_rows_for_stores",
        side_effect=_mock_widget_rows,
    ):
        health = build_integration_health(window_days=7, now=_NOW)

    by_slug = {r["store_slug"]: r for r in health["stores"]}
    assert by_slug["good-store"]["zid"]["status"] == STATUS_HEALTHY
    assert by_slug["bad-store"]["zid"]["status"] == STATUS_DISCONNECTED


def test_operational_health_integrations_block() -> None:
    _store(token="tok")
    payload = build_admin_operational_health_json(store_slug=_STORE)
    assert "integrations" in payload
    assert payload["integrations"]["version"] == "integration_health_v1"
    assert "platform" in payload["integrations"]
    assert "stores" in payload["integrations"]


def test_composer_failure_isolation() -> None:
    _store(token="tok")
    with mock.patch(
        "services.integration_health_v1._build_store_zid_health",
        side_effect=RuntimeError("probe exploded"),
    ):
        health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)
    assert health["ok"] is True
    assert health["stores"][0]["zid"]["status"] == "unknown"
    assert "error" in health["stores"][0]["zid"]["evidence"]


def test_no_duplicated_truth_sources() -> None:
    src = (_ROOT / "services" / "integration_health_v1.py").read_text(encoding="utf-8")
    forbidden = (
        "db.session.add",
        "db.session.commit",
        "upsert_abandoned_cart",
        "ingest_purchase_truth",
        "send_whatsapp",
        "build_knowledge_report",
    )
    for token in forbidden:
        assert token not in src


def test_architecture_composer_not_in_main() -> None:
    main_src = (_ROOT / "main.py").read_text(encoding="utf-8")
    assert "integration_health_v1" not in main_src
    assert "build_integration_health" not in main_src

    admin_src = (_ROOT / "services" / "admin_operational_health_json_v1.py").read_text(
        encoding="utf-8"
    )
    assert "build_integration_health" in admin_src


def test_zid_cart_events_missing_when_connected() -> None:
    _store(token="oauth-token")
    health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)
    assert DIAG_ZID_CART_EVENTS_MISSING in health["stores"][0]["zid"]["diagnosis_codes"]


def test_signal_classes_separated() -> None:
    _store(token="tok")
    base = _NOW - timedelta(hours=2)
    db.session.add(
        CartRecoveryReason(
            store_slug=_STORE,
            session_id="s1",
            reason="price_high",
            created_at=base.replace(tzinfo=None),
        )
    )
    db.session.add(
        RecoveryTruthTimelineEvent(
            recovery_key=f"{_STORE}:s1",
            store_slug=_STORE,
            session_id="s1",
            status="checkout_started",
            source="test",
            created_at=base.replace(tzinfo=None),
        )
    )
    db.session.commit()

    health = build_integration_health(store_slug=_STORE, window_days=7, now=_NOW)
    signals = health["signal_readiness"]
    assert signals["hesitation"]["name"] == "hesitation"
    assert signals["checkout_friction"]["name"] == "checkout_friction"
    assert signals["payment_failure"]["name"] == "payment_failure"
    assert signals["purchase_confirmation"]["name"] == "purchase_confirmation"
    assert signals["hesitation"]["evidence"]["event_count"] == 1
    assert signals["checkout_friction"]["evidence"]["signal_count"] == 1
    assert signals["payment_failure"]["status"] == STATUS_NOT_IMPLEMENTED
