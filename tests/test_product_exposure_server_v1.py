# -*- coding: utf-8 -*-
"""Product Exposure Server Implementation V1 — ingest, persist, retention, isolation."""
from __future__ import annotations

import inspect
import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

import main
from extensions import db
from models import ProductCatalogEntry, ProductExposureDailyFact, ProductExposureEvent, Store
from schema_product_exposure_v1 import (
    ensure_product_exposure_schema,
    reset_product_exposure_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_exposure_v1.constants_v1 import (
    PAGE_CONTEXT_PDP,
    SOURCE_STOREFRONT_WIDGET_V1,
    TRUTH_VERSION_EXPOSURE_V1,
)
from services.product_exposure_v1.ingest_v1 import IngestHttpError, ingest_product_viewed
from services.product_exposure_v1.metrics_v1 import (
    exposure_metrics_snapshot,
    reset_exposure_metrics_for_tests,
)
from services.product_exposure_v1.persist_v1 import persist_commercial_exposure
from services.product_exposure_v1.rate_limit_v1 import reset_exposure_rate_limiter_for_tests
from services.product_exposure_v1.rebuild_v1 import rebuild_daily_facts
from services.product_exposure_v1.retention_v1 import (
    hot_cutoff_utc,
    purge_exposure_for_store,
    run_exposure_retention_tick,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    ALIAS_KIND_ZID_PERMALINK,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory

PID = "29fcfe6d-b5d0-4fc6-aaac-c9cca296a0b6"
ENDPOINT = "/api/storefront/product-viewed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _wipe() -> None:
    from models import StoreIdentityAlias

    for model in (
        ProductExposureEvent,
        ProductExposureDailyFact,
        ProductCatalogEntry,
        StoreIdentityAlias,
        Store,
    ):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_product_exposure_schema_guard_for_tests()
    reset_exposure_metrics_for_tests()
    reset_exposure_rate_limiter_for_tests()


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CARTFLOW_EXPOSURE_RATE_LIMIT_ENABLED", "0")
    monkeypatch.delenv("CARTFLOW_EXPOSURE_RETENTION_ENABLED", raising=False)
    _reset_recovery_memory()
    _wipe()
    db.create_all()
    ensure_store_identity_schema(db)
    ensure_product_exposure_schema(db)
    yield
    _wipe()


def _seed(
    *,
    slug: str | None = None,
    permalink: str | None = None,
    product_id: str = PID,
) -> dict[str, str]:
    slug = slug or f"pex-{uuid.uuid4().hex[:10]}"
    permalink = permalink or f"ph{uuid.uuid4().hex[:8]}"
    store = Store(zid_store_id=slug, vip_cart_threshold=1000)
    db.session.add(store)
    db.session.commit()
    register_store_identity_alias(
        store_id=int(store.id),
        alias_kind=ALIAS_KIND_CARTFLOW_ZID,
        alias_value=slug,
        platform="cartflow",
    )
    register_store_identity_alias(
        store_id=int(store.id),
        alias_kind=ALIAS_KIND_ZID_PERMALINK,
        alias_value=permalink,
        platform="zid",
    )
    now = _utcnow()
    db.session.add(
        ProductCatalogEntry(
            store_slug=slug,
            stable_identity_key=f"pid:{product_id}",
            identity_tier="C",
            product_id=product_id,
            capture_confidence="high",
            catalog_source="test_exposure",
            first_seen_at=now,
            last_synced_at=now,
        )
    )
    db.session.commit()
    return {
        "slug": slug,
        "permalink": permalink,
        "product_id": product_id,
        "origin": f"https://{permalink}.zid.store",
    }


def _payload(ctx: dict[str, str], **over: object) -> dict[str, object]:
    body: dict[str, object] = {
        "event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "store_slug": ctx["slug"],
        "product_id": ctx["product_id"],
        "session_id": f"s_{uuid.uuid4().hex[:12]}",
        "occurred_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": SOURCE_STOREFRONT_WIDGET_V1,
        "page_context": PAGE_CONTEXT_PDP,
        "truth_version": TRUTH_VERSION_EXPOSURE_V1,
    }
    body.update(over)
    return body


def _post(ctx: dict[str, str], payload: dict[str, object], *, origin: str | None = None):
    client = TestClient(main.app)
    headers = {}
    if origin is not False:  # type: ignore[comparison-overlap]
        headers["Origin"] = origin if origin is not None else ctx["origin"]
    return client.post(ENDPOINT, json=payload, headers=headers)


def _persist(
    ctx: dict[str, str],
    *,
    occurred_at: datetime,
    session_id: str,
    event_id: str | None = None,
    product_id: str | None = None,
    _fail_after: str | None = None,
):
    return persist_commercial_exposure(
        event_id=event_id or f"evt_{uuid.uuid4().hex[:16]}",
        store_slug=ctx["slug"],
        product_id=product_id or ctx["product_id"],
        session_id=session_id,
        occurred_at=occurred_at,
        received_at=_utcnow(),
        source=SOURCE_STOREFRONT_WIDGET_V1,
        page_context=PAGE_CONTEXT_PDP,
        truth_version=TRUTH_VERSION_EXPOSURE_V1,
        commerce_platform="zid",
        _fail_after=_fail_after,
    )


def test_http_persist_happy_path():
    ctx = _seed()
    r = _post(ctx, _payload(ctx))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["persisted"] is True
    assert body["reason"] == "persisted"
    assert "error" not in body or body.get("error") in (None, "")
    assert db.session.query(ProductExposureEvent).count() == 1
    fact = db.session.query(ProductExposureDailyFact).one()
    assert fact.pdp_view_count == 1
    assert fact.viewing_session_count == 1
    assert fact.sealed_at is None
    row = db.session.query(ProductExposureEvent).one()
    assert row.store_slug == ctx["slug"]
    assert row.referrer_domain is None


def test_rate_limited(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CARTFLOW_EXPOSURE_RATE_LIMIT_ENABLED", "1")
    reset_exposure_rate_limiter_for_tests()
    ctx = _seed()
    sid = "s_ratelimit-aaa-1"
    last = None
    for i in range(21):
        last = _post(
            ctx,
            _payload(ctx, session_id=sid, event_id=f"evt_rl_{i:04d}_abcd"),
        )
    assert last is not None
    assert last.status_code == 429
    assert last.json()["error"] == "rate_limited"


def test_duplicate_event_id_idempotent_replay():
    ctx = _seed()
    p = _payload(ctx, event_id="evt_replay_same_01")
    r1 = _post(ctx, p)
    r2 = _post(ctx, p)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["reason"] == "idempotent_replay"
    assert r2.json()["persisted"] is False
    assert db.session.query(ProductExposureEvent).count() == 1
    assert db.session.query(ProductExposureDailyFact).one().pdp_view_count == 1


def test_commercial_duplicate_no_row():
    ctx = _seed()
    sid = "s_session-aaaa-01"
    t0 = _utcnow()
    a = _persist(ctx, occurred_at=t0, session_id=sid)
    b = _persist(ctx, occurred_at=t0 + timedelta(minutes=10), session_id=sid)
    assert a.reason == "persisted"
    assert b.reason == "commercial_dedupe"
    assert db.session.query(ProductExposureEvent).count() == 1
    assert db.session.query(ProductExposureDailyFact).one().pdp_view_count == 1


def test_boundary_29m59_30m00_30m01():
    ctx = _seed()
    sid = "s_session-bound-01"
    t0 = _utcnow().replace(microsecond=0)
    assert _persist(ctx, occurred_at=t0, session_id=sid).reason == "persisted"
    d2959 = _persist(ctx, occurred_at=t0 + timedelta(minutes=29, seconds=59), session_id=sid)
    assert d2959.reason == "commercial_dedupe"
    d3000 = _persist(ctx, occurred_at=t0 + timedelta(minutes=30), session_id=sid)
    assert d3000.reason == "persisted"

    sid2 = "s_session-bound-02"
    t1 = t0 + timedelta(hours=3)
    assert _persist(ctx, occurred_at=t1, session_id=sid2).reason == "persisted"
    d3001 = _persist(ctx, occurred_at=t1 + timedelta(minutes=30, seconds=1), session_id=sid2)
    assert d3001.reason == "persisted"
    assert db.session.query(ProductExposureEvent).count() == 4


def test_invalid_origin_and_missing_origin():
    ctx = _seed()
    p = _payload(ctx)
    r_missing = TestClient(main.app).post(ENDPOINT, json=p)
    assert r_missing.status_code == 403
    assert r_missing.json()["error"] == "missing_origin"
    r_bad = _post(ctx, p, origin="https://evil.example.com")
    assert r_bad.status_code == 403
    assert r_bad.json()["error"] in {"invalid_origin", "unknown_store"}
    r_http = _post(ctx, p, origin="http://{}.zid.store".format(ctx["permalink"]))
    assert r_http.status_code == 403
    assert r_http.json()["error"] == "invalid_origin"
    assert db.session.query(ProductExposureEvent).count() == 0


def test_store_mismatch():
    a = _seed()
    b = _seed()
    p = _payload(a, store_slug=b["slug"])
    r = _post(a, p, origin=a["origin"])
    assert r.status_code == 403
    assert r.json()["error"] == "store_origin_mismatch"


def test_foreign_and_missing_and_invalid_product():
    a = _seed()
    b = _seed(product_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    r_foreign = _post(a, _payload(a, product_id=b["product_id"]))
    assert r_foreign.status_code == 422
    assert r_foreign.json()["error"] == "product_not_owned"
    r_missing = _post(a, _payload(a, product_id="00000000-0000-0000-0000-000000000000"))
    assert r_missing.status_code == 422
    assert r_missing.json()["error"] == "product_not_owned"
    r_invalid = _post(a, _payload(a, product_id="has space"))
    assert r_invalid.status_code == 400
    assert r_invalid.json()["error"] == "invalid_product_id"


def test_invalid_session_and_clock_and_payload():
    ctx = _seed()
    r_sess = _post(ctx, _payload(ctx, session_id="not-a-session"))
    assert r_sess.status_code == 400
    assert r_sess.json()["error"] == "malformed_session"
    r_empty = _post(ctx, _payload(ctx, session_id=""))
    assert r_empty.status_code == 400
    assert r_empty.json()["error"] == "missing_session"
    old = (datetime.now(timezone.utc) - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r_old = _post(ctx, _payload(ctx, occurred_at=old))
    assert r_old.status_code == 422
    assert r_old.json()["error"] == "clock_too_old"
    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r_fut = _post(ctx, _payload(ctx, occurred_at=future))
    assert r_fut.status_code == 422
    assert r_fut.json()["error"] == "clock_future"
    r_src = _post(ctx, _payload(ctx, source="other_source"))
    assert r_src.status_code == 422
    assert r_src.json()["error"] == "unknown_source"
    r_field = _post(ctx, {**_payload(ctx), "url": "https://example.com/p"})
    assert r_field.status_code == 400
    assert r_field.json()["error"] == "unknown_field"
    huge = json.dumps(_payload(ctx)).encode("utf-8") + b"x" * 3000
    with pytest.raises(IngestHttpError) as ei:
        ingest_product_viewed(raw_body=huge, origin=ctx["origin"])
    assert ei.value.status == 413
    assert ei.value.error == "payload_too_large"


def test_db_unavailable(monkeypatch: pytest.MonkeyPatch):
    ctx = _seed()

    def _boom(**kwargs):
        raise SQLAlchemyError("down")

    monkeypatch.setattr(
        "services.product_exposure_v1.ingest_v1.persist_commercial_exposure",
        _boom,
    )
    r = _post(ctx, _payload(ctx))
    assert r.status_code == 503
    assert r.json()["error"] == "unavailable"
    assert "stack" not in (r.text or "").lower()
    assert db.session.query(ProductExposureEvent).count() == 0


def test_transaction_rollback_raw_then_fact_fail():
    ctx = _seed()
    sid = "s_rollback-aaaa-1"
    t0 = _utcnow()
    with pytest.raises(RuntimeError):
        _persist(ctx, occurred_at=t0, session_id=sid, _fail_after="raw")
    assert db.session.query(ProductExposureEvent).count() == 0
    assert db.session.query(ProductExposureDailyFact).count() == 0
    with pytest.raises(RuntimeError):
        _persist(ctx, occurred_at=t0, session_id=sid, _fail_after="fact")
    assert db.session.query(ProductExposureEvent).count() == 0
    assert db.session.query(ProductExposureDailyFact).count() == 0


def test_commit_success_then_unknown_outcome_retry():
    ctx = _seed()
    sid = "s_unknown-bbbb-1"
    eid = "evt_unknown_outcome01"
    t0 = _utcnow()
    with pytest.raises(RuntimeError):
        _persist(ctx, occurred_at=t0, session_id=sid, event_id=eid, _fail_after="commit")
    assert db.session.query(ProductExposureEvent).count() == 1
    retry = _persist(ctx, occurred_at=t0, session_id=sid, event_id=eid)
    assert retry.reason == "idempotent_replay"
    assert db.session.query(ProductExposureEvent).count() == 1
    assert db.session.query(ProductExposureDailyFact).one().pdp_view_count == 1


def test_concurrent_same_event_id():
    ctx = _seed()
    eid = "evt_concurrent_same01"
    sid = "s_conc-event-0001"
    t0 = _utcnow()
    barrier = threading.Barrier(2)
    out: list[str] = []

    def worker() -> None:
        barrier.wait()
        res = _persist(ctx, occurred_at=t0, session_id=sid, event_id=eid)
        out.append(res.reason)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=15)
    assert sorted(out) in (
        ["idempotent_replay", "persisted"],
        ["persisted", "idempotent_replay"],
    )
    assert db.session.query(ProductExposureEvent).count() == 1
    assert db.session.query(ProductExposureDailyFact).one().pdp_view_count == 1


def test_concurrent_same_session_product():
    ctx = _seed()
    sid = "s_conc-sess-prod01"
    t0 = _utcnow()
    barrier = threading.Barrier(2)
    out: list[str] = []

    def worker(i: int) -> None:
        barrier.wait()
        res = _persist(
            ctx,
            occurred_at=t0,
            session_id=sid,
            event_id=f"evt_conc_sess_{i:02d}xx",
        )
        out.append(res.reason)

    threads = [
        threading.Thread(target=worker, args=(i,)) for i in range(2)
    ]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=15)
    assert "persisted" in out
    assert out.count("persisted") == 1
    assert out.count("commercial_dedupe") == 1
    assert db.session.query(ProductExposureEvent).count() == 1


def test_midnight_crossing_does_not_reset_commercial_window():
    ctx = _seed()
    sid = "s_midnight-aaaa-1"
    t0 = datetime(2026, 9, 9, 23, 50, 0)
    late = datetime(2026, 9, 10, 0, 10, 0)
    assert _persist(ctx, occurred_at=t0, session_id=sid).reason == "persisted"
    dup = _persist(ctx, occurred_at=late, session_id=sid)
    assert dup.reason == "commercial_dedupe"
    assert db.session.query(ProductExposureEvent).count() == 1
    fact = db.session.query(ProductExposureDailyFact).one()
    assert fact.date_utc == "2026-09-09"


def test_daily_boundary_23_59_and_00_00():
    ctx = _seed()
    sid1 = "s_daybound-aaa-1"
    sid2 = "s_daybound-bbb-2"
    a = _persist(ctx, occurred_at=datetime(2026, 9, 9, 23, 59, 59), session_id=sid1)
    b = _persist(ctx, occurred_at=datetime(2026, 9, 10, 0, 0, 0), session_id=sid2)
    assert a.reason == "persisted" and b.reason == "persisted"
    dates = {
        r.date_utc: (r.pdp_view_count, r.viewing_session_count)
        for r in db.session.query(ProductExposureDailyFact).all()
    }
    assert dates["2026-09-09"] == (1, 1)
    assert dates["2026-09-10"] == (1, 1)


def test_viewing_session_count_not_per_row():
    ctx = _seed()
    sid = "s_sessions-same-01"
    t0 = _utcnow().replace(microsecond=0)
    _persist(ctx, occurred_at=t0, session_id=sid)
    _persist(ctx, occurred_at=t0 + timedelta(minutes=30), session_id=sid)
    fact = db.session.query(ProductExposureDailyFact).one()
    assert fact.pdp_view_count == 2
    assert fact.viewing_session_count == 1
    _persist(
        ctx,
        occurred_at=t0 + timedelta(minutes=31),
        session_id="s_sessions-other-02",
    )
    fact = db.session.query(ProductExposureDailyFact).one()
    assert fact.pdp_view_count == 3
    assert fact.viewing_session_count == 2


def test_lab_tenant_forbidden():
    ctx = _seed(slug="demo", permalink=f"lb{uuid.uuid4().hex[:8]}")
    r = _post(ctx, _payload(ctx))
    assert r.status_code == 403
    assert r.json()["error"] == "lab_tenant_forbidden"


def test_tenant_isolation_and_product_deleted():
    a = _seed()
    b = _seed()
    _post(a, _payload(a))
    _post(b, _payload(b))
    assert db.session.query(ProductExposureEvent).filter_by(store_slug=a["slug"]).count() == 1
    assert db.session.query(ProductExposureEvent).filter_by(store_slug=b["slug"]).count() == 1
    db.session.query(ProductCatalogEntry).filter_by(store_slug=a["slug"]).delete()
    db.session.commit()
    r = _post(a, _payload(a))
    assert r.status_code == 422
    assert r.json()["error"] == "product_not_owned"
    assert db.session.query(ProductExposureEvent).filter_by(store_slug=a["slug"]).count() == 1
    purged = purge_exposure_for_store(a["slug"])
    assert purged["raw_deleted"] == 1
    assert db.session.query(ProductExposureEvent).filter_by(store_slug=b["slug"]).count() == 1


def test_rebuild_replace_not_increment():
    ctx = _seed()
    sid = "s_rebuild-aaaa-01"
    t0 = _utcnow()
    _persist(ctx, occurred_at=t0, session_id=sid)
    fact = db.session.query(ProductExposureDailyFact).one()
    fact.pdp_view_count = 99
    db.session.commit()
    out = rebuild_daily_facts(store_slug=ctx["slug"], last_30_days=True)
    assert out["ok"] is True
    fact = db.session.query(ProductExposureDailyFact).one()
    assert fact.pdp_view_count == 1
    assert fact.viewing_session_count == 1


def test_seal_valid_then_raw_delete():
    ctx = _seed()
    occurred = hot_cutoff_utc() - timedelta(days=1, hours=3)
    _persist(ctx, occurred_at=occurred, session_id="s_seal-valid-0001")
    assert db.session.query(ProductExposureEvent).count() == 1
    tick = run_exposure_retention_tick(force=True)
    assert tick["ok"] is True
    assert tick["seal_success"] >= 1
    fact = db.session.query(ProductExposureDailyFact).one()
    assert fact.sealed_at is not None
    assert fact.seal_source_row_count == 1
    assert db.session.query(ProductExposureEvent).count() == 0


def test_seal_mismatch_blocks_raw_delete():
    ctx = _seed()
    occurred = hot_cutoff_utc() - timedelta(days=1, hours=3)
    _persist(ctx, occurred_at=occurred, session_id="s_seal-mismatch-01")
    fact = db.session.query(ProductExposureDailyFact).one()
    fact.pdp_view_count = 7
    db.session.commit()
    tick = run_exposure_retention_tick(force=True)
    assert tick["seal_failure"] >= 1
    assert db.session.query(ProductExposureEvent).count() == 1
    assert db.session.query(ProductExposureDailyFact).one().sealed_at is None


def test_raw_delete_blocked_without_seal():
    ctx = _seed()
    occurred = hot_cutoff_utc() - timedelta(days=2)
    db.session.add(
        ProductExposureEvent(
            event_id="evt_noseal_raw_0001",
            store_slug=ctx["slug"],
            product_id=ctx["product_id"],
            session_id="s_noseal-aaaa-01",
            page_context=PAGE_CONTEXT_PDP,
            occurred_at=occurred,
            received_at=_utcnow(),
            source=SOURCE_STOREFRONT_WIDGET_V1,
            truth_version=TRUTH_VERSION_EXPOSURE_V1,
            commercial_dedupe_key="k",
            commercial_bucket="b",
            commerce_platform="zid",
        )
    )
    db.session.commit()
    tick = run_exposure_retention_tick(force=True)
    assert db.session.query(ProductExposureEvent).count() == 1
    assert tick["raw_deleted"] == 0


def test_cleanup_restart_retry_idempotent():
    ctx = _seed()
    occurred = hot_cutoff_utc() - timedelta(days=1, hours=1)
    _persist(ctx, occurred_at=occurred, session_id="s_cleanup-aaaa-1")
    first = run_exposure_retention_tick(force=True)
    second = run_exposure_retention_tick(force=True)
    assert first["ok"] and second["ok"]
    assert db.session.query(ProductExposureEvent).count() == 0
    assert second["raw_deleted"] == 0


def test_quiet_merchant_tick_without_new_ingest():
    ctx = _seed()
    occurred = hot_cutoff_utc() - timedelta(days=1, hours=2)
    _persist(ctx, occurred_at=occurred, session_id="s_quiet-merchant1")
    tick = run_exposure_retention_tick(force=True)
    assert tick["skipped"] is False
    assert tick["seal_success"] >= 1


def test_large_retention_backlog_is_bounded():
    ctx = _seed()
    cutoff = hot_cutoff_utc()
    for i in range(25):
        d = cutoff - timedelta(days=i + 1)
        _persist(
            ctx,
            occurred_at=d + timedelta(hours=1),
            session_id=f"s_backlog-{i:04d}-xx",
            event_id=f"evt_backlog_{i:04d}_row",
        )
    tick = run_exposure_retention_tick(force=True)
    assert tick["seal_attempts"] <= 20
    assert tick["raw_deleted"] <= 200


def test_fact_retention_over_400_days_separate_sql():
    ctx = _seed()
    old = (datetime.now(timezone.utc).date() - timedelta(days=401)).isoformat()
    db.session.add(
        ProductExposureDailyFact(
            store_slug=ctx["slug"],
            product_id=ctx["product_id"],
            date_utc=old,
            pdp_view_count=3,
            viewing_session_count=2,
            truth_version=TRUTH_VERSION_EXPOSURE_V1,
            sealed_at=_utcnow(),
            seal_truth_version=TRUTH_VERSION_EXPOSURE_V1,
            seal_source_row_count=3,
        )
    )
    db.session.commit()
    tick = run_exposure_retention_tick(force=True)
    assert tick["facts_deleted"] == 1
    assert db.session.query(ProductExposureDailyFact).filter_by(date_utc=old).count() == 0


def test_retention_default_off_and_overlap_skip():
    ctx = _seed()
    skipped = run_exposure_retention_tick(force=False)
    assert skipped["skipped"] is True
    assert skipped["reason"] == "retention_disabled"
    src = inspect.getsource(run_exposure_retention_tick)
    assert "tick_in_progress" in src


def test_hot_rebuild_unseals_mismatch():
    ctx = _seed()
    t0 = _utcnow()
    _persist(ctx, occurred_at=t0, session_id="s_unseal-aaaa-01")
    fact = db.session.query(ProductExposureDailyFact).one()
    fact.sealed_at = _utcnow()
    fact.pdp_view_count = 4
    db.session.commit()
    out = rebuild_daily_facts(store_slug=ctx["slug"], product_id=ctx["product_id"])
    assert out["unsealed"] == 1
    fact = db.session.query(ProductExposureDailyFact).one()
    assert fact.sealed_at is None
    assert fact.pdp_view_count == 1


def test_endpoint_statement_count_and_wall_time():
    ctx = _seed()
    t0 = time.perf_counter()
    raw = json.dumps(_payload(ctx)).encode("utf-8")
    body = ingest_product_viewed(raw_body=raw, origin=ctx["origin"])
    wall_ms = (time.perf_counter() - t0) * 1000
    assert body["reason"] == "persisted"
    assert body["db_statements"] <= 12
    assert body["db_statements"] >= 5
    assert wall_ms < 2000


def test_retention_tick_wall_and_bounds():
    ctx = _seed()
    occurred = hot_cutoff_utc() - timedelta(days=1, hours=4)
    _persist(ctx, occurred_at=occurred, session_id="s_tickwall-0001")
    t0 = time.perf_counter()
    tick = run_exposure_retention_tick(force=True)
    wall_ms = (time.perf_counter() - t0) * 1000
    assert tick["ok"] is True
    assert tick["query_count"] <= 40
    assert wall_ms < 5000


def test_metrics_low_cardinality_and_no_ai():
    ctx = _seed()
    _post(ctx, _payload(ctx))
    snap = exposure_metrics_snapshot()
    assert snap["exposure_requests_total"] >= 1
    assert snap["exposure_persisted_total"] >= 1
    assert "product_id" not in snap
    ingest_src = Path("services/product_exposure_v1/ingest_v1.py").read_text(encoding="utf-8")
    persist_src = Path("services/product_exposure_v1/persist_v1.py").read_text(encoding="utf-8")
    for src in (ingest_src, persist_src):
        assert "anthropic" not in src
        assert "zid_client" not in src
        assert "requests.get" not in src


def test_scheduler_isolation_from_recovery_and_whatsapp():
    loop_src = Path("services/exposure_retention_loop_v1.py").read_text(encoding="utf-8")
    tick_src = Path("services/product_exposure_v1/retention_v1.py").read_text(encoding="utf-8")
    for src in (loop_src, tick_src):
        assert "whatsapp" not in src.lower()
        assert "recovery_db_due" not in src
        assert "purchase_stop" not in src
        assert "send_whatsapp" not in src
    scanner = Path("services/recovery_db_due_scanner.py").read_text(encoding="utf-8")
    assert "exposure_retention" not in scanner
    assert "product_exposure" not in scanner
    main_startup = inspect.getsource(main._startup_whatsapp_queue)
    assert "start_exposure_retention_loop" not in main_startup
    assert "run_exposure_retention_tick" not in main_startup
    assert "3600" in loop_src
    interval_src = inspect.getsource(
        __import__(
            "services.exposure_retention_loop_v1",
            fromlist=["exposure_retention_loop_interval_seconds"],
        ).exposure_retention_loop_interval_seconds
    )
    assert "max(300.0, v)" in interval_src


def test_products_read_fanout_not_reopened():
    from services.product_data import product_catalog_v1 as catalog

    src = inspect.getsource(catalog)
    assert "product_exposure" not in src
    assert "ProductExposure" not in src
    main_src = Path("main.py").read_text(encoding="utf-8")
    assert "product-viewed" in main_src
    assert "widget_loader.js" not in Path(
        "services/product_exposure_v1/http_v1.py"
    ).read_text(encoding="utf-8")


def test_ingest_does_not_delete_raw():
    src = Path("services/product_exposure_v1/ingest_v1.py").read_text(encoding="utf-8")
    persist = Path("services/product_exposure_v1/persist_v1.py").read_text(encoding="utf-8")
    assert "DELETE" not in src
    assert ".delete(" not in persist
