# -*- coding: utf-8 -*-
"""Guidance Eligibility Foundation V1 — Knowledge only."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import GuidanceEligibilityEvaluation, ProductSignalEvent, Store
from schema_guidance_eligibility_v1 import (
    reset_guidance_eligibility_schema_guard_for_tests,
)
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.guidance_eligibility_flag_v1 import (
    ENV_GUIDANCE_ELIGIBILITY_V1,
)
from services.product_data.knowledge_foundation_flag_v1 import (
    ENV_KNOWLEDGE_FOUNDATION_V1,
)
from services.product_data.guidance_eligibility_foundation_v1 import (
    evaluate_guidance_eligibility_v1,
    evaluate_subject_eligibility_v1,
    materialize_guidance_eligibility_v1,
    verify_guidance_eligibility_determinism_v1,
)
from services.product_data.guidance_eligibility_types_v1 import (
    STATUS_ELIGIBLE,
    STATUS_INSUFFICIENT_KNOWLEDGE,
    STATUS_PENDING_OBSERVATION,
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
    for model in (GuidanceEligibilityEvaluation, ProductSignalEvent, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_guidance_eligibility_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_GUIDANCE_ELIGIBILITY_V1, "1")
    monkeypatch.setenv(ENV_KNOWLEDGE_FOUNDATION_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"gef-{uuid.uuid4().hex[:8]}"
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


def test_pending_when_no_knowledge() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    ev = evaluate_subject_eligibility_v1(
        store_slug="demo",
        subject_type="store",
        subject_id="demo",
        statements=[],
        as_of=as_of,
        evaluated_at=as_of,
    )
    assert ev["eligibility_status"] == STATUS_PENDING_OBSERVATION
    assert "no_knowledge" in ev["blocking_conditions"]


def test_eligible_from_live_knowledge_path() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    _add_signal(
        store=store,
        identity="c|gef_a",
        observed_at=as_of - timedelta(days=2),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    report = evaluate_guidance_eligibility_v1(store, as_of=as_of)
    assert report["ok"] is True
    assert report["inputs"]["knowledge_foundation_only"] is True
    store_ev = next(e for e in report["evaluations"] if e["subject_type"] == "store")
    assert store_ev["eligibility_status"] == STATUS_ELIGIBLE
    assert store_ev["blocking_conditions"] == []
    assert store_ev["knowledge_count"] >= 2


def test_insufficient_without_trend_type() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    stmts = [
        {
            "knowledge_id": "k1",
            "knowledge_type": "evidence_quality",
            "confidence_level": "very_high",
            "valid_until": (as_of + timedelta(days=7)).isoformat(sep=" "),
        }
    ]
    ev = evaluate_subject_eligibility_v1(
        store_slug="demo",
        subject_type="store",
        subject_id="demo",
        statements=stmts,
        as_of=as_of,
        evaluated_at=as_of,
    )
    assert ev["eligibility_status"] == STATUS_INSUFFICIENT_KNOWLEDGE
    assert "missing_trend_observation" in ev["blocking_conditions"]


def test_determinism() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    _add_signal(
        store=store,
        identity="c|gef_b",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    det = verify_guidance_eligibility_determinism_v1(store, as_of=as_of)
    assert det["ok"] is True
    assert det["deterministic"] is True


def test_materialize_idempotent() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    _add_signal(
        store=store,
        identity="c|gef_c",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    m1 = materialize_guidance_eligibility_v1(store, as_of=as_of)
    m2 = materialize_guidance_eligibility_v1(store, as_of=as_of)
    assert m1["ok"] and m2["ok"]
    assert m1["canonical_fingerprint"] == m2["canonical_fingerprint"]
    n = (
        db.session.query(GuidanceEligibilityEvaluation)
        .filter(GuidanceEligibilityEvaluation.store_slug == store)
        .count()
    )
    assert n >= 1


def test_disabled_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_store()
    monkeypatch.setenv(ENV_GUIDANCE_ELIGIBILITY_V1, "0")
    out = materialize_guidance_eligibility_v1(store)
    assert out["ok"] is False
    assert out.get("skipped_disabled") is True


def test_no_guidance_content() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = evaluate_guidance_eligibility_v1(store, as_of=as_of)
    blob = str(report).lower()
    for forbidden in ("recommend", "you should", "next best", "opportunity", "guidance_text"):
        assert forbidden not in blob
