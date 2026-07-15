# -*- coding: utf-8 -*-
"""Deterministic random seed helpers — Phase 2."""
from __future__ import annotations

import hashlib
import random
from typing import Any


def normalize_seed(seed: Any) -> int:
    if seed is None:
        return 0
    if isinstance(seed, bool):
        return int(seed)
    if isinstance(seed, int):
        return int(seed)
    raw = str(seed).strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)


def make_rng(seed: int) -> random.Random:
    return random.Random(normalize_seed(seed))


def derive_subseed(*parts: Any) -> int:
    """Deterministic child seed from parent seed + parts."""
    material = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)
