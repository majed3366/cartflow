# -*- coding: utf-8 -*-
"""
INV-001 WP-4 — Knowledge Time Authority migration tests.

Golden Comparison freezes the pre-WP-4 Knowledge window formula and requires
V2 bounds to match exactly for production-equivalent ``now`` injects.
"""
from __future__ import annotations

import ast
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import event

from extensions import db
from models import AbandonedCart, Store
from services.knowledge_insights_v1 import build_all_insights
from services.knowledge_layer_v1 import build_knowledge_report
from services.knowledge_metrics_v1 import collect_knowledge_metrics
from services.knowledge_time_authority_v1 import (
    classify_knowledge_temporal_emptiness,
    knowledge_time_contract_meta,
    resolve_knowledge_windows,
)
from services.time_authority import (
    EmptinessType,
    WindowResultStatus,
    clear_query_time_context,
    historical_replay_scope,
    simulation_scope,
)
from services.time_authority.contracts import TimezonePolicy
from services.time_authority.query_context import build_query_time_context

FIXED = datetime(2026, 5, 4, 15, 30, 45, tzinfo=timezone.utc)
JULY_NOW = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
_STORE = "kl-wp4-store"


def _legacy_knowledge_window_bounds(
    *, window_days: int, now: datetime
) -> tuple[datetime, datetime, datetime]:
    """
    Frozen pre-WP-4 formula from knowledge_metrics_v1._window_bounds.

    Do not use in production — Golden Comparison baseline only.
    """
    end = now.replace(tzinfo=None) if now.tzinfo is not None else now
    start = end - timedelta(days=max(1, int(window_days)))
    prev_start = start - timedelta(days=max(1, int(window_days)))
    return start, end, prev_start


def setup_function() -> None:
    clear_query_time_context()


def teardown_function() -> None:
    clear_query_time_context()


# --- Golden Comparison (production-equivalent bounds) ---


