# -*- coding: utf-8 -*-
"""
Durable Evidence Truth shadow artifact store — WP-ET-10.6.

Shared across processes via SQL. Demo materialization writes here.
Preview reads Knowledge from here (plus optional in-process merge).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

from schema_evidence_truth_materialization_v1 import (
    ensure_evidence_truth_materialization_schema,
)
from services.evidence_truth.knowledge_model_v1 import KnowledgeRecordV1
from services.evidence_truth.materialization_serde_v1 import (
    knowledge_record_from_dict_v1,
)

log = logging.getLogger("cartflow.evidence_truth")

ARTIFACT_OBSERVATION = "observation"
ARTIFACT_EVIDENCE = "evidence"
ARTIFACT_BUNDLE = "bundle"
ARTIFACT_KNOWLEDGE = "knowledge"
COMPOSER_VERSION_V1 = "wp_et_10_6_v1"

DEMO_STORE_SLUG = "demo"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _db():
    from extensions import db

    return db


def assert_demo_store_slug_v1(store_slug: str) -> str:
    slug = (store_slug or "").strip().lower()
    if slug != DEMO_STORE_SLUG:
        raise ValueError(f"non_demo_store_forbidden:{slug or 'empty'}")
    return slug


def put_shadow_artifact_v1(
    *,
    artifact_kind: str,
    artifact_id: str,
    store_slug: str,
    materialization_run_id: str,
    idempotency_key: str,
    payload: Mapping[str, Any],
    lineage: Mapping[str, Any] | None = None,
    source_ref: str = "",
    artifact_version: int = 1,
    composer_version: str = COMPOSER_VERSION_V1,
) -> dict[str, Any]:
    """Idempotent durable put. Returns {created, reused, artifact_id}."""
    from models import EvidenceTruthShadowArtifact

    slug = assert_demo_store_slug_v1(store_slug)
    kind = (artifact_kind or "").strip().lower()
    if kind not in {
        ARTIFACT_OBSERVATION,
        ARTIFACT_EVIDENCE,
        ARTIFACT_BUNDLE,
        ARTIFACT_KNOWLEDGE,
    }:
        raise ValueError(f"unknown_artifact_kind:{kind}")
    key = (idempotency_key or "").strip()
    if not key:
        raise ValueError("idempotency_key_required")
    db = _db()
    ensure_evidence_truth_materialization_schema(db)
    existing = (
        db.session.query(EvidenceTruthShadowArtifact)
        .filter(EvidenceTruthShadowArtifact.idempotency_key == key)
        .first()
    )
    if existing is not None:
        return {
            "created": False,
            "reused": True,
            "artifact_id": existing.artifact_id,
            "artifact_kind": existing.artifact_kind,
            "idempotency_key": existing.idempotency_key,
        }
    row = EvidenceTruthShadowArtifact(
        artifact_kind=kind,
        artifact_id=str(artifact_id or "").strip(),
        artifact_version=int(artifact_version or 1),
        store_slug=slug,
        materialization_run_id=str(materialization_run_id or "").strip(),
        idempotency_key=key,
        source_ref=str(source_ref or "")[:256],
        lineage_json=json.dumps(dict(lineage or {}), ensure_ascii=False, sort_keys=True),
        payload_json=json.dumps(dict(payload or {}), ensure_ascii=False, sort_keys=True),
        composer_version=str(composer_version or COMPOSER_VERSION_V1),
        created_at=_utc_now(),
    )
    db.session.add(row)
    db.session.commit()
    return {
        "created": True,
        "reused": False,
        "artifact_id": row.artifact_id,
        "artifact_kind": row.artifact_kind,
        "idempotency_key": row.idempotency_key,
    }


def list_shadow_artifacts_v1(
    *,
    store_slug: str,
    artifact_kind: str = "",
    limit: int = 200,
) -> list[dict[str, Any]]:
    from models import EvidenceTruthShadowArtifact

    slug = assert_demo_store_slug_v1(store_slug)
    db = _db()
    ensure_evidence_truth_materialization_schema(db)
    q = db.session.query(EvidenceTruthShadowArtifact).filter(
        EvidenceTruthShadowArtifact.store_slug == slug
    )
    if artifact_kind:
        q = q.filter(
            EvidenceTruthShadowArtifact.artifact_kind
            == artifact_kind.strip().lower()
        )
    q = q.order_by(EvidenceTruthShadowArtifact.id.desc()).limit(max(1, int(limit)))
    out: list[dict[str, Any]] = []
    for row in q.all():
        try:
            payload = json.loads(row.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        try:
            lineage = json.loads(row.lineage_json or "{}")
        except json.JSONDecodeError:
            lineage = {}
        out.append(
            {
                "artifact_kind": row.artifact_kind,
                "artifact_id": row.artifact_id,
                "artifact_version": int(row.artifact_version or 1),
                "store_slug": row.store_slug,
                "materialization_run_id": row.materialization_run_id,
                "idempotency_key": row.idempotency_key,
                "source_ref": row.source_ref,
                "lineage": lineage,
                "payload": payload,
                "composer_version": row.composer_version,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
        )
    return out


def list_durable_knowledge_records_v1(
    *,
    store_slug: str = "",
    limit: int = 50,
) -> list[KnowledgeRecordV1]:
    """
    Load durable Knowledge for Preview.

    When store_slug empty, returns demo-only Knowledge (V1 authorization).
    """
    from models import EvidenceTruthShadowArtifact

    db = _db()
    ensure_evidence_truth_materialization_schema(db)
    slug = (store_slug or "").strip().lower()
    q = db.session.query(EvidenceTruthShadowArtifact).filter(
        EvidenceTruthShadowArtifact.artifact_kind == ARTIFACT_KNOWLEDGE
    )
    if slug:
        if slug != DEMO_STORE_SLUG:
            return []
        q = q.filter(EvidenceTruthShadowArtifact.store_slug == DEMO_STORE_SLUG)
    else:
        q = q.filter(EvidenceTruthShadowArtifact.store_slug == DEMO_STORE_SLUG)
    q = q.order_by(EvidenceTruthShadowArtifact.id.desc()).limit(max(1, int(limit)))
    records: list[KnowledgeRecordV1] = []
    seen: set[str] = set()
    for row in q.all():
        try:
            payload = json.loads(row.payload_json or "{}")
            rec = knowledge_record_from_dict_v1(payload)
        except Exception as exc:  # noqa: BLE001
            log.warning("durable knowledge decode skipped: %s", exc)
            continue
        if rec.knowledge_id in seen:
            continue
        seen.add(rec.knowledge_id)
        records.append(rec)
    return records


def list_durable_knowledge_store_slugs_v1() -> list[str]:
    """Demo-authorized store slugs that have durable Knowledge (V1: demo only)."""
    from models import EvidenceTruthShadowArtifact

    db = _db()
    ensure_evidence_truth_materialization_schema(db)
    rows = (
        db.session.query(EvidenceTruthShadowArtifact.store_slug)
        .filter(
            EvidenceTruthShadowArtifact.artifact_kind == ARTIFACT_KNOWLEDGE,
            EvidenceTruthShadowArtifact.store_slug == DEMO_STORE_SLUG,
        )
        .distinct()
        .all()
    )
    return sorted({str(r[0]).strip().lower() for r in rows if r and r[0]})


def count_shadow_artifacts_v1(
    *, store_slug: str, artifact_kind: str = ""
) -> int:
    from models import EvidenceTruthShadowArtifact

    slug = assert_demo_store_slug_v1(store_slug)
    db = _db()
    ensure_evidence_truth_materialization_schema(db)
    q = db.session.query(EvidenceTruthShadowArtifact).filter(
        EvidenceTruthShadowArtifact.store_slug == slug
    )
    if artifact_kind:
        q = q.filter(
            EvidenceTruthShadowArtifact.artifact_kind
            == artifact_kind.strip().lower()
        )
    return int(q.count() or 0)


def delete_shadow_artifacts_for_run_v1(
    *,
    materialization_run_id: str,
    store_slug: str = DEMO_STORE_SLUG,
) -> int:
    """
    Cleanup helper — deletes only artifacts for one run + demo store.

    Cannot delete unrelated stores. Returns deleted row count.
    """
    from models import EvidenceTruthShadowArtifact

    slug = assert_demo_store_slug_v1(store_slug)
    run_id = (materialization_run_id or "").strip()
    if not run_id:
        raise ValueError("materialization_run_id_required")
    db = _db()
    ensure_evidence_truth_materialization_schema(db)
    q = db.session.query(EvidenceTruthShadowArtifact).filter(
        EvidenceTruthShadowArtifact.store_slug == slug,
        EvidenceTruthShadowArtifact.materialization_run_id == run_id,
    )
    n = q.count()
    q.delete(synchronize_session=False)
    db.session.commit()
    return int(n or 0)


def delete_demo_shadow_artifacts_v1(*, confirm_store_slug: str) -> int:
    """Delete all demo shadow artifacts. Requires explicit confirm_store_slug=demo."""
    from models import EvidenceTruthShadowArtifact

    slug = assert_demo_store_slug_v1(confirm_store_slug)
    db = _db()
    ensure_evidence_truth_materialization_schema(db)
    q = db.session.query(EvidenceTruthShadowArtifact).filter(
        EvidenceTruthShadowArtifact.store_slug == slug
    )
    n = q.count()
    q.delete(synchronize_session=False)
    db.session.commit()
    return int(n or 0)


def save_materialization_run_v1(
    *,
    materialization_run_id: str,
    store_slug: str,
    mode: str,
    status: str,
    batch_limit: int,
    accounting: Mapping[str, Any],
    error: str = "",
    completed: bool = False,
) -> None:
    from models import EvidenceTruthMaterializationRun

    slug = assert_demo_store_slug_v1(store_slug)
    db = _db()
    ensure_evidence_truth_materialization_schema(db)
    row = (
        db.session.query(EvidenceTruthMaterializationRun)
        .filter(
            EvidenceTruthMaterializationRun.materialization_run_id
            == materialization_run_id
        )
        .first()
    )
    now = _utc_now()
    if row is None:
        row = EvidenceTruthMaterializationRun(
            materialization_run_id=materialization_run_id,
            store_slug=slug,
            mode=mode,
            status=status,
            batch_limit=int(batch_limit),
            composer_version=COMPOSER_VERSION_V1,
            accounting_json=json.dumps(dict(accounting), ensure_ascii=False, sort_keys=True),
            error_json=str(error or "")[:4000],
            created_at=now,
            completed_at=now if completed else None,
        )
        db.session.add(row)
    else:
        row.status = status
        row.mode = mode
        row.accounting_json = json.dumps(
            dict(accounting), ensure_ascii=False, sort_keys=True
        )
        row.error_json = str(error or "")[:4000]
        if completed:
            row.completed_at = now
    db.session.commit()


__all__ = [
    "ARTIFACT_BUNDLE",
    "ARTIFACT_EVIDENCE",
    "ARTIFACT_KNOWLEDGE",
    "ARTIFACT_OBSERVATION",
    "COMPOSER_VERSION_V1",
    "DEMO_STORE_SLUG",
    "assert_demo_store_slug_v1",
    "count_shadow_artifacts_v1",
    "delete_demo_shadow_artifacts_v1",
    "delete_shadow_artifacts_for_run_v1",
    "list_durable_knowledge_records_v1",
    "list_durable_knowledge_store_slugs_v1",
    "list_shadow_artifacts_v1",
    "put_shadow_artifact_v1",
    "save_materialization_run_v1",
]
