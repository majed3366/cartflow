# -*- coding: utf-8 -*-
"""
C-07 Canonical Observation store — WP-ET-03 shadow persistence.

In-process append-only store (Blueprint: new store and/or shadow table).
No DB migration in WP-ET-03. Durable SQL store may follow without changing
the observation contract.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional

from services.evidence_truth.observation_model_v1 import (
    CanonicalObservationV1,
    validate_observation_constitutional_metadata_v1,
)

_MAX_OBSERVATIONS = 5000


class CanonicalObservationStoreV1:
    """Thread-safe shadow observation store keyed by observation_id (idempotent)."""

    def __init__(self, *, max_entries: int = _MAX_OBSERVATIONS) -> None:
        self._lock = threading.Lock()
        self._max = max(1, int(max_entries))
        self._by_id: OrderedDict[str, CanonicalObservationV1] = OrderedDict()
        self._by_raw_ref: dict[str, str] = {}

    def reset(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_raw_ref.clear()

    def put(self, observation: CanonicalObservationV1) -> CanonicalObservationV1:
        """
        Insert or return existing observation for the same observation_id / raw_ref.

        Idempotent: duplicate raw_ref returns prior record without double-insert.
        Rejects Observations lacking constitutional metadata (WP-ET-04).
        """
        validate_observation_constitutional_metadata_v1(observation)
        with self._lock:
            existing_id = self._by_raw_ref.get(observation.raw_ref)
            if existing_id and existing_id in self._by_id:
                return self._by_id[existing_id]
            if observation.observation_id in self._by_id:
                return self._by_id[observation.observation_id]
            self._by_id[observation.observation_id] = observation
            self._by_raw_ref[observation.raw_ref] = observation.observation_id
            while len(self._by_id) > self._max:
                _oid, old = self._by_id.popitem(last=False)
                self._by_raw_ref.pop(old.raw_ref, None)
            return observation

    def get(self, observation_id: str) -> Optional[CanonicalObservationV1]:
        with self._lock:
            return self._by_id.get(observation_id)

    def get_by_raw_ref(self, raw_ref: str) -> Optional[CanonicalObservationV1]:
        with self._lock:
            oid = self._by_raw_ref.get(raw_ref)
            if not oid:
                return None
            return self._by_id.get(oid)

    def list_recent(self, *, limit: int = 100, store_slug: str = "") -> list[CanonicalObservationV1]:
        with self._lock:
            rows = list(self._by_id.values())
        if store_slug:
            slug = store_slug.strip().lower()
            rows = [r for r in rows if r.store_slug.lower() == slug]
        if limit > 0:
            rows = rows[-limit:]
        return rows

    def count(self, *, store_slug: str = "") -> int:
        with self._lock:
            if not store_slug:
                return len(self._by_id)
            slug = store_slug.strip().lower()
            return sum(1 for r in self._by_id.values() if r.store_slug.lower() == slug)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "count": len(self._by_id),
                "max_entries": self._max,
                "raw_refs": len(self._by_raw_ref),
            }


_GLOBAL_STORE = CanonicalObservationStoreV1()


def get_canonical_observation_store_v1() -> CanonicalObservationStoreV1:
    return _GLOBAL_STORE


def reset_canonical_observation_store_v1() -> None:
    _GLOBAL_STORE.reset()