@pytest.mark.parametrize("window_days", [1, 7, 14, 30, 90])
@pytest.mark.parametrize(
    "now",
    [
        FIXED,
        JULY_NOW,
        datetime(2024, 2, 29, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ],
)
def test_production_golden_comparison_identical_boundaries(
    window_days: int, now: datetime
) -> None:
    legacy = _legacy_knowledge_window_bounds(window_days=window_days, now=now)
    v2 = resolve_knowledge_windows(window_days=window_days, now=now)
    assert v2.ok
    assert (v2.start, v2.end, v2.prev_start) == legacy


def test_golden_comparison_naive_and_aware_now_agree() -> None:
    aware = FIXED
    naive = FIXED.replace(tzinfo=None)
    a = resolve_knowledge_windows(window_days=7, now=aware)
    b = resolve_knowledge_windows(window_days=7, now=naive)
    assert (a.start, a.end, a.prev_start) == (b.start, b.end, b.prev_start)


# --- Semantic equivalence helpers (same now → same metrics/insights) ---


def _reset_db() -> None:
    for model in (AbandonedCart, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()


@pytest.fixture()
def kl_db():
    _reset_db()
    db.create_all()
    yield
    _reset_db()


def _seed_store_and_carts(*, first_seen: datetime, n: int = 3) -> None:
    store = Store(zid_store_id=_STORE, access_token="t", is_active=True)
    db.session.add(store)
    db.session.commit()
    fs = first_seen.replace(tzinfo=None) if first_seen.tzinfo else first_seen
    for i in range(n):
        db.session.add(
            AbandonedCart(
                store_id=store.id,
                zid_cart_id=f"wp4-cart-{_STORE}-{i}",
                recovery_session_id=f"wp4-s-{i}",
                first_seen_at=fs + timedelta(hours=i),
                last_seen_at=fs + timedelta(hours=i),
                vip_mode=False,
            )
        )
    db.session.commit()


def test_production_knowledge_candidate_and_confidence_equivalence(kl_db) -> None:
    """Same injected now ⇒ deterministic metrics + insight confidence (no dual path)."""
    _seed_store_and_carts(first_seen=FIXED - timedelta(days=1), n=5)
    m1 = collect_knowledge_metrics(db.session, _STORE, window_days=7, now=FIXED)
    m2 = collect_knowledge_metrics(db.session, _STORE, window_days=7, now=FIXED)
    assert m1.to_dict() == m2.to_dict()
    i1 = [(x.insight_key, x.confidence, x.severity) for x in build_all_insights(m1)]
    i2 = [(x.insight_key, x.confidence, x.severity) for x in build_all_insights(m2)]
    assert i1 == i2
    r1 = build_knowledge_report(db.session, _STORE, window_days=7, now=FIXED).to_dict()
    r2 = build_knowledge_report(db.session, _STORE, window_days=7, now=FIXED).to_dict()
    # generated_at uses same stamp for same now
    assert r1["generated_at"] == r2["generated_at"]
    assert r1["metrics_snapshot"] == r2["metrics_snapshot"]
    assert [
        (i["insight_key"], i["confidence"]) for i in r1["insights"]
    ] == [
        (i["insight_key"], i["confidence"]) for i in r2["insights"]
    ]


def test_production_eligibility_recommendation_suppression_stable(kl_db) -> None:
    _seed_store_and_carts(first_seen=FIXED - timedelta(days=1), n=2)
    report = build_knowledge_report(db.session, _STORE, window_days=7, now=FIXED)
    keys = {i.insight_key for i in report.insights}
    # Empty-advice / insufficient paths remain governed by existing insight builders
    assert report.ok is True
    assert keys
    for ins in report.insights:
        assert ins.confidence
        assert isinstance(ins.recommended_action_ar, str)


def test_simulation_context_selects_historical_evidence(kl_db) -> None:
    _seed_store_and_carts(first_seen=datetime(2026, 5, 2, 10, 0, 0), n=4)
    # Wall-like July inject → outside window
    july = collect_knowledge_metrics(db.session, _STORE, window_days=7, now=JULY_NOW)
    assert july.cart_count == 0
    # Simulation / as-of May → evidence appears (same DB)
    with simulation_scope(simulation_run_id="srs_wp4", start=FIXED):
        may = collect_knowledge_metrics(db.session, _STORE, window_days=7)
    assert may.cart_count == 4
    assert may.time_window is not None
    assert may.time_window.context.simulation_run_id == "srs_wp4"
    # Difference explained only by context/window
    assert july.window_end != may.window_end
    assert may.window_end.replace(tzinfo=timezone.utc) == FIXED or may.window_end == FIXED.replace(
        tzinfo=None
    )


def test_historical_replay_selects_correct_evidence(kl_db) -> None:
    _seed_store_and_carts(first_seen=datetime(2026, 5, 3, 8, 0, 0), n=2)
    with historical_replay_scope(FIXED, replay_id="hr-wp4"):
        m = collect_knowledge_metrics(db.session, _STORE, window_days=7)
    assert m.cart_count == 2
    assert m.time_window is not None
    assert m.time_window.context.replay_id == "hr-wp4"


def test_half_open_start_included_end_excluded(kl_db) -> None:
    store = Store(zid_store_id=_STORE, access_token="t", is_active=True)
    db.session.add(store)
    db.session.commit()
    tw = resolve_knowledge_windows(window_days=7, now=FIXED)
    # Exactly at start → included; exactly at end → excluded
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"wp4-start-{_STORE}",
            recovery_session_id="at-start",
            first_seen_at=tw.start,
            last_seen_at=tw.start,
            vip_mode=False,
        )
    )
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"wp4-end-{_STORE}",
            recovery_session_id="at-end",
            first_seen_at=tw.end,
            last_seen_at=tw.end,
            vip_mode=False,
        )
    )
    db.session.commit()
    m = collect_knowledge_metrics(db.session, _STORE, window_days=7, now=FIXED)
    assert m.cart_count == 1


def test_no_duplicate_adjacent_window_evidence(kl_db) -> None:
    store = Store(zid_store_id=_STORE, access_token="t", is_active=True)
    db.session.add(store)
    db.session.commit()
    tw = resolve_knowledge_windows(window_days=7, now=FIXED)
    # Boundary shared by comparison.end == primary.start — counted in primary only
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"wp4-bound-{_STORE}",
            recovery_session_id="boundary",
            first_seen_at=tw.start,
            last_seen_at=tw.start,
            vip_mode=False,
        )
    )
    db.session.commit()
    m = collect_knowledge_metrics(db.session, _STORE, window_days=7, now=FIXED)
    assert m.cart_count == 1
    assert m.prev_cart_count == 0


def test_typed_no_evidence_and_insufficient_history() -> None:
    tw = resolve_knowledge_windows(window_days=7, now=FIXED)
    none = classify_knowledge_temporal_emptiness(
        time_window=tw, has_any_history=False, has_in_window=False
    )
    assert none.emptiness_type == EmptinessType.NO_STORE_HISTORY
    oow = classify_knowledge_temporal_emptiness(
        time_window=tw, has_any_history=True, has_in_window=False
    )
    assert oow.emptiness_type == EmptinessType.OUT_OF_WINDOW
    ctx, _ = build_query_time_context(
        "testing",
        as_of=FIXED,
        timezone_policy=TimezonePolicy.STORE_LOCAL_RESERVED,
    )
    bad = resolve_knowledge_windows(window_days=7, context=ctx)
    assert bad.temporal_status == WindowResultStatus.UNSUPPORTED_TIMEZONE_POLICY
    typed = classify_knowledge_temporal_emptiness(
        time_window=bad, has_any_history=True, has_in_window=False
    )
    assert typed.emptiness_type == EmptinessType.METRIC_UNSUPPORTED


