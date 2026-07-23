# -*- coding: utf-8 -*-
"""
C-04 Evidence Accounting & No-Silent-Loss Auditor — WP-ET-02 skeleton.

In-process derived counters + append-only audit samples.
No production ingress wiring. Publishers (later WPs) call increment APIs.
"""
from __future__ import annotations

import threading
from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from services.evidence_truth.kernel_v1 import REJECT_REASON_CODES_V1

# Pipeline stages counted by C-04
STAGE_RAW_IN = "raw_in"
STAGE_OBSERVATION_OUT = "observation_out"
STAGE_EVIDENCE_OUT = "evidence_out"
STAGE_BUNDLE_PROJECTION_OUT = "bundle_projection_out"
STAGE_KNOWLEDGE_OUT = "knowledge_out"

PIPELINE_STAGES_V1: tuple[str, ...] = (
    STAGE_RAW_IN,
    STAGE_OBSERVATION_OUT,
    STAGE_EVIDENCE_OUT,
    STAGE_BUNDLE_PROJECTION_OUT,
    STAGE_KNOWLEDGE_OUT,
)

_MAX_AUDIT_SAMPLES = 200


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class EvidenceAccountingStateV1:
    stage_counts: dict[str, int] = field(
        default_factory=lambda: {s: 0 for s in PIPELINE_STAGES_V1}
    )
    rejected_by_reason: dict[str, int] = field(
        default_factory=lambda: {r: 0 for r in sorted(REJECT_REASON_CODES_V1)}
    )
    contract_violations: dict[str, int] = field(default_factory=dict)
    missing_ownership: int = 0
    in_flight: int = 0
    silent_loss_trips: int = 0
    last_event_at: str = ""


