# -*- coding: utf-8 -*-
"""Product Evidence Assembly Foundation V1 — Metrics + Trends only."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import (
    ProductEvidenceBundle,
    ProductEvidenceItem,
    ProductSignalEvent,
    Store,
)
from schema_product_evidence_assembly_v1 import (
    reset_product_evidence_assembly_schema_guard_for_tests,
)
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.product_evidence_assembly_flag_v1 import (
    ENV_PRODUCT_EVIDENCE_ASSEMBLY_V1,
)
from services.product_data.product_evidence_assembly_v1 import (
    assemble_product_evidence_v1,
    materialize_product_evidence_v1,
    verify_evidence_assembly_determinism_v1,
)
from services.product_data.product_signal_types_v1 import (
    FAMILY_PRODUCT_CART_ACTIVITY,
    SIGNAL_PRODUCT_CART_ADDED,
)
from services.product_data.product_trends_types_v1 import TREND_WINDOW_D7
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (
        ProductEvidenceItem,
        ProductEvidenceBundle,
        ProductSignalEvent,
        Store,
    ):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_product_evidence_assembly_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_PRODUCT_EVIDENCE_ASSEMBLY_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"pea-{uuid.uuid4().hex[:8]}"
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
    # Signals exist only so Metrics/Trends APIs have data; assembly never reads them.
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


def test_assemble_bundle_with_lineage() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 15, 0, 0)
    _add_signal(
        store=store,
        identity="c|pea_a",
        observed_at=as_of - timedelta(days=2),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    report = assemble_product_evidence_v1(
        store, assembly_window=TREND_WINDOW_D7, as_of=as_of
    )
    assert report["ok"] is True
    assert report["inputs"]["signals"] is False
    assert report["bundle_count"] >= 1
    store_b = next(b for b in report["bundles"] if b["subject_type"] == "store")
    cart = next(
        i for i in store_b["items"] if i["metric_key"] == "cart_added_count"
    )
    assert cart["metric_value"] == 1
    assert cart["trend_direction"] == "newly_appeared"
    assert cart["trend_window"] == "d7"
    assert cart["source_layer"] in {"metrics+trends", "trends", "metrics"}
    assert cart["lineage"]["originating_as_of"]
    assert cart["source_record_id"]


def test_determinism() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 15, 0, 0)
    _add_signal(
        store=store,
        identity="c|pea_b",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    det = verify_evidence_assembly_determinism_v1(
        store, assembly_window=TREND_WINDOW_D7, as_of=as_of
    )
    assert det["ok"] is True
    assert det["deterministic"] is True
    assert det["fingerprint_a"] == det["fingerprint_b"]


def test_materialize_idempotent() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 15, 0, 0)
    _add_signal(
        store=store,
        identity="c|pea_c",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    m1 = materialize_product_evidence_v1(
        store, assembly_window=TREND_WINDOW_D7, as_of=as_of
    )
    m2 = materialize_product_evidence_v1(
        store, assembly_window=TREND_WINDOW_D7, as_of=as_of
    )
    assert m1["ok"] and m2["ok"]
    assert m1["canonical_fingerprint"] == m2["canonical_fingerprint"]
    bundles = (
        db.session.query(ProductEvidenceBundle)
        .filter(ProductEvidenceBundle.store_slug == store)
        .count()
    )
    items = (
        db.session.query(ProductEvidenceItem)
        .filter(ProductEvidenceItem.store_slug == store)
        .count()
    )
    assert bundles >= 1
    assert items >= 1


def test_disabled_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_store()
    monkeypatch.setenv(ENV_PRODUCT_EVIDENCE_ASSEMBLY_V1, "0")
    out = materialize_product_evidence_v1(store)
    assert out["ok"] is False
    assert out.get("skipped_disabled") is True


def test_no_forbidden_semantics() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 15, 0, 0)
    report = assemble_product_evidence_v1(store, as_of=as_of)
    blob = str(report).lower()
    for forbidden in (
        "confidence",
        "recommend",
        "ranking",
        "health_score",
        "opportunity",
        "guidance",
        "weight",
    ):
        assert forbidden not in blob
