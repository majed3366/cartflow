# -*- coding: utf-8 -*-
"""
Evidence Truth version store — WP-ET-05 shadow persistence.

In-process append-only versions (Blueprint: Evidence versions retained).
No DB migration. No consumer cutover.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional

from services.evidence_truth.evidence_model_v1 import (
    EvidenceTruthRecordV1,
    validate_evidence_constitutional_metadata_v1,
)

_MAX_VERSIONS = 5000


class EvidenceTruthStoreV1:
    """Thread-safe shadow Evidence version store."""

    def __init__(self, *, max_entries: int = _MAX_VERSIONS) -> None:
        self._lock = threading.Lock()
        self._max = max(1, int(max_entries))
        # key: evidence_id|version → record
        self._by_key: OrderedDict[str, EvidenceTruthRecordV1] = OrderedDict()
        # evidence_id → latest version
        self._latest: dict[str, int] = {}

    @staticmethod
    def _key(evidence_id: str, version: int) -> str:
        return f"{evidence_id}|{int(version)}"

    def reset(self) -> None:
        with self._lock:
            self._by_key.clear()
            self._latest.clear()

    def put(self, record: EvidenceTruthRecordV1) -> EvidenceTruthRecordV1:
        """
        Insert an immutable Evidence version.

        Idempotent for identical (evidence_id, version). Rejects incomplete
        constitutional metadata. Does not mutate prior versions.
        """
        validate_evidence_constitutional_metadata_v1(record)
        key = self._key(record.evidence_id, record.evidence_version)
        with self._lock:
            existing = self._by_key.get(key)
            if existing is not None:
                return existing
            self._by_key[key] = record
            cur = self._latest.get(record.evidence_id)
            if cur is None or int(record.evidence_version) >= int(cur):
                self._latest[record.evidence_id] = int(record.evidence_version)
            while len(self._by_key) > self._max:
                old_key, old = self._by_key.popitem(last=False)
                # Drop latest pointer only if it pointed at removed version
                if self._latest.get(old.evidence_id) == old.evidence_version:
                    # Find remaining max for that id
                    remaining = [
                        r.evidence_version
                        for r in self._by_key.values()
                        if r.evidence_id == old.evidence_id
                    ]
                    if remaining:
                        self._latest[old.evidence_id] = max(remaining)
                    else:
                        self._latest.pop(old.evidence_id, None)
            return record

    def get(
        self, evidence_id: str, *, version: Optional[int] = None
    ) -> Optional[EvidenceTruthRecordV1]:
        with self._lock:
            if version is None:
                ver = self._latest.get(evidence_id)
                if ver is None:
                    return None
                return self._by_key.get(self._key(evidence_id, ver))
            return self._by_key.get(self._key(evidence_id, int(version)))

    def list_recent(
        self,
        *,
        limit: int = 100,
        store_slug: str = "",
        family: str = "",
    ) -> list[EvidenceTruthRecordV1]:
        with self._lock:
            rows = list(self._by_key.values())
        if store_slug:
            slug = store_slug.strip().lower()
            rows = [r for r in rows if r.envelope.store_slug.lower() == slug]
        if family:
            fam = family.strip().lower()
            rows = [r for r in rows if r.canonical_family == fam]
        if limit > 0:
            rows = rows[-limit:]
        return rows

    def count(self, *, family: str = "") -> int:
        with self._lock:
            if not family:
                return len(self._by_key)
            fam = family.strip().lower()
            return sum(1 for r in self._by_key.values() if r.canonical_family == fam)

    def snapshot(self) -> dict:
        with self._lock:
            by_family: dict[str, int] = {}
            for r in self._by_key.values():
                by_family[r.canonical_family] = by_family.get(r.canonical_family, 0) + 1
            return {
                "count": len(self._by_key),
                "max_entries": self._max,
                "distinct_evidence_ids": len(self._latest),
                "by_family": by_family,
            }


_GLOBAL_EVIDENCE_STORE = EvidenceTruthStoreV1()


def get_evidence_truth_store_v1() -> EvidenceTruthStoreV1:
    return _GLOBAL_EVIDENCE_STORE


def reset_evidence_truth_store_v1() -> None:
    _GLOBAL_EVIDENCE_STORE.reset()
