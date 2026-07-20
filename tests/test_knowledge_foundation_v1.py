# -*- coding: utf-8 -*-
"""Knowledge Foundation V1 — Evidence Confidence only."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import KnowledgeStatement, ProductSignalEvent, Store
from schema_knowledge_foundation_v1 import (
    reset_knowledge_foundation_schema_guard_for_tests,
)
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.knowledge_foundation_flag_v1 import (
    ENV_KNOWLEDGE_FOUNDATION_V1,
)
from services.product_data.knowledge_foundation_types_v1 import (
    KNOWLEDGE_TYPE_EVIDENCE_QUALITY,
    KNOWLEDGE_TYPE_METRIC_TREND,
    trend_statement,
)
from services.product_data.knowledge_foundation_v1 import (
    generate_knowledge_v1,
    materialize_knowledge_v1,
    verify_knowledge_determinism_v1,
)
from services.product_data.product_signal_types_v1 import (
    FAMILY_PRODUCT_CART_ACTIVITY,
    SIGNAL_PRODUCT_CART_ADDED,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (KnowledgeStatement, ProductSignalEvent, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_knowledge_foundation_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_KNOWLEDGE_FOUNDATION_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"kf-{uuid.uuid4().hex[:8]}"
    store = Store(zid_store_id=slug, vip_cart_threshold=1000)
    db.session.add(store)
    db.session.commit()
    register_store_identity_alias(
        store_id=int(store.id),
        alias_kind=ALIAS_KIND_CARTFLOW_ZID,
        alias_value=slug,
        platform="cartflow",
    )
    return slug


def _add_signal(
    *,
    store: str,
    identity: str,
    observed_at: datetime,
    dedup: str,
) -> None:
    db.session.add(
        ProductSignalEvent(
            store_slug=store,
            session_id=f"s-{dedup[-8:]}",
            cart_id=f"c-{dedup[-6:]}",
            recovery_key=None,
            stable_identity_key=identity,
            identity_tier="C",
            product_id="p1",
            signal_family=FAMILY_PRODUCT_CART_ACTIVITY,
            signal_type=SIGNAL_PRODUCT_CART_ADDED,
            observed_at=observed_at,
            source="cart_state_sync",
            evidence_ref_type="session",
            evidence_ref_id=f"s-{dedup[-8:]}",
            dedup_hash=dedup,
        )
    )
    db.session.commit()


def test_trend_template() -> None:
    s = trend_statement("cart_added_count", "newly_appeared", "d7")
    assert s == "Cart additions have newly appeared during the last 7 days."


def test_generate_references_confidence() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 10, 0, 0)
    _add_signal(
        store=store,
        identity="c|kf_a",
        observed_at=as_of - timedelta(days=2),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    report = generate_knowledge_v1(store, as_of=as_of)
    assert report["ok"] is True
    assert report["inputs"]["evidence_confidence_only"] is True
    assert report["statement_count"] >= 1
    assert all(s.get("evidence_confidence_id") for s in report["statements"])
    quality = [
        s
        for s in report["statements"]
        if s["knowledge_type"] == KNOWLEDGE_TYPE_EVIDENCE_QUALITY
        and s["subject_type"] == "store"
    ]
    assert quality
    assert "Evidence quality is" in quality[0]["statement"]
    # Demo-like high confidence should yield trend observations
    trends = [
        s for s in report["statements"] if s["knowledge_type"] == KNOWLEDGE_TYPE_METRIC_TREND
    ]
    if trends:
        assert "during" in trends[0]["statement"]


def test_determinism() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 10, 0, 0)
    _add_signal(
        store=store,
        identity="c|kf_b",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    det = verify_knowledge_determinism_v1(store, as_of=as_of)
    assert det["ok"] is True
    assert det["deterministic"] is True


def test_materialize_idempotent() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 10, 0, 0)
    _add_signal(
        store=store,
        identity="c|kf_c",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    m1 = materialize_knowledge_v1(store, as_of=as_of)
    m2 = materialize_knowledge_v1(store, as_of=as_of)
    assert m1["ok"] and m2["ok"]
    assert m1["canonical_fingerprint"] == m2["canonical_fingerprint"]
    n = (
        db.session.query(KnowledgeStatement)
        .filter(KnowledgeStatement.store_slug == store)
        .count()
    )
    assert n >= 1


def test_disabled_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_store()
    monkeypatch.setenv(ENV_KNOWLEDGE_FOUNDATION_V1, "0")
    out = materialize_knowledge_v1(store)
    assert out["ok"] is False
    assert out.get("skipped_disabled") is True


def test_no_forbidden_semantics() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 10, 0, 0)
    report = generate_knowledge_v1(store, as_of=as_of)
    blob = str(report).lower()
    for forbidden in (
        "recommend",
        "should do",
        "next best",
        "opportunity",
        "health_score",
        "guidance",
    ):
        assert forbidden not in blob
