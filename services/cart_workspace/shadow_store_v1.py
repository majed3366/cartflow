# -*- coding: utf-8 -*-
"""In-memory shadow store for Cart Workspace Sprint 1 — no DB schema migration."""
from __future__ import annotations

import threading
from typing import Any, Optional

from services.cart_workspace.contracts_v1 import DecisionRecord, OwnershipState, OwnershipTransitionAudit
from services.cart_workspace.ownership_v1 import default_ownership


class ShadowStoreV1:
    """Process-local store. Restart clears state (tests cover restart rebuild from empty)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ownership: dict[str, OwnershipState] = {}
        self._decisions: dict[str, DecisionRecord] = {}
        self._admission_ledger: list[dict[str, Any]] = []
        self._transition_audits: list[dict[str, Any]] = []
        self._closed_fingerprints: set[str] = set()
        self._completion_events: list[dict[str, Any]] = []
        self._projection_version: dict[str, int] = {}
        self._last_projection: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _own_key(store_slug: str, recovery_key: str) -> str:
        return f"{(store_slug or '').strip().lower()}::{(recovery_key or '').strip()}"

    def reset(self) -> None:
        with self._lock:
            self._ownership.clear()
            self._decisions.clear()
            self._admission_ledger.clear()
            self._transition_audits.clear()
            self._closed_fingerprints.clear()
            self._completion_events.clear()
            self._projection_version.clear()
            self._last_projection.clear()

    def get_ownership(self, store_slug: str, recovery_key: str) -> OwnershipState:
        with self._lock:
            key = self._own_key(store_slug, recovery_key)
            if key not in self._ownership:
                self._ownership[key] = default_ownership(store_slug, recovery_key)
            return self._ownership[key]

    def set_ownership(self, state: OwnershipState) -> None:
        with self._lock:
            self._ownership[self._own_key(state.store_slug, state.recovery_key)] = state

    def append_transition(self, audit: OwnershipTransitionAudit) -> None:
        with self._lock:
            self._transition_audits.append(audit.to_dict())

    def list_transitions(self, store_slug: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self._transition_audits)
        if store_slug:
            slug = store_slug.strip().lower()
            rows = [r for r in rows if (r.get("store_slug") or "").lower() == slug]
        return rows

    def append_admission(self, result_dict: dict[str, Any]) -> None:
        with self._lock:
            self._admission_ledger.append(result_dict)

    def list_admissions(self, store_slug: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self._admission_ledger)
        # AdmissionResult doesn't carry store_slug; filter via fingerprint callers if needed
        return rows

    def put_decision(self, decision: DecisionRecord) -> None:
        with self._lock:
            self._decisions[decision.decision_id] = decision

    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        with self._lock:
            return self._decisions.get(decision_id)

    def open_decisions(self, store_slug: str) -> list[DecisionRecord]:
        slug = (store_slug or "").strip().lower()
        with self._lock:
            return [
                d
                for d in self._decisions.values()
                if d.status == "open" and (d.store_slug or "").strip().lower() == slug
            ]

    def all_decisions(self, store_slug: str) -> list[DecisionRecord]:
        slug = (store_slug or "").strip().lower()
        with self._lock:
            return [
                d
                for d in self._decisions.values()
                if (d.store_slug or "").strip().lower() == slug
            ]

    def close_decision(self, decision_id: str, *, resolved_at: str) -> Optional[DecisionRecord]:
        with self._lock:
            d = self._decisions.get(decision_id)
            if not d or d.status != "open":
                return d
            d.status = "closed"
            d.resolved_at = resolved_at
            d.decision_owner = "cartflow"
            self._closed_fingerprints.add(d.evidence_fingerprint)
            return d

    def fingerprint_was_closed(self, fingerprint: str) -> bool:
        with self._lock:
            return fingerprint in self._closed_fingerprints

    def has_open_fingerprint(self, store_slug: str, recovery_key: str, fingerprint: str) -> bool:
        slug = (store_slug or "").strip().lower()
        rk = (recovery_key or "").strip()
        with self._lock:
            for d in self._decisions.values():
                if d.status != "open":
                    continue
                if (d.store_slug or "").strip().lower() != slug:
                    continue
                if (d.recovery_key or "").strip() != rk:
                    continue
                if d.evidence_fingerprint == fingerprint:
                    return True
        return False

    def merchant_has_open_decision(self, store_slug: str, recovery_key: str) -> bool:
        slug = (store_slug or "").strip().lower()
        rk = (recovery_key or "").strip()
        with self._lock:
            for d in self._decisions.values():
                if d.status == "open" and (d.store_slug or "").lower() == slug and d.recovery_key == rk:
                    return True
        return False

    def record_completion(self, store_slug: str, recovery_key: str, *, at: str) -> None:
        with self._lock:
            self._completion_events.append(
                {"store_slug": store_slug, "recovery_key": recovery_key, "at": at}
            )

    def completions(self, store_slug: str) -> list[dict[str, Any]]:
        slug = (store_slug or "").strip().lower()
        with self._lock:
            return [c for c in self._completion_events if (c.get("store_slug") or "").lower() == slug]

    def next_projection_version(self, store_slug: str) -> int:
        slug = (store_slug or "").strip().lower()
        with self._lock:
            v = int(self._projection_version.get(slug, 0)) + 1
            self._projection_version[slug] = v
            return v

    def current_projection_version(self, store_slug: str) -> int:
        slug = (store_slug or "").strip().lower()
        with self._lock:
            return int(self._projection_version.get(slug, 0))

    def save_projection(self, store_slug: str, projection: dict[str, Any]) -> None:
        slug = (store_slug or "").strip().lower()
        with self._lock:
            self._last_projection[slug] = projection

    def last_projection(self, store_slug: str) -> Optional[dict[str, Any]]:
        slug = (store_slug or "").strip().lower()
        with self._lock:
            return self._last_projection.get(slug)


# Process singleton for shadow endpoint + tests may construct their own.
SHADOW_STORE = ShadowStoreV1()