def test_provenance_preservation() -> None:
    with simulation_scope(simulation_run_id="srs_prov4", start=FIXED):
        tw = resolve_knowledge_windows(window_days=7)
    prov = tw.internal_provenance()
    assert prov["merchant_visible"] is False
    assert prov["simulation_run_id"] == "srs_prov4"
    assert prov["primary"]["recipe"] == "last_n_days"
    assert prov["comparison"]["recipe"] == "comparison_period"
    assert "authoritative_now" in prov


def test_no_direct_wall_clock_in_migrated_knowledge_modules() -> None:
    root = Path(__file__).resolve().parents[2]
    paths = [
        root / "services" / "knowledge_time_authority_v1.py",
        root / "services" / "knowledge_metrics_v1.py",
        root / "services" / "knowledge_product_metrics_v1.py",
        root / "services" / "knowledge_layer_v1.py",
        root / "services" / "knowledge_health_v1.py",
    ]
    for path in paths:
        src = path.read_text(encoding="utf-8")
        assert "datetime.now" not in src, path.name
        assert "utcnow" not in src, path.name
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("now", "utcnow"):
                if isinstance(node.value, ast.Name) and node.value.id == "datetime":
                    pytest.fail(f"wall clock in {path.name}")


def test_no_new_io_in_window_bridge() -> None:
    src = Path(__file__).resolve().parents[2]
    blob = (src / "services" / "knowledge_time_authority_v1.py").read_text(encoding="utf-8")
    assert "import sqlalchemy" not in blob.lower()
    assert "from sqlalchemy" not in blob.lower()
    assert "import requests" not in blob
    assert "import httpx" not in blob
    meta = knowledge_time_contract_meta()
    assert meta["io"] == "none"


def test_window_construction_constant_time() -> None:
    t0 = time.perf_counter()
    for _ in range(1000):
        resolve_knowledge_windows(window_days=7, now=FIXED)
    assert time.perf_counter() - t0 < 1.0


def test_index_friendly_predicates_in_metrics_source() -> None:
    root = Path(__file__).resolve().parents[2]
    metrics = (root / "services" / "knowledge_metrics_v1.py").read_text(encoding="utf-8")
    product = (root / "services" / "knowledge_product_metrics_v1.py").read_text(
        encoding="utf-8"
    )
    for blob in (metrics, product):
        assert ">=" in blob
        assert " < " in blob or ".first_seen_at <" in blob or "window_end" in blob
        # No year()/date() wrapping on timestamp columns for windowing
        assert "func.date(" not in blob
        assert "func.year(" not in blob


def test_query_count_stable_for_metrics(kl_db) -> None:
    _seed_store_and_carts(first_seen=FIXED - timedelta(days=1), n=2)
    engine = db.session.get_bind()
    counts: list[int] = []

    def _run() -> int:
        n = {"c": 0}

        def before(*_a, **_k):  # noqa: ANN001
            n["c"] += 1

        event.listen(engine, "before_cursor_execute", before)
        try:
            collect_knowledge_metrics(db.session, _STORE, window_days=7, now=FIXED)
        finally:
            event.remove(engine, "before_cursor_execute", before)
        return n["c"]

    counts.append(_run())
    counts.append(_run())
    assert counts[0] == counts[1]
    assert counts[0] > 0
    # No query explosion — Knowledge metrics remain a small fixed query set
    assert counts[0] < 40


def test_no_main_py_change_for_wp4() -> None:
    root = Path(__file__).resolve().parents[2]
    main_txt = (root / "main.py").read_text(encoding="utf-8")
    assert "knowledge_time_authority" not in main_txt
    assert "resolve_knowledge_windows" not in main_txt


def test_merchant_snapshot_omits_internal_provenance(kl_db) -> None:
    _seed_store_and_carts(first_seen=FIXED - timedelta(days=1), n=1)
    m = collect_knowledge_metrics(db.session, _STORE, window_days=7, now=FIXED)
    d = m.to_dict()
    assert "time_window" not in d
    assert "time_authority" not in d
    assert "merchant_visible" not in d
    assert m.time_window is not None
    assert m.time_window.internal_provenance()["merchant_visible"] is False


def test_legacy_private_window_helpers_removed() -> None:
    root = Path(__file__).resolve().parents[2]
    for name in ("knowledge_metrics_v1.py", "knowledge_product_metrics_v1.py"):
        src = (root / "services" / name).read_text(encoding="utf-8")
        assert "def _window_bounds" not in src
        assert "def _utc_now" not in src
