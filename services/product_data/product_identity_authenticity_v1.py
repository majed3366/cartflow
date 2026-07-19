# -*- coding: utf-8 -*-
"""
Product Identity Authenticity V1 — merchant-facing identity gates (IF / AR).

Never fabricates product identity. Fixtures remain for explicit review/dev only.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, MutableMapping, Optional

ENGINE_MARK = "product_identity_authenticity_v1"

# Merchant-forbidden placeholder labels (AR-2).
_FORBIDDEN_NAME_RE = re.compile(
    r"(?:"
    r"منتج\s*[XABCأابب]"
    r"|Product\s*[XABC]"
    r"|منتج\s*مقارن"
    r"|prod_[xabc]\b"
    r")",
    re.IGNORECASE,
)

_FIXTURE_LOADED_FROM = frozenset(
    {
        "demo_rich_fixture_v1",
        "insufficient_fixture_v1",
        "conflicting_fixture_v1",
        "fixture",
        "findings_engine_demo_fixture",
    }
)


def is_fixture_loaded_from(loaded_from: Any) -> bool:
    raw = str(loaded_from or "").strip().lower()
    if not raw:
        return False
    if raw in _FIXTURE_LOADED_FROM:
        return True
    if "demo_rich_fixture" in raw or "fixture_v1" in raw:
        return True
    if raw.startswith("findings_engine_demo"):
        return True
    return False


def text_has_forbidden_product_placeholder(text: Any) -> bool:
    s = str(text or "").strip()
    if not s:
        return False
    return bool(_FORBIDDEN_NAME_RE.search(s))


def finding_has_forbidden_placeholder(finding: Mapping[str, Any]) -> bool:
    for key in (
        "title",
        "merchant_summary",
        "evidence_summary",
        "scope_reference",
        "commercial_answer_ar",
        "name_ar",
    ):
        if text_has_forbidden_product_placeholder(finding.get(key)):
            return True
    return False


def package_evidence_loaded_from(package: Mapping[str, Any]) -> str:
    ev = package.get("evidence")
    if isinstance(ev, Mapping):
        return str(ev.get("loaded_from") or "").strip()
    return str(package.get("evidence_loaded_from") or "").strip()


def sanitize_findings_package_for_merchant_v1(
    package: Mapping[str, Any],
    *,
    admit_review_fixtures: bool = False,
) -> dict[str, Any]:
    """
    Return a merchant-safe findings package.

    When ``admit_review_fixtures`` is False (default):
    - Fixture-sourced packages yield zero findings (honest empty).
    - Any finding with placeholder product identity is dropped.
    """
    out: dict[str, Any] = dict(package) if isinstance(package, Mapping) else {}
    findings_in = [
        f for f in list(out.get("findings") or []) if isinstance(f, Mapping)
    ]
    loaded = package_evidence_loaded_from(out)
    meta = {
        "engine": ENGINE_MARK,
        "admit_review_fixtures": bool(admit_review_fixtures),
        "evidence_loaded_from": loaded or None,
        "fixture_blocked": False,
        "placeholders_removed": 0,
        "findings_in": len(findings_in),
        "findings_out": 0,
    }

    if not admit_review_fixtures and is_fixture_loaded_from(loaded):
        meta["fixture_blocked"] = True
        out["findings"] = []
        out["home_candidates_v1"] = []
        meta["findings_out"] = 0
        out["product_identity_authenticity_v1"] = meta
        return out

    kept: list[dict[str, Any]] = []
    removed = 0
    for f in findings_in:
        if not admit_review_fixtures and finding_has_forbidden_placeholder(f):
            removed += 1
            continue
        kept.append(dict(f))
    meta["placeholders_removed"] = removed
    meta["findings_out"] = len(kept)
    out["findings"] = kept
    # Drop home candidates that reference removed finding ids
    kept_ids = {
        str(f.get("finding_id") or "").strip() for f in kept if f.get("finding_id")
    }
    hc = out.get("home_candidates_v1")
    if isinstance(hc, list) and kept_ids:
        out["home_candidates_v1"] = [
            c
            for c in hc
            if isinstance(c, Mapping)
            and str(c.get("finding_id") or c.get("id") or "").strip() in kept_ids
        ]
    elif isinstance(hc, list) and not kept:
        out["home_candidates_v1"] = []
    out["product_identity_authenticity_v1"] = meta
    return out


def merchant_package_is_authentic_v1(package: Mapping[str, Any]) -> bool:
    """True when package has no fixture provenance and no placeholder findings."""
    if is_fixture_loaded_from(package_evidence_loaded_from(package)):
        return False
    for f in list(package.get("findings") or []):
        if isinstance(f, Mapping) and finding_has_forbidden_placeholder(f):
            return False
    return True


def unresolved_product_identity_ar() -> str:
    """Honest merchant copy when product identity is unavailable."""
    return "اسم المنتج غير متوفر"


__all__ = [
    "ENGINE_MARK",
    "finding_has_forbidden_placeholder",
    "is_fixture_loaded_from",
    "merchant_package_is_authentic_v1",
    "package_evidence_loaded_from",
    "sanitize_findings_package_for_merchant_v1",
    "text_has_forbidden_product_placeholder",
    "unresolved_product_identity_ar",
]
