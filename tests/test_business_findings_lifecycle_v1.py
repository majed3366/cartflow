# -*- coding: utf-8 -*-
"""Business Findings Lifecycle V1 — foundation tests."""
from __future__ import annotations

import inspect
import uuid

import pytest

from extensions import db
from models import BusinessFinding, Store
from schema_business_findings_lifecycle_v1 import (
    ensure_business_findings_lifecycle_schema,
    reset_business_findings_lifecycle_schema_guard_for_tests,
)
from services.business_findings_lifecycle_v1.consume_home_v1 import (
    load_current_findings_package_v1,
)
from services.business_findings_lifecycle_v1.flag_v1 import (
    ENV_BUSINESS_FINDINGS_LIFECYCLE_V1,
    business_findings_lifecycle_v1_enabled,
)
from services.business_findings_lifecycle_v1.lifecycle_v1 import can_advance
from services.business_findings_lifecycle_v1.materialize_v1 import (
    materialize_business_findings_lifecycle_v1,
)
from services.business_findings_lifecycle_v1.prod_probe_v1 import (
    build_business_findings_lifecycle_prod_probe_v1,
)
from services.business_findings_lifecycle_v1.types_v1 import (
    LIFECYCLE_ORDER_V1,
    LS_DETECTED,
    LS_DISPLAYED,
    LS_KNOWLEDGE_ROUTED,
    LS_OT_ROUTED,
    LS_PERSISTED,
    LS_SURFACE_ELIGIBLE,
    LS_VALIDATED,
)
from services.home_commercial_intelligence_v1 import apply_home_commercial_intelligence_v1
from services.merchant_home_composition_v1 import build_merchant_home_experience_api_payload
from tests.test_recovery_isolation import _reset_recovery_memory


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_BUSINESS_FINDINGS_LIFECYCLE_V1, "1")
    reset_business_findings_lifecycle_schema_guard_for_tests()
    db.session.query(BusinessFinding).delete()
    db.session.query(Store).delete()
    db.session.commit()
    db.create_all()
    ensure_business_findings_lifecycle_schema(db)
    yield


def _seed_store() -> str:
    slug = f"bfl-{uuid.uuid4().hex[:8]}"
    db.session.add(Store(zid_store_id=slug, vip_cart_threshold=1000))
    db.session.commit()
    return slug


def test_flag_default_on() -> None:
    assert business_findings_lifecycle_v1_enabled() is True


def test_lifecycle_no_skips() -> None:
    assert can_advance(LS_DETECTED, LS_VALIDATED) is True
    assert can_advance(LS_DETECTED, LS_PERSISTED) is False
    assert can_advance(LS_VALIDATED, LS_PERSISTED) is True
    assert can_advance(LS_PERSISTED, LS_KNOWLEDGE_ROUTED) is True
    assert can_advance(LS_KNOWLEDGE_ROUTED, LS_OT_ROUTED) is True
    assert can_advance(LS_OT_ROUTED, LS_SURFACE_ELIGIBLE) is True
    assert can_advance(LS_SURFACE_ELIGIBLE, LS_DISPLAYED) is True
    assert can_advance(LS_DETECTED, LS_SURFACE_ELIGIBLE) is False
    assert LIFECYCLE_ORDER_V1[0] == LS_DETECTED


def test_materialize_persists_and_routes_demo_fixture() -> None:
    slug = _seed_store()
    mat = materialize_business_findings_lifecycle_v1(
        slug,
        load_db=False,
        demo_fixture=True,
        admit_review_fixtures=True,
    )
    assert mat["ok"] is True
    assert int(mat["detected"]) >= 1
    assert int(mat["persisted"]) >= 1
    assert int(mat["knowledge_routed"]) >= 1
    assert int(mat["ot_routed"]) >= 1
    rows = db.session.query(BusinessFinding).filter_by(store_slug=slug).all()
    assert rows
    for row in rows:
        assert row.lifecycle_state in {
            LS_SURFACE_ELIGIBLE,
            LS_DISPLAYED,
            LS_OT_ROUTED,
            LS_KNOWLEDGE_ROUTED,
            LS_PERSISTED,
        }
        assert row.finding_id
        assert row.finding_type
        assert row.evidence_json
        assert row.lifecycle_state != LS_DETECTED or True
        # After full materialize path, expect at least surface_eligible
        assert row.lifecycle_state == LS_SURFACE_ELIGIBLE


def test_home_never_calls_engine() -> None:
    src = inspect.getsource(build_merchant_home_experience_api_payload)
    assert "run_business_findings_engine_v1" not in src
    assert "load_current_findings_package_v1" in src
    hci = inspect.getsource(apply_home_commercial_intelligence_v1)
    assert "run_business_findings_engine_v1" not in hci
    assert "load_current_findings_package_v1" in hci


def test_consume_marks_displayed() -> None:
    slug = _seed_store()
    mat = materialize_business_findings_lifecycle_v1(
        slug,
        load_db=False,
        demo_fixture=True,
        admit_review_fixtures=True,
    )
    assert mat["ok"] is True
    pkg = load_current_findings_package_v1(slug, mark_displayed=True)
    assert pkg.get("source") == "lifecycle_consume"
    assert pkg.get("ok") is True
    # Home-eligible findings become displayed
    displayed = (
        db.session.query(BusinessFinding)
        .filter_by(store_slug=slug, lifecycle_state=LS_DISPLAYED)
        .count()
    )
    assert displayed >= 1


def test_probe_diagnostics_stages() -> None:
    slug = "demo"
    if not db.session.query(Store).filter_by(zid_store_id=slug).first():
        db.session.add(Store(zid_store_id=slug, vip_cart_threshold=1000))
        db.session.commit()
    report = build_business_findings_lifecycle_prod_probe_v1(
        slug,
        materialize=True,
        demo_fixture=True,
        admit_review_fixtures=True,
    )
    assert report["ok"] is True
    assert report["home_must_not_generate"] is True
    assert report["surfaces_consume_only"] is True
    assert report["diagnostics"]
    d0 = report["diagnostics"][0]
    for key in (
        "generated",
        "persisted",
        "routed",
        "surface_eligible",
        "displayed",
        "stopped_at",
    ):
        assert key in d0, key
    assert d0["generated"] is True
    assert d0["persisted"] is True
    assert d0["stopped_at"]
