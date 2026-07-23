# -*- coding: utf-8 -*-
"""
Evidence Bundle shadow store — WP-ET-09.

In-process projection cache (Blueprint: disposable). No consumer cutover.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional

from services.evidence_truth.bundle_model_v1 import (
    EvidenceBundleRecordV1,
    validate_evidence_bundle_constitutional_v1,
)

_MAX_BUNDLES = 2000


class EvidenceBundleStoreV1:
    """Thread-safe shadow Bundle projection store."""

    def __init__(self, *, max_entries: int = _MAX_BUNDLES) -> None:
        self._lock = threading.Lock()
        self._max = max(1, int(max_entries))
        self._by_id: OrderedDict[str, EvidenceBundleRecordV1] = OrderedDict()
        # store_slug → latest bundle_id
        self._latest_by_store: dict[str, str] = {}

    def reset(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._latest_by_store.clear()

    def put(self, bundle: EvidenceBundleRecordV1) -> EvidenceBundleRecordV1:
        validate_evidence_bundle_constitutional_v1(bundle)
        with self._lock:
            existing = self._by_id.get(bundle.bundle_id)
            if existing is not None:
                # EB-6: identical id is idempotent; version bump replaces
                if int(existing.bundle_version) == int(bundle.bundle_version):
                    return existing
            self._by_id[bundle.bundle_id] = bundle
            self._by_id.move_to_end(bundle.bundle_id)
            slug = (bundle.store_slug or "").strip().lower()
            if slug:
                self._latest_by_store[slug] = bundle.bundle_id
            while len(self._by_id) > self._max:
                old_id, old = self._by_id.popitem(last=False)
                if self._latest_by_store.get((old.store_slug or "").strip().lower()) == old_id:
                    self._latest_by_store.pop(
                        (old.store_slug or "").strip().lower(), None
                    )
            return bundle

    def get(self, bundle_id: str) -> Optional[EvidenceBundleRecordV1]:
        with self._lock:
            return self._by_id.get(bundle_id)

    def latest_for_store(self, store_slug: str) -> Optional[EvidenceBundleRecordV1]:
        slug = (store_slug or "").strip().lower()
        with self._lock:
            bid = self._latest_by_store.get(slug)
            if not bid:
                return None
            return self._by_id.get(bid)

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


_GLOBAL_BUNDLE_STORE = EvidenceBundleStoreV1()


def get_evidence_bundle_store_v1() -> EvidenceBundleStoreV1:
    return _GLOBAL_BUNDLE_STORE


def reset_evidence_bundle_store_v1() -> None:
    _GLOBAL_BUNDLE_STORE.reset()
