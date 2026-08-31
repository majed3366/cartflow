# -*- coding: utf-8 -*-
"""
Semantic Visual Model V1 — derivation only.

RAW CANONICAL TRUTH → bounded semantic variables.
No presentation. No invented fields. Painters must consume this output.
"""
from __future__ import annotations

from typing import Any, Mapping

SEMANTIC_MODEL_VERSION = "semantic-visual-model-v1"

STATUS_INSUFFICIENT_AR = "أدلة غير كافية"
STATUS_WAITING_AR = "بانتظار متابعة"
STATUS_NO_TASKS_AR = "لا مهام"

READY = "READY"
NEEDS_MORE = "NEEDS_MORE_EVIDENCE"
BLOCKED = "BLOCKED"
EXTERNAL = "EXTERNAL_DEPENDENCY"
READINESS_KNOWN = frozenset({READY, NEEDS_MORE, BLOCKED, EXTERNAL})

CONFLICT_STATUSES = frozenset({"conflicting_evidence", "conflicting"})


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _as_bool(v: Any) -> bool:
    return v is True or v == "true" or v == 1


def core_silence_home(pkg: Mapping[str, Any] | None) -> str:
    if not isinstance(pkg, Mapping) or pkg.get("enabled") is False:
        return "QUIET"
    sections = [s for s in (pkg.get("sections") or []) if isinstance(s, Mapping)]
    if not sections:
        return "QUIET"
    primary = next(
        (s for s in sections if s.get("dominant") or _norm(s.get("id")) == "decisions"),
        sections[0],
    )
    others = [s for s in sections if s is not primary]
    if _as_bool(primary.get("empty")) and not others:
        return "QUIET"
    return "ACTIVE"


def core_silence_workspace(projection: Mapping[str, Any] | None) -> str:
    if not isinstance(projection, Mapping):
        return "QUIET"
    if _as_bool(projection.get("quiet")):
        return "QUIET"
    zone_b = projection.get("zone_b")
    if not isinstance(zone_b, list) or len(zone_b) == 0:
        return "QUIET"
    return "ACTIVE"


def attention_intensity(
    *,
    silence: str,
    surface: str,
    section: Mapping[str, Any] | None = None,
    card: Mapping[str, Any] | None = None,
) -> str:
    if silence == "QUIET":
        return "NONE"
    if surface == "home":
        sec = section if isinstance(section, Mapping) else {}
        if _as_bool(sec.get("empty")):
            return "NONE"
        if sec.get("dominant") or _norm(sec.get("id")) == "decisions":
            return "PRIMARY"
        return "SECONDARY"
    card = card if isinstance(card, Mapping) else {}
    if card.get("is_primary_decision") is True:
        return "PRIMARY"
    return "SECONDARY"


def decision_readiness(*, surface: str, card: Mapping[str, Any] | None = None) -> str:
    if surface != "workspace":
        return "UNKNOWN"
    raw = _norm((card or {}).get("execution_readiness"))
    if raw in READINESS_KNOWN:
        return raw
    return "UNKNOWN"


def evidence_sufficiency(
    *,
    surface: str,
    section: Mapping[str, Any] | None = None,
    card: Mapping[str, Any] | None = None,
    readiness: str = "UNKNOWN",
) -> str:
    if surface == "home":
        sec = section if isinstance(section, Mapping) else {}
        if _as_bool(sec.get("empty")) or _norm(sec.get("status_ar")) == STATUS_INSUFFICIENT_AR:
            return "INSUFFICIENT"
        return "UNKNOWN"
    card = card if isinstance(card, Mapping) else {}
    if card.get("has_decision") is False:
        return "INSUFFICIENT"
    if _norm(card.get("missing_evidence")):
        return "INSUFFICIENT"
    if readiness == NEEDS_MORE:
        return "INSUFFICIENT"
    if readiness in {READY, EXTERNAL, BLOCKED}:
        return "SUFFICIENT"
    return "UNKNOWN"


def evidence_conflict(*, surface: str, card: Mapping[str, Any] | None = None) -> str:
    if surface != "workspace":
        return "UNKNOWN"
    card = card if isinstance(card, Mapping) else {}
    if "diagnosis_status" not in card:
        return "UNKNOWN"
    status = _norm(card.get("diagnosis_status")).casefold()
    if status in CONFLICT_STATUSES:
        return "CONFLICT"
    return "NONE"


def uncertainty_level(
    *,
    silence: str,
    sufficiency: str,
    conflict: str,
    readiness: str,
) -> str:
    if silence == "QUIET":
        return "NONE"
    if conflict == "CONFLICT":
        return "HIGH"
    if sufficiency == "SUFFICIENT" and conflict != "CONFLICT" and readiness == READY:
        return "NONE"
    if sufficiency == "INSUFFICIENT" or readiness == NEEDS_MORE:
        return "MEDIUM"
    return "UNKNOWN"


