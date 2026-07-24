# -*- coding: utf-8 -*-
"""
EvidenceKnowledgeMaterializationOrchestratorV1 — WP-ET-10.6.

Coordinates approved composers only:
  Observation → Evidence → Bundle → Knowledge

Bounded, idempotent, resumable, demo-only. No Home / Findings / Guidance.
No merchant hot-path execution. No real outbound provider calls.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.evidence_truth.bundle_shadow_compose_v1 import (
    maybe_compose_evidence_bundle_v1,
)
from services.evidence_truth.durable_shadow_store_v1 import (
    ARTIFACT_BUNDLE,
    ARTIFACT_EVIDENCE,
    ARTIFACT_KNOWLEDGE,
    ARTIFACT_OBSERVATION,
    COMPOSER_VERSION_V1,
    DEMO_STORE_SLUG,
    assert_demo_store_slug_v1,
    put_shadow_artifact_v1,
    save_materialization_run_v1,
)
from services.evidence_truth.evidence_dual_write_v1 import shadow_dual_write_evidence_v1
from services.evidence_truth.evidence_store_v1 import get_evidence_truth_store_v1
from services.evidence_truth.knowledge_model_v1 import KNOWLEDGE_TYPE_FAMILY_PRESENCE
from services.evidence_truth.knowledge_shadow_compose_v1 import (
    maybe_compose_knowledge_record_v1,
)
from services.evidence_truth.materialization_flags_v1 import (
    FLAG_KNOWLEDGE_MATERIALIZATION_EXECUTE,
    FLAG_KNOWLEDGE_MATERIALIZATION_V1,
    knowledge_materialization_execute_enabled,
    knowledge_materialization_v1_enabled,
)
from services.evidence_truth.materialization_input_contract_v1 import (
    discover_materialization_sources_v1,
)
from services.evidence_truth.observation_store_v1 import (
    get_canonical_observation_store_v1,
)

log = logging.getLogger("cartflow.evidence_truth")

MODE_DRY_RUN = "dry_run"
MODE_EXECUTE = "execute"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_run_id() -> str:
    return f"mat_{uuid.uuid4().hex[:20]}"


def _empty_stage_counts() -> dict[str, int]:
    return {
        "created": 0,
        "reused": 0,
        "failed": 0,
        "insufficient": 0,
        "suppressed": 0,
    }


class EvidenceKnowledgeMaterializationOrchestratorV1:
    """Governed demo materialization orchestrator (no new BI logic)."""

    def run(
        self,
        *,
        store_slug: str,
        mode: str = MODE_DRY_RUN,
        batch_limit: int = 50,
        materialization_run_id: str = "",
        include_validation_fixtures: bool = False,
        fixture_count: int = 2,
        force: bool = False,
        environ: Mapping[str, str] | None = None,
        as_of: str = "",
    ) -> dict[str, Any]:
        """
        Execute one bounded materialization run.

        ``force=True`` bypasses materialization flags (tests only).
        """
        run_id = (materialization_run_id or "").strip() or _new_run_id()
        mode_norm = (mode or MODE_DRY_RUN).strip().lower()
        if mode_norm not in {MODE_DRY_RUN, MODE_EXECUTE}:
            return self._fail(
                run_id=run_id,
                store_slug=store_slug,
                mode=mode_norm,
                batch_limit=batch_limit,
                error=f"invalid_mode:{mode_norm}",
            )

        try:
            slug = assert_demo_store_slug_v1(store_slug)
        except ValueError as exc:
            return self._fail(
                run_id=run_id,
                store_slug=store_slug,
                mode=mode_norm,
                batch_limit=batch_limit,
                error=str(exc),
                abort_non_demo=True,
            )

        if not force and not knowledge_materialization_v1_enabled(environ=environ):
            return {
                "ok": False,
                "skipped": True,
                "reason": "flag_off",
                "flag": FLAG_KNOWLEDGE_MATERIALIZATION_V1,
                "materialization_run_id": run_id,
                "store_slug": slug,
                "mode": mode_norm,
                "mutations": False,
            }

        if mode_norm == MODE_EXECUTE and not force:
            if not knowledge_materialization_execute_enabled(environ=environ):
                return {
                    "ok": False,
                    "skipped": True,
                    "reason": "execute_flag_off",
                    "flag": FLAG_KNOWLEDGE_MATERIALIZATION_EXECUTE,
                    "materialization_run_id": run_id,
                    "store_slug": slug,
                    "mode": mode_norm,
                    "mutations": False,
                }

        discovery = discover_materialization_sources_v1(
            store_slug=slug,
            batch_limit=batch_limit,
            include_validation_fixtures=include_validation_fixtures,
            fixture_count=fixture_count,
        )

        accounting: dict[str, Any] = {
            "source_records_discovered": discovery.discovered,
            "source_records_eligible": len(discovery.eligible),
            "source_records_unsupported": len(discovery.unsupported),
            "source_records_duplicated": len(discovery.duplicated),
            "source_records_rejected": len(discovery.rejected),
            "observations": _empty_stage_counts(),
            "evidence": _empty_stage_counts(),
            "bundles": _empty_stage_counts(),
            "knowledge": _empty_stage_counts(),
            "source_outcomes": [],
            "suppressed": [],
            "traceability": [],
            "composer_version": COMPOSER_VERSION_V1,
            "outbound_calls": 0,
            "findings_activated": False,
            "guidance_activated": False,
            "home_cutover": False,
        }

        # Discovery accounting must balance
        accounted = (
            accounting["source_records_eligible"]
            + accounting["source_records_unsupported"]
            + accounting["source_records_duplicated"]
            + accounting["source_records_rejected"]
        )
        accounting["discovery_balanced"] = accounted == discovery.discovered

        if mode_norm == MODE_DRY_RUN:
            accounting["observations"]["created"] = len(discovery.eligible)
            accounting["evidence"]["created"] = len(discovery.eligible)
            accounting["bundles"]["created"] = 1 if discovery.eligible else 0
            accounting["knowledge"]["created"] = 1 if discovery.eligible else 0
            report = {
                "ok": True,
                "skipped": False,
                "dry_run": True,
                "mutations": False,
                "materialization_run_id": run_id,
                "store_slug": slug,
                "mode": MODE_DRY_RUN,
                "batch_limit": int(batch_limit),
                "composer_version": COMPOSER_VERSION_V1,
                "as_of": as_of or _utc_now_iso(),
                "discovery": discovery.to_dict(),
                "accounting": accounting,
                "expected_writes": {
                    "observations": len(discovery.eligible),
                    "evidence": len(discovery.eligible),
                    "bundles": 1 if discovery.eligible else 0,
                    "knowledge": 1 if discovery.eligible else 0,
                },
                "note": "DRY RUN — no durable mutation; composers not executed",
            }
            try:
                save_materialization_run_v1(
                    materialization_run_id=run_id,
                    store_slug=slug,
                    mode=MODE_DRY_RUN,
                    status="dry_run_complete",
                    batch_limit=batch_limit,
                    accounting=accounting,
                    completed=True,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("materialization dry_run ledger save failed: %s", exc)
            return report

        # EXECUTE
        try:
            save_materialization_run_v1(
                materialization_run_id=run_id,
                store_slug=slug,
                mode=MODE_EXECUTE,
                status="started",
                batch_limit=batch_limit,
                accounting=accounting,
            )
        except Exception as exc:  # noqa: BLE001
            return self._fail(
                run_id=run_id,
                store_slug=slug,
                mode=mode_norm,
                batch_limit=batch_limit,
                error=f"run_ledger_failed:{exc}",
            )

        obs_store = get_canonical_observation_store_v1()
        for cand in discovery.eligible:
            if cand.store_slug != DEMO_STORE_SLUG:
                return self._fail(
                    run_id=run_id,
                    store_slug=slug,
                    mode=mode_norm,
                    batch_limit=batch_limit,
                    error=f"non_demo_escape:{cand.store_slug}",
                    abort_non_demo=True,
                    accounting=accounting,
                )
            outcome = self._materialize_source(
                cand=cand,
                run_id=run_id,
                accounting=accounting,
            )
            accounting["source_outcomes"].append(outcome)

        # Bundle + Knowledge (store-level, after source batch)
        bundle_out = self._compose_bundle_stage(
            store_slug=slug,
            run_id=run_id,
            as_of=as_of,
            accounting=accounting,
            environ=environ,
        )
        knowledge_out = self._compose_knowledge_stage(
            store_slug=slug,
            run_id=run_id,
            as_of=as_of,
            accounting=accounting,
            environ=environ,
            bundle_id=str(bundle_out.get("bundle_id") or ""),
        )

        status = "completed"
        if accounting["observations"]["failed"] or accounting["evidence"]["failed"]:
            status = "completed_with_failures"

        report = {
            "ok": True,
            "skipped": False,
            "dry_run": False,
            "mutations": True,
            "materialization_run_id": run_id,
            "store_slug": slug,
            "mode": MODE_EXECUTE,
            "batch_limit": int(batch_limit),
            "composer_version": COMPOSER_VERSION_V1,
            "as_of": as_of or _utc_now_iso(),
            "status": status,
            "discovery": discovery.to_dict(),
            "accounting": accounting,
            "bundle": bundle_out,
            "knowledge": knowledge_out,
            "in_process_observation_count": obs_store.count(store_slug=slug),
            "in_process_evidence_count": len(
                get_evidence_truth_store_v1().list_recent(
                    limit=500, store_slug=slug
                )
            ),
        }
        try:
            save_materialization_run_v1(
                materialization_run_id=run_id,
                store_slug=slug,
                mode=MODE_EXECUTE,
                status=status,
                batch_limit=batch_limit,
                accounting=accounting,
                completed=True,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("materialization execute ledger save failed: %s", exc)
            report["ledger_warning"] = str(exc)
        return report

    def _materialize_source(
        self,
        *,
        cand: Any,
        run_id: str,
        accounting: dict[str, Any],
    ) -> dict[str, Any]:
        """Observation + Evidence for one source via approved dual-write (force)."""
        outcome: dict[str, Any] = {
            "source_type": cand.source_type,
            "source_id": cand.source_id,
            "dedupe_key": cand.dedupe_key,
            "stage_stopped": None,
            "observation_id": "",
            "evidence_id": "",
        }
        try:
            ev = shadow_dual_write_evidence_v1(
                raw_kind=cand.raw_kind,
                payload=dict(cand.payload or {}),
                source_channel=cand.source_channel,
                source=f"materialization:{cand.source_type}:{cand.source_id}",
                force=True,
            )
        except Exception as exc:  # noqa: BLE001
            accounting["observations"]["failed"] += 1
            accounting["evidence"]["failed"] += 1
            outcome["stage_stopped"] = "observation"
            outcome["error"] = str(exc)
            return outcome

        if ev.get("rejected") or not ev.get("ok"):
            reason = str(ev.get("reason_code") or ev.get("detail") or "rejected")
            # Observation may have failed inside ensure
            if "observation" in str(ev.get("detail") or "").lower() or not ev.get(
                "observation_id"
            ):
                accounting["observations"]["failed"] += 1
                outcome["stage_stopped"] = "observation"
            else:
                accounting["observations"]["reused"] += 1
                accounting["evidence"]["failed"] += 1
                outcome["stage_stopped"] = "evidence"
            if reason in {"conflict_unresolved"}:
                accounting["suppressed"].append(
                    {
                        "source_id": cand.source_id,
                        "reason": reason,
                        "stage": outcome["stage_stopped"],
                    }
                )
            outcome["error"] = reason
            outcome["detail"] = ev
            return outcome

        oid = str(ev.get("observation_id") or "")
        eid = str(ev.get("evidence_id") or "")
        outcome["observation_id"] = oid
        outcome["evidence_id"] = eid

        obs = get_canonical_observation_store_v1().get(oid) if oid else None
        if obs is None:
            accounting["observations"]["failed"] += 1
            outcome["stage_stopped"] = "observation"
            outcome["error"] = "observation_missing_after_dual_write"
            return outcome

        obs_key = f"obs:{cand.dedupe_key}"
        obs_put = put_shadow_artifact_v1(
            artifact_kind=ARTIFACT_OBSERVATION,
            artifact_id=obs.observation_id,
            store_slug=DEMO_STORE_SLUG,
            materialization_run_id=run_id,
            idempotency_key=obs_key,
            payload=obs.to_dict(),
            lineage={
                **dict(cand.lineage or {}),
                "materialization_run_id": run_id,
                "raw_ref": obs.raw_ref,
                "source_timestamps": cand.observed_at,
            },
            source_ref=obs.raw_ref,
        )
        if obs_put.get("created"):
            accounting["observations"]["created"] += 1
        else:
            accounting["observations"]["reused"] += 1

        evid = get_evidence_truth_store_v1().get(eid) if eid else None
        if evid is None:
            accounting["evidence"]["failed"] += 1
            outcome["stage_stopped"] = "evidence"
            outcome["error"] = "evidence_missing_after_dual_write"
            return outcome

        # Insufficient evidence honesty
        if str(evid.readiness or "").lower() in {"insufficient", "unavailable"}:
            accounting["evidence"]["insufficient"] += 1

        ev_key = f"ev:{cand.dedupe_key}"
        ev_put = put_shadow_artifact_v1(
            artifact_kind=ARTIFACT_EVIDENCE,
            artifact_id=evid.evidence_id,
            store_slug=DEMO_STORE_SLUG,
            materialization_run_id=run_id,
            idempotency_key=ev_key,
            payload=evid.to_dict(),
            lineage={
                **dict(cand.lineage or {}),
                "materialization_run_id": run_id,
                "observation_id": oid,
                "evidence_version": evid.evidence_version,
                "source_timestamps": cand.observed_at,
            },
            source_ref=obs.raw_ref,
            artifact_version=int(evid.evidence_version or 1),
        )
        if ev_put.get("created"):
            accounting["evidence"]["created"] += 1
        else:
            accounting["evidence"]["reused"] += 1

        if ev.get("duplicated") and not ev_put.get("created"):
            # Idempotent resume path
            pass

        accounting["traceability"].append(
            {
                "source_type": cand.source_type,
                "source_id": cand.source_id,
                "source_timestamp": cand.observed_at,
                "observation_id": oid,
                "evidence_id": eid,
                "materialization_run_id": run_id,
                "idempotency_keys": {"observation": obs_key, "evidence": ev_key},
            }
        )
        outcome["stage_stopped"] = None
        outcome["ok"] = True
        return outcome

    def _compose_bundle_stage(
        self,
        *,
        store_slug: str,
        run_id: str,
        as_of: str,
        accounting: dict[str, Any],
        environ: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        if accounting["evidence"]["created"] + accounting["evidence"]["reused"] < 1:
            accounting["bundles"]["suppressed"] += 1
            accounting["suppressed"].append(
                {"stage": "bundle", "reason": "no_evidence_in_batch"}
            )
            return {"ok": False, "reason": "no_evidence_in_batch"}

        out = maybe_compose_evidence_bundle_v1(
            store_slug=store_slug,
            as_of=as_of or _utc_now_iso(),
            force=True,
            persist=True,
            environ=environ or {},
            provenance=f"materialization:{run_id}",
        )
        if not out.get("ok"):
            accounting["bundles"]["failed"] += 1
            accounting["suppressed"].append(
                {
                    "stage": "bundle",
                    "reason": out.get("reason") or out.get("message") or "bundle_failed",
                }
            )
            return out

        bundle = out.get("bundle") or {}
        bid = str(out.get("bundle_id") or bundle.get("bundle_id") or "")
        bver = int(out.get("bundle_version") or bundle.get("bundle_version") or 1)
        idem = f"bundle:{store_slug}:{bid}:{bver}"
        put = put_shadow_artifact_v1(
            artifact_kind=ARTIFACT_BUNDLE,
            artifact_id=bid,
            store_slug=DEMO_STORE_SLUG,
            materialization_run_id=run_id,
            idempotency_key=idem,
            payload=dict(bundle),
            lineage={
                "materialization_run_id": run_id,
                "store_slug": store_slug,
                "evidence_ref_count": out.get("evidence_ref_count"),
                "composer_version": COMPOSER_VERSION_V1,
            },
            artifact_version=bver,
        )
        if put.get("created"):
            accounting["bundles"]["created"] += 1
        else:
            accounting["bundles"]["reused"] += 1
        return out

    def _compose_knowledge_stage(
        self,
        *,
        store_slug: str,
        run_id: str,
        as_of: str,
        accounting: dict[str, Any],
        environ: Mapping[str, str] | None,
        bundle_id: str,
    ) -> dict[str, Any]:
        if accounting["bundles"]["created"] + accounting["bundles"]["reused"] < 1:
            accounting["knowledge"]["suppressed"] += 1
            accounting["suppressed"].append(
                {"stage": "knowledge", "reason": "no_bundle"}
            )
            return {"ok": False, "reason": "no_bundle"}

        out = maybe_compose_knowledge_record_v1(
            store_slug=store_slug,
            knowledge_type=KNOWLEDGE_TYPE_FAMILY_PRESENCE,
            bundle_ids=[bundle_id] if bundle_id else None,
            as_of=as_of or _utc_now_iso(),
            force=True,
            persist=True,
            environ=environ or {},
            provenance=f"materialization:{run_id}",
        )
        if not out.get("ok"):
            reason = str(out.get("reason") or out.get("message") or "knowledge_failed")
            if "insufficient" in reason.lower() or reason == "missing_sources":
                accounting["knowledge"]["suppressed"] += 1
                accounting["suppressed"].append(
                    {"stage": "knowledge", "reason": reason}
                )
            else:
                accounting["knowledge"]["failed"] += 1
            return out

        record = out.get("record") or {}
        kid = str(out.get("knowledge_id") or record.get("knowledge_id") or "")
        kver = int(
            out.get("knowledge_version") or record.get("knowledge_version") or 1
        )
        readiness = str(out.get("readiness") or record.get("readiness") or "")
        if readiness.lower() in {"insufficient", "unavailable", "unknown"}:
            # Honest immature Knowledge — still persisted, flagged
            accounting["suppressed"].append(
                {
                    "stage": "knowledge",
                    "reason": f"readiness_{readiness}",
                    "knowledge_id": kid,
                    "persisted": True,
                }
            )

        idem = f"knowledge:{store_slug}:{kid}:{kver}"
        put = put_shadow_artifact_v1(
            artifact_kind=ARTIFACT_KNOWLEDGE,
            artifact_id=kid,
            store_slug=DEMO_STORE_SLUG,
            materialization_run_id=run_id,
            idempotency_key=idem,
            payload=dict(record),
            lineage={
                "materialization_run_id": run_id,
                "store_slug": store_slug,
                "bundle_id": bundle_id,
                "composer_version": COMPOSER_VERSION_V1,
                "created_at": _utc_now_iso(),
            },
            artifact_version=kver,
        )
        if put.get("created"):
            accounting["knowledge"]["created"] += 1
        else:
            accounting["knowledge"]["reused"] += 1

        # Enrich last traceability rows with knowledge/bundle
        for row in accounting["traceability"]:
            row["bundle_id"] = bundle_id
            row["knowledge_id"] = kid
        return out

    def _fail(
        self,
        *,
        run_id: str,
        store_slug: str,
        mode: str,
        batch_limit: int,
        error: str,
        abort_non_demo: bool = False,
        accounting: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload = {
            "ok": False,
            "skipped": False,
            "materialization_run_id": run_id,
            "store_slug": store_slug,
            "mode": mode,
            "batch_limit": int(batch_limit),
            "error": error,
            "abort_non_demo": abort_non_demo,
            "mutations": False,
            "accounting": accounting or {},
        }
        if abort_non_demo:
            log.error("materialization STOP non-demo: %s", error)
        try:
            if (store_slug or "").strip().lower() == DEMO_STORE_SLUG:
                save_materialization_run_v1(
                    materialization_run_id=run_id,
                    store_slug=DEMO_STORE_SLUG,
                    mode=mode,
                    status="aborted",
                    batch_limit=batch_limit,
                    accounting=accounting or {},
                    error=error,
                    completed=True,
                )
        except Exception:  # noqa: BLE001
            pass
        return payload


def run_evidence_knowledge_materialization_v1(**kwargs: Any) -> dict[str, Any]:
    """Module-level entrypoint for CLI / tests."""
    return EvidenceKnowledgeMaterializationOrchestratorV1().run(**kwargs)


__all__ = [
    "MODE_DRY_RUN",
    "MODE_EXECUTE",
    "EvidenceKnowledgeMaterializationOrchestratorV1",
    "run_evidence_knowledge_materialization_v1",
]
