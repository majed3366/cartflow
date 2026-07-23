# -*- coding: utf-8 -*-
"""
Knowledge Record shadow store — WP-ET-10.

In-process projection store. No consumer cutover. No Home wiring.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional

from services.evidence_truth.knowledge_model_v1 import (
    KnowledgeRecordV1,
    validate_knowledge_record_constitutional_v1,
)

_MAX_KNOWLEDGE = 2000


class KnowledgeRecordStoreV1:
    """Thread-safe shadow Knowledge store."""

    def __init__(self, *, max_entries: int = _MAX_KNOWLEDGE) -> None:
        self._lock = threading.Lock()
        self._max = max(1, int(max_entries))
        self._by_id: OrderedDict[str, KnowledgeRecordV1] = OrderedDict()
        self._latest_by_store: dict[str, str] = {}

    def reset(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._latest_by_store.clear()

    def put(self, record: KnowledgeRecordV1) -> KnowledgeRecordV1:
        validate_knowledge_record_constitutional_v1(record)
        with self._lock:
            existing = self._by_id.get(record.knowledge_id)
            if existing is not None and int(existing.knowledge_version) == int(
                record.knowledge_version
            ):
                return existing
            self._by_id[record.knowledge_id] = record
            self._by_id.move_to_end(record.knowledge_id)
            slug = (record.store_slug or "").strip().lower()
            if slug:
                self._latest_by_store[slug] = record.knowledge_id
            while len(self._by_id) > self._max:
                old_id, old = self._by_id.popitem(last=False)
                key = (old.store_slug or "").strip().lower()
                if self._latest_by_store.get(key) == old_id:
                    self._latest_by_store.pop(key, None)
            return record

    def get(self, knowledge_id: str) -> Optional[KnowledgeRecordV1]:
        with self._lock:
            return self._by_id.get(knowledge_id)

    def latest_for_store(self, store_slug: str) -> Optional[KnowledgeRecordV1]:
        slug = (store_slug or "").strip().lower()
        with self._lock:
            kid = self._latest_by_store.get(slug)
            if not kid:
                return None
            return self._by_id.get(kid)

    def list_recent(
        self,
        *,
        limit: int = 100,
        store_slug: str = "",
    ) -> list[KnowledgeRecordV1]:
        """Read-only listing for validation surfaces (WP-ET-10.5)."""
        with self._lock:
            rows = list(self._by_id.values())
        if store_slug:
            slug = store_slug.strip().lower()
            rows = [r for r in rows if (r.store_slug or "").strip().lower() == slug]
        # Newest last in OrderedDict insertion order — return newest-first
        rows = list(reversed(rows))
        if limit > 0:
            rows = rows[: int(limit)]
        return rows

    def list_store_slugs(self) -> list[str]:
        with self._lock:
            return sorted(self._latest_by_store.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._by_id)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "count": len(self._by_id),
                "max_entries": self._max,
                "stores": len(self._latest_by_store),
            }


_GLOBAL_KNOWLEDGE_STORE = KnowledgeRecordStoreV1()


def get_knowledge_record_store_v1() -> KnowledgeRecordStoreV1:
    return _GLOBAL_KNOWLEDGE_STORE


def reset_knowledge_record_store_v1() -> None:
    _GLOBAL_KNOWLEDGE_STORE.reset()
