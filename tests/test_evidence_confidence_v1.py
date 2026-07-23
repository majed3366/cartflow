# -*- coding: utf-8 -*-
"""Evidence Confidence Foundation V1 — Evidence Assembly only."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import EvidenceConfidenceEvaluation, ProductSignalEvent, Store
from schema_evidence_confidence_v1 import reset_evidence_confidence_schema_guard_for_tests
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.evidence_confidence_flag_v1 import (
    ENV_EVIDENCE_CONFIDENCE_V1,
)
from services.product_data.evidence_confidence_foundation_v1 import (
    evaluate_evidence_confidence_v1,
    materialize_evidence_confidence_v1,
    verify_evidence_confidence_determinism_v1,
)
from services.product_data.evidence_confidence_types_v1 import confidence_level_for_score
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
    for model in (EvidenceConfidenceEvaluation, ProductSignalEvent, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_evidence_confidence_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_EVIDENCE_CONFIDENCE_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"ecf-{uuid.uuid4().hex[:8]}"
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


def test_level_bands() -> None:
    assert confidence_level_for_score(10) == "low"
    assert confidence_level_for_score(50) == "medium"
    assert confidence_level_for_score(70) == "high"
    assert confidence_level_for_score(90) == "very_high"


def test_evaluate_from_evidence_assembly() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 16, 0, 0)
    _add_signal(
        store=store,
        identity="c|ecf_a",
        observed_at=as_of - timedelta(days=2),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    report = evaluate_evidence_confidence_v1(store, as_of=as_of)
    assert report["ok"] is True
    assert report["inputs"]["evidence_assembly_only"] is True
    assert report["evaluation_count"] >= 1
    store_ev = next(e for e in report["evaluations"] if e["subject_type"] == "store")
    assert 0 <= store_ev["confidence_score"] <= 100
    assert store_ev["confidence_level"] in {"low", "medium", "high", "very_high"}
    assert "completeness" in store_ev["factors"]
    assert store_ev["evidence_bundle_id"]
    assert "purchase_count" in store_ev["missing_sources"]


def test_determinism() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 16, 0, 0)
    _add_signal(
        store=store,
        identity="c|ecf_b",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    det = verify_evidence_confidence_determinism_v1(store, as_of=as_of)
    assert det["ok"] is True
    assert det["deterministic"] is True


def test_materialize_idempotent() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 16, 0, 0)
    _add_signal(
        store=store,
        identity="c|ecf_c",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    m1 = materialize_evidence_confidence_v1(store, as_of=as_of)
    m2 = materialize_evidence_confidence_v1(store, as_of=as_of)
    assert m1["ok"] and m2["ok"]
    assert m1["canonical_fingerprint"] == m2["canonical_fingerprint"]
    n = (
        db.session.query(EvidenceConfidenceEvaluation)
        .filter(EvidenceConfidenceEvaluation.store_slug == store)
        .count()
    )
    assert n >= 1


def test_disabled_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_store()
    monkeypatch.setenv(ENV_EVIDENCE_CONFIDENCE_V1, "0")
    out = materialize_evidence_confidence_v1(store)
    assert out["ok"] is False
    assert out.get("skipped_disabled") is True


def test_no_forbidden_semantics() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 16, 0, 0)
    report = evaluate_evidence_confidence_v1(store, as_of=as_of)
    blob = str(report).lower()
    for forbidden in ("recommend", "ranking", "health_score", "opportunity", "guidance"):
        assert forbidden not in blob
