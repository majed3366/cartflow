# -*- coding: utf-8 -*-
"""
Executive Knowledge Preview — WP-ET-10.5 validation surface (READ ONLY).

Consumes Shadow Knowledge Records only.
Never reads Raw / Observation / Evidence Truth / Bundle stores.
Never writes. Never activates Home / Findings / Guidance.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.evidence_truth.knowledge_model_v1 import (
    KNOWLEDGE_TYPE_FAMILY_PRESENCE,
    KNOWLEDGE_TYPE_READY_FAMILY_SET,
    KnowledgeRecordV1,
)
from services.evidence_truth.knowledge_store_v1 import (
    KnowledgeRecordStoreV1,
    get_knowledge_record_store_v1,
)

FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW = "CARTFLOW_EXECUTIVE_KNOWLEDGE_PREVIEW"

_TRUE = frozenset({"1", "true", "yes", "on"})

# Readiness classes for executive honesty (mapped from Knowledge only)
_STABLE = frozenset({"ready", "trusted"})
_IMMATURE = frozenset({"unknown", "insufficient", "unavailable", "conflicting"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def executive_knowledge_preview_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    """Default OFF. Unknown/unset → False (fail closed)."""
    env = environ if environ is not None else os.environ
    raw = str(env.get(FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW, "") or "").strip().lower()
    return raw in _TRUE


def _pattern_label(knowledge_type: str) -> str:
    if knowledge_type == KNOWLEDGE_TYPE_FAMILY_PRESENCE:
        return "Family presence pattern"
    if knowledge_type == KNOWLEDGE_TYPE_READY_FAMILY_SET:
        return "Ready-family set pattern"
    return knowledge_type or "unknown_pattern"


def _maturity_bucket(readiness: str) -> str:
    r = (readiness or "").strip().lower()
    if r in _STABLE:
        return "stable"
    if r == "conflicting":
        return "conflicting"
    if r in {"insufficient", "unavailable"}:
        return "insufficient"
    return "immature"


def _project_record_for_preview(rec: KnowledgeRecordV1) -> dict[str, Any]:
    """
    Project Knowledge → preview DTO.

    No new facts. No recommendations. No business meaning.
    """
    summary = dict(rec.pattern_summary or {})
    maturity = _maturity_bucket(rec.readiness)
    claims = []
    for c in rec.claims:
        claims.append(
            {
                "claim_id": c.claim_id,
                "claim_kind": c.claim_kind,
                "readiness": c.readiness,
                "confidence": c.confidence,
                "evidence_ids": list(c.evidence_ids),
                "bundle_ids": list(c.bundle_ids),
                "payload": dict(c.payload or {}),
                "maturity": _maturity_bucket(c.readiness),
            }
        )

    what_known: list[str] = []
    if rec.knowledge_type == KNOWLEDGE_TYPE_FAMILY_PRESENCE:
        families = list(summary.get("families_present") or [])
        if families:
            what_known.append(
                "Evidence-backed family presence observed for: "
                + ", ".join(sorted(families))
            )
        else:
            what_known.append("No present families in this Knowledge record.")
    elif rec.knowledge_type == KNOWLEDGE_TYPE_READY_FAMILY_SET:
        ready = list(summary.get("ready_families") or [])
        if ready:
            what_known.append(
                "Ready-family set currently includes: " + ", ".join(sorted(ready))
            )
        else:
            what_known.append(
                "Ready-family set is empty — no family slice is Ready in supporting Bundle."
            )

    return {
        "knowledge_id": rec.knowledge_id,
        "knowledge_version": int(rec.knowledge_version),
        "knowledge_type": rec.knowledge_type,
        "pattern_label": _pattern_label(rec.knowledge_type),
        "store_slug": rec.store_slug,
        "as_of": rec.as_of,
        "window_start": rec.window_start,
        "window_end": rec.window_end,
        "readiness": rec.readiness,
        "confidence": rec.confidence,
        "maturity": maturity,
        "provenance": rec.provenance,
        "consumable": bool(rec.consumable),
        "bundle_ref_count": len(rec.bundle_refs),
        "evidence_ref_count": len(rec.evidence_refs),
        "claim_count": len(rec.claims),
        "bundle_ids": [b.bundle_id for b in rec.bundle_refs],
        "evidence_ids": [e.evidence_id for e in rec.evidence_refs],
        "pattern_summary": summary,
        "claims": claims,
        "what_cartflow_knows": what_known,
        "stable": maturity == "stable",
        "immature": maturity == "immature",
        "insufficient": maturity == "insufficient",
        "composition_notes": {
            "input": "shadow_knowledge_only",
            "findings": False,
            "guidance": False,
            "home": False,
        },
    }


def build_executive_knowledge_preview_v1(
    *,
    store_slug: str = "",
    limit: int = 50,
    environ: Mapping[str, str] | None = None,
    store: Optional[KnowledgeRecordStoreV1] = None,
) -> dict[str, Any]:
    """
    Read-only Executive Knowledge Preview payload.

    When flag OFF → disabled payload (callers should not render production UI).
    When flag ON and store empty → honest empty Knowledge state.
    """
    enabled = executive_knowledge_preview_enabled(environ=environ)
    base = {
        "schema": "executive_knowledge_preview_v1",
        "as_of": _utc_now_iso(),
        "flag": FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW,
        "flag_enabled": enabled,
        "preview": True,
        "validation_surface": True,
        "production_home": False,
        "read_only": True,
        "writes": False,
        "mutations": False,
        "input_authority": "shadow_knowledge_only",
        "forbidden_inputs": (
            "raw_event",
            "observation",
            "evidence_truth",
            "evidence_bundle",
        ),
        "consumers_activated": False,
        "findings_enabled": False,
        "guidance_enabled": False,
        "knowledge_composer_input_enabled": False,
    }
    if not enabled:
        return {
            **base,
            "ok": False,
            "reason": "flag_off",
            "empty": True,
            "stores": [],
            "records": [],
            "sections": {},
            "honesty": {
                "status": "preview_disabled",
                "message": (
                    "Executive Knowledge Preview is OFF "
                    f"({FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW} default OFF)."
                ),
            },
        }

    kstore = store or get_knowledge_record_store_v1()
    records = kstore.list_recent(limit=max(1, int(limit)), store_slug=store_slug or "")
    projected = [_project_record_for_preview(r) for r in records]

    stable = [p for p in projected if p.get("stable")]
    immature = [p for p in projected if p.get("immature")]
    insufficient = [p for p in projected if p.get("insufficient")]
    # Recent change: multiple versions / as_of ordering already newest-first
    recent = projected[:5]

    empty = len(projected) == 0
    honesty_msg = (
        "Knowledge has nothing to say yet — no Shadow Knowledge Records are available "
        "for this preview. Absence is shown honestly; nothing was fabricated."
        if empty
        else "Preview renders only Shadow Knowledge Records already composed by WP-ET-10."
    )

    return {
        **base,
        "ok": True,
        "reason": "ok",
        "empty": empty,
        "store_filter": (store_slug or "").strip().lower() or None,
        "stores": kstore.list_store_slugs(),
        "record_count": len(projected),
        "records": projected,
        "sections": {
            "what_cartflow_currently_knows": {
                "title": "What does CartFlow currently know?",
                "items": [
                    {
                        "store_slug": p["store_slug"],
                        "knowledge_id": p["knowledge_id"],
                        "statements": p["what_cartflow_knows"],
                        "readiness": p["readiness"],
                        "confidence": p["confidence"],
                    }
                    for p in projected
                ],
            },
            "stable_patterns": {
                "title": "Which patterns are stable?",
                "items": stable,
                "count": len(stable),
            },
            "immature_patterns": {
                "title": "Which patterns are still immature?",
                "items": immature,
                "count": len(immature),
            },
            "insufficient_evidence": {
                "title": "Where is evidence still insufficient?",
                "items": insufficient,
                "count": len(insufficient),
            },
            "what_changed_recently": {
                "title": "What changed recently?",
                "items": recent,
                "count": len(recent),
                "note": (
                    "Ordered by shadow store recency (newest first). "
                    "No invented deltas."
                ),
            },
        },
        "honesty": {
            "status": "empty_knowledge" if empty else "knowledge_present",
            "message": honesty_msg,
        },
    }