def wait_kind(
    *,
    surface: str,
    silence: str,
    readiness: str,
    section: Mapping[str, Any] | None = None,
    card: Mapping[str, Any] | None = None,
) -> str:
    if silence == "QUIET":
        return "NO_ACTION"
    if surface == "home":
        status = _norm((section or {}).get("status_ar"))
        if status == STATUS_WAITING_AR:
            return "WAITING_READINESS"
        if status == STATUS_NO_TASKS_AR:
            return "NO_ACTION"
        return "UNKNOWN"
    if readiness == READY:
        return "ACTION_REQUIRED"
    if readiness == EXTERNAL:
        return "WAITING_EXTERNAL"
    if readiness == BLOCKED:
        return "BLOCKED"
    if readiness == NEEDS_MORE:
        return "WAITING_READINESS"
    waits = (card or {}).get("action_wait_lines_ar")
    if isinstance(waits, list) and any(_norm(x) for x in waits):
        return "WAITING_READINESS"
    return "UNKNOWN"


def density_state(sufficiency: str) -> str:
    if sufficiency == "INSUFFICIENT":
        return "LOW"
    if sufficiency == "SUFFICIENT":
        return "PRESENT"
    return "NEUTRAL"


def mass_state(readiness: str) -> str:
    if readiness == READY:
        return "READY"
    if readiness in {BLOCKED, EXTERNAL}:
        return "HELD"
    return "OPEN"


def tension_state(*, conflict: str, readiness: str) -> str:
    if conflict == "CONFLICT" or readiness == BLOCKED:
        return "HIGH"
    if conflict == "UNKNOWN" and readiness == "UNKNOWN":
        return "UNKNOWN"
    return "NONE"


def clause_roles(sem: Mapping[str, Any]) -> list[dict[str, str]]:
    if _norm(sem.get("core_silence")) == "QUIET":
        return []
    roles: list[dict[str, str]] = []
    att = _norm(sem.get("attention_intensity"))
    if att in {"PRIMARY", "SECONDARY"}:
        roles.append(
            {
                "role": "attention",
                "kind": "attention",
                "label": "انتباه",
                "attention": att.lower(),
            }
        )
    if _norm(sem.get("evidence_sufficiency")) == "INSUFFICIENT":
        roles.append(
            {
                "role": "evidence",
                "kind": "insufficient",
                "label": "أدلة ناقصة",
                "sufficiency": "insufficient",
            }
        )
    unc = _norm(sem.get("uncertainty_level"))
    if unc in {"MEDIUM", "HIGH"}:
        item = {
            "role": "uncertainty",
            "kind": "uncertainty",
            "label": "عدم يقين",
            "uncertainty": unc.lower(),
            "tension": "high" if _norm(sem.get("evidence_conflict")) == "CONFLICT" else "none",
        }
        roles.append(item)
    return roles


def _pack(
    *,
    surface: str,
    silence: str,
    attention: str,
    readiness: str,
    sufficiency: str,
    conflict: str,
    uncertainty: str,
    wait: str,
) -> dict[str, Any]:
    sem = {
        "model": SEMANTIC_MODEL_VERSION,
        "surface": surface,
        "core_silence": silence,
        "attention_intensity": attention,
        "decision_readiness": readiness,
        "evidence_sufficiency": sufficiency,
        "evidence_conflict": conflict,
        "uncertainty_level": uncertainty,
        "wait_kind": wait,
        "density": density_state(sufficiency),
        "mass": mass_state(readiness),
        "tension": tension_state(conflict=conflict, readiness=readiness),
    }
    sem["roles"] = clause_roles(sem)
    return sem


def project_home_surface(
    pkg: Mapping[str, Any] | None,
    section: Mapping[str, Any] | None,
) -> dict[str, Any]:
    silence = core_silence_home(pkg)
    readiness = "UNKNOWN"
    sufficiency = evidence_sufficiency(
        surface="home", section=section, readiness=readiness
    )
    conflict = "UNKNOWN"
    attention = attention_intensity(silence=silence, surface="home", section=section)
    uncertainty = uncertainty_level(
        silence=silence,
        sufficiency=sufficiency,
        conflict=conflict,
        readiness=readiness,
    )
    wait = wait_kind(
        surface="home",
        silence=silence,
        readiness=readiness,
        section=section,
    )
    return _pack(
        surface="home",
        silence=silence,
        attention=attention,
        readiness=readiness,
        sufficiency=sufficiency,
        conflict=conflict,
        uncertainty=uncertainty,
        wait=wait,
    )


def project_workspace(
    projection: Mapping[str, Any] | None,
    card: Mapping[str, Any] | None,
) -> dict[str, Any]:
    silence = core_silence_workspace(projection)
    readiness = decision_readiness(surface="workspace", card=card)
    sufficiency = evidence_sufficiency(
        surface="workspace", card=card, readiness=readiness
    )
    conflict = evidence_conflict(surface="workspace", card=card)
    attention = attention_intensity(silence=silence, surface="workspace", card=card)
    uncertainty = uncertainty_level(
        silence=silence,
        sufficiency=sufficiency,
        conflict=conflict,
        readiness=readiness,
    )
    wait = wait_kind(
        surface="workspace",
        silence=silence,
        readiness=readiness,
        card=card,
    )
    return _pack(
        surface="workspace",
        silence=silence,
        attention=attention,
        readiness=readiness,
        sufficiency=sufficiency,
        conflict=conflict,
        uncertainty=uncertainty,
        wait=wait,
    )


__all__ = [
    "SEMANTIC_MODEL_VERSION",
    "clause_roles",
    "project_home_surface",
    "project_workspace",
]