class EvidenceAccountingLedgerV1:
    """
    Thread-safe process-local accounting ledger (derived / ephemeral).

    Invariant (Blueprint §8): in >= out + rejected + in_flight
    where in = raw_in, out = observation_out (first durable governed step).
    Extended checks also track evidence_out vs observation_out.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = EvidenceAccountingStateV1()
        self._audit: deque[dict[str, Any]] = deque(maxlen=_MAX_AUDIT_SAMPLES)

    def reset(self) -> None:
        with self._lock:
            self._state = EvidenceAccountingStateV1()
            self._audit.clear()

    def increment_stage(self, stage: str, *, n: int = 1, detail: str = "") -> None:
        stage_key = (stage or "").strip()
        if stage_key not in PIPELINE_STAGES_V1:
            raise ValueError(f"unknown_accounting_stage:{stage!r}")
        if n < 0:
            raise ValueError("increment_must_be_non_negative")
        with self._lock:
            self._state.stage_counts[stage_key] = int(self._state.stage_counts[stage_key]) + int(n)
            self._state.last_event_at = _utc_now_iso()
            if detail:
                self._audit.append(
                    {
                        "kind": "stage_increment",
                        "stage": stage_key,
                        "n": int(n),
                        "detail": (detail or "")[:200],
                        "at": self._state.last_event_at,
                    }
                )

    def record_reject(self, reason_code: str, *, detail: str = "") -> None:
        code = (reason_code or "").strip()
        if code not in REJECT_REASON_CODES_V1:
            raise ValueError(f"unknown_reject_reason:{reason_code!r}")
        with self._lock:
            self._state.rejected_by_reason[code] = int(self._state.rejected_by_reason[code]) + 1
            self._state.last_event_at = _utc_now_iso()
            self._audit.append(
                {
                    "kind": "reject",
                    "reason_code": code,
                    "detail": (detail or "")[:200],
                    "at": self._state.last_event_at,
                }
            )

    def record_contract_violation(self, rule_id: str, *, detail: str = "") -> None:
        rid = (rule_id or "").strip().upper()
        if not rid:
            raise ValueError("rule_id_required")
        with self._lock:
            self._state.contract_violations[rid] = int(
                self._state.contract_violations.get(rid, 0)
            ) + 1
            self._state.last_event_at = _utc_now_iso()
            self._audit.append(
                {
                    "kind": "contract_violation",
                    "rule_id": rid,
                    "detail": (detail or "")[:200],
                    "at": self._state.last_event_at,
                }
            )

    def record_missing_ownership(self, *, detail: str = "") -> None:
        with self._lock:
            self._state.missing_ownership += 1
            self._state.last_event_at = _utc_now_iso()
            self._audit.append(
                {
                    "kind": "missing_ownership",
                    "detail": (detail or "")[:200],
                    "at": self._state.last_event_at,
                }
            )

    def set_in_flight(self, n: int) -> None:
        if n < 0:
            raise ValueError("in_flight_must_be_non_negative")
        with self._lock:
            self._state.in_flight = int(n)
            self._state.last_event_at = _utc_now_iso()

    def adjust_in_flight(self, delta: int) -> None:
        with self._lock:
            nxt = int(self._state.in_flight) + int(delta)
            if nxt < 0:
                raise ValueError("in_flight_cannot_go_negative")
            self._state.in_flight = nxt
            self._state.last_event_at = _utc_now_iso()

    def total_rejected(self) -> int:
        with self._lock:
            return int(sum(self._state.rejected_by_reason.values()))

    def check_invariants(self) -> dict[str, Any]:
        """
        Blueprint §8 accounting invariant:
          raw_in >= observation_out + rejected + in_flight
        Plus non-negative monotonic stage relationships for skeleton:
          observation_out >= evidence_out  (evidence cannot exceed observations)
          evidence_out >= bundle_projection_out
          bundle_projection_out >= knowledge_out
        """
        with self._lock:
            raw_in = int(self._state.stage_counts[STAGE_RAW_IN])
            obs = int(self._state.stage_counts[STAGE_OBSERVATION_OUT])
            ev = int(self._state.stage_counts[STAGE_EVIDENCE_OUT])
            bundle = int(self._state.stage_counts[STAGE_BUNDLE_PROJECTION_OUT])
            knowledge = int(self._state.stage_counts[STAGE_KNOWLEDGE_OUT])
            rejected = int(sum(self._state.rejected_by_reason.values()))
            in_flight = int(self._state.in_flight)

        primary_ok = raw_in >= (obs + rejected + in_flight)
        obs_ev_ok = obs >= ev
        ev_bundle_ok = ev >= bundle
        bundle_kn_ok = bundle >= knowledge
        ok = primary_ok and obs_ev_ok and ev_bundle_ok and bundle_kn_ok
        return {
            "ok": ok,
            "primary_invariant_ok": primary_ok,
            "observation_ge_evidence_ok": obs_ev_ok,
            "evidence_ge_bundle_ok": ev_bundle_ok,
            "bundle_ge_knowledge_ok": bundle_kn_ok,
            "raw_in": raw_in,
            "observation_out": obs,
            "evidence_out": ev,
            "bundle_projection_out": bundle,
            "knowledge_out": knowledge,
            "rejected": rejected,
            "in_flight": in_flight,
            "formula": "raw_in >= observation_out + rejected + in_flight",
        }

    def detect_silent_loss(self) -> dict[str, Any]:
        """
        Trip when primary invariant fails — P0 class (Blueprint §8.2).
        Does not mutate production truth; records trip counter.
        """
        inv = self.check_invariants()
        tripped = not bool(inv.get("primary_invariant_ok"))
        with self._lock:
            if tripped:
                self._state.silent_loss_trips += 1
                self._state.last_event_at = _utc_now_iso()
                self._audit.append(
                    {
                        "kind": "silent_loss_trip",
                        "detail": "primary_invariant_failed",
                        "at": self._state.last_event_at,
                        "snapshot": {
                            "raw_in": inv["raw_in"],
                            "observation_out": inv["observation_out"],
                            "rejected": inv["rejected"],
                            "in_flight": inv["in_flight"],
                        },
                    }
                )
            trips = int(self._state.silent_loss_trips)
        return {
            "tripped": tripped,
            "silent_loss_trips": trips,
            "invariant": inv,
            "alert_class": "P0" if tripped else None,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "stage_counts": dict(self._state.stage_counts),
                "rejected_by_reason": dict(self._state.rejected_by_reason),
                "rejected_total": int(sum(self._state.rejected_by_reason.values())),
                "contract_violations": dict(self._state.contract_violations),
                "missing_ownership": int(self._state.missing_ownership),
                "in_flight": int(self._state.in_flight),
                "silent_loss_trips": int(self._state.silent_loss_trips),
                "last_event_at": self._state.last_event_at,
                "audit_samples": list(self._audit),
            }


# Process-global ledger (zero traffic until later WPs increment)
_GLOBAL_LEDGER = EvidenceAccountingLedgerV1()


def get_evidence_accounting_ledger_v1() -> EvidenceAccountingLedgerV1:
    return _GLOBAL_LEDGER


def reset_evidence_accounting_ledger_v1() -> None:
    """Test / rollback helper — clears process counters."""
    _GLOBAL_LEDGER.reset()


def evidence_accounting_snapshot_v1() -> dict[str, Any]:
    return _GLOBAL_LEDGER.snapshot()
