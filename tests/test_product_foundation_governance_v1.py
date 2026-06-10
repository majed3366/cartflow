# -*- coding: utf-8 -*-
"""Product Foundation Governance v1 — growth, query cost, archive policy tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

import main
from extensions import db
from models import CartLineSnapshot, Store
from schema_cart_line_snapshots_v1 import reset_cart_line_snapshots_schema_guard_for_tests
from schema_product_catalog_v1 import reset_product_catalog_schema_guard_for_tests
from schema_product_hesitation_mapping_v1 import (
    reset_product_hesitation_mapping_schema_guard_for_tests,
)
from schema_product_purchase_mapping_v1 import (
    reset_product_purchase_mapping_schema_guard_for_tests,
)
from services.product_data.product_foundation_archive_policy_v1 import (
    ARCHIVE_AFTER_CART_LINE_SNAPSHOTS_DAYS,
    archive_policy_summary,
)
from services.product_data.product_foundation_governance_v1 import (
    build_product_foundation_governance_report,
)
from services.product_data.product_foundation_growth_v1 import (
    GROWTH_HIGH,
    GROWTH_NORMAL,
    GROWTH_WATCH,
    assess_table_growth,
    classify_growth_status,
)
from services.product_data.product_foundation_query_cost_v1 import (
    QUERY_COST_FAILED,
    QUERY_COST_OK,
    QUERY_COST_SLOW,
    run_timed_read,
)

_ROOT = Path(__file__).resolve().parent.parent
_STORE_SLUG = "gov-test-store"
_NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def _reset_db() -> None:
    for model in (CartLineSnapshot, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_cart_line_snapshots_schema_guard_for_tests()
    reset_product_catalog_schema_guard_for_tests()
    reset_product_hesitation_mapping_schema_guard_for_tests()
    reset_product_purchase_mapping_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db() -> None:
    _reset_db()
    db.create_all()
    yield
    _reset_db()


def _ensure_store(slug: str = _STORE_SLUG) -> Store:
    row = Store(zid_store_id=slug, access_token="t", is_active=True)
    db.session.add(row)
    db.session.commit()
    return row


def _snapshot(
    slug: str,
    *,
    days_ago: int,
    suffix: str | None = None,
) -> None:
    when = (_NOW - timedelta(days=days_ago)).replace(tzinfo=None)
    sid = f"s_{suffix or uuid.uuid4().hex[:8]}"
    snap = CartLineSnapshot(
        store_slug=slug,
        session_id=sid,
        cart_id=f"c_{sid}",
        product_id="p1",
        name="Widget",
        unit_price=10.0,
        quantity=1,
        captured_at=when,
        capture_source="cart_state_sync",
        capture_confidence="high",
        content_hash=uuid.uuid4().hex,
    )
    db.session.add(snap)
    db.session.commit()


class TestArchivePolicy:
    def test_policy_summary_is_read_only_constants(self) -> None:
        summary = archive_policy_summary()
        assert summary["execution_enabled"] is False
        assert summary["principle"] == "archive_before_delete"
        tables = {t["table"]: t for t in summary["tables"]}
        assert tables["cart_line_snapshots"]["archive_after_days"] == (
            ARCHIVE_AFTER_CART_LINE_SNAPSHOTS_DAYS
        )
        assert tables["product_catalog_entries"]["archive_after_days"] is None


class TestQueryCostHelper:
    def test_run_timed_read_ok(self) -> None:
        result, cost = run_timed_read(
            "test_ok",
            lambda: [1, 2, 3],
            row_count_from=len,
        )
        assert result == [1, 2, 3]
        assert cost.status == QUERY_COST_OK
        assert cost.row_count == 3

    def test_run_timed_read_slow(self) -> None:
        def _slow() -> list[int]:
            import time

            time.sleep(0.01)
            return [1]

        result, cost = run_timed_read(
            "test_slow", _slow, slow_threshold_ms=1.0
        )
        assert result == [1]
        assert cost.status == QUERY_COST_SLOW

    def test_run_timed_read_failed(self) -> None:
        def _boom() -> None:
            raise RuntimeError("read failed")

        result, cost = run_timed_read("test_fail", _boom)
        assert result is None
        assert cost.status == QUERY_COST_FAILED


class TestGrowthMetrics:
    def test_classify_growth_status_thresholds(self) -> None:
        assert classify_growth_status(rows_last_7_days=0, rows_last_30_days=0) == GROWTH_NORMAL
        assert classify_growth_status(rows_last_7_days=100, rows_last_30_days=0) == GROWTH_WATCH
        assert classify_growth_status(rows_last_7_days=1000, rows_last_30_days=0) == GROWTH_HIGH

    def test_assess_table_growth_counts(self) -> None:
        _ensure_store()
        _snapshot(_STORE_SLUG, days_ago=0)
        _snapshot(_STORE_SLUG, days_ago=3)
        _snapshot(_STORE_SLUG, days_ago=20)

        metrics = assess_table_growth(
            db.session, _STORE_SLUG, "cart_line_snapshots", now=_NOW
        )
        assert metrics.total_rows == 3
        assert metrics.rows_added_today == 1
        assert metrics.rows_added_last_7_days == 2
        assert metrics.rows_added_last_30_days == 3
        assert metrics.growth_status == GROWTH_NORMAL
        assert metrics.oldest_row_at is not None
        assert metrics.newest_row_at is not None


class TestGovernanceReport:
    def test_build_report_shape_and_query_costs(self) -> None:
        _ensure_store()
        _snapshot(_STORE_SLUG, days_ago=1)

        report = build_product_foundation_governance_report(
            db.session, _STORE_SLUG, now=_NOW
        )
        assert report["ok"] is True
        assert report["store_slug"] == _STORE_SLUG
        assert "cart_line_snapshots" in report["tables"]
        assert report["tables"]["cart_line_snapshots"]["total_rows"] == 1
        assert len(report["query_costs"]) == 4
        assert report["query_costs"][0]["query_name"].startswith("growth_")
        assert report["archive_policy"]["execution_enabled"] is False

    def test_governance_performs_no_writes(self) -> None:
        _ensure_store()
        with mock.patch.object(db.session, "add", wraps=db.session.add) as add_mock:
            with mock.patch.object(
                db.session, "commit", wraps=db.session.commit
            ) as commit_mock:
                build_product_foundation_governance_report(
                    db.session, _STORE_SLUG, now=_NOW
                )
                assert add_mock.call_count == 0
                assert commit_mock.call_count == 0


class TestGovernanceApi:
    def test_api_unauthorized(self) -> None:
        client = TestClient(main.app)
        r = client.get("/api/product-data/governance/health")
        assert r.status_code == 401

    def test_api_authenticated_response(self) -> None:
        _ensure_store()
        _snapshot(_STORE_SLUG, days_ago=0)
        client = TestClient(main.app)
        with mock.patch(
            "services.merchant_test_widget_store_v1.merchant_authenticated_store_slug",
            return_value=_STORE_SLUG,
        ):
            r = client.get("/api/product-data/governance/health")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["store_slug"] == _STORE_SLUG
        assert "tables" in body
        assert "query_costs" in body
        assert "archive_policy" in body

    def test_route_registered_without_main_py_changes(self) -> None:
        paths = {getattr(r, "path", "") for r in main.app.routes}
        assert "/api/product-data/governance/health" in paths
        main_src = (_ROOT / "main.py").read_text(encoding="utf-8")
        assert "product_foundation_governance" not in main_src
