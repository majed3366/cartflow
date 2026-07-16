# -*- coding: utf-8 -*-
"""
Product Investigation Registry projection (read-only).

Canonical source: ``docs/investigations/PRODUCT_INVESTIGATION_REGISTRY.md``
plus case files ``INV-*.md``. No second independent registry.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

ROOT = Path(__file__).resolve().parents[1]
INVESTIGATIONS_DIR = ROOT / "docs" / "investigations"
REGISTRY_PATH = INVESTIGATIONS_DIR / "PRODUCT_INVESTIGATION_REGISTRY.md"
DEPENDENCY_GRAPH_PATH = INVESTIGATIONS_DIR / "INVESTIGATION_DEPENDENCY_GRAPH.md"

# UI / summary labels (canonical → display)
STATUS_CANONICAL = (
    "Open",
    "Investigating",
    "Root Cause Confirmed",
    "Ready for Fix",
    "Fixed",
    "Verified",
    "Blocked",
    "Closed",
)
STATUS_DISPLAY = {
    "Open": "Open",
    "Investigating": "Investigating",
    "Root Cause Confirmed": "Root Cause Confirmed",
    "Ready for Fix": "Ready for Fix",
    "Fixed": "Implementation",
    "Verified": "Verification",
    "Blocked": "Blocked",
    "Closed": "Closed",
}
SUMMARY_STATUS_KEYS = (
    "Open",
    "Investigating",
    "Root Cause Confirmed",
    "Ready for Fix",
    "Implementation",
    "Verification",
    "Blocked",
    "Closed",
)
SEVERITIES = ("Critical", "High", "Medium", "Low")

WAVE_BY_ID = {
    "INV-001": "Wave 0",
    "INV-002": "Wave 0",
    "INV-003": "Wave 1",
    "INV-005": "Wave 1",
    "INV-006": "Wave 1",
    "INV-007": "Wave 1",
    "INV-008": "Wave 1",
    "INV-004": "Wave 2",
    "INV-009": "Test Fixture",
}

# Approved dependency edges only (do not invent). From INVESTIGATION_DEPENDENCY_GRAPH.md
APPROVED_DEPENDENCIES: dict[str, list[str]] = {
    "INV-001": [],
    "INV-002": [],
    "INV-003": ["INV-001", "INV-002"],
    "INV-004": ["INV-002", "INV-003"],
    "INV-005": ["INV-002"],
    "INV-006": ["INV-001"],
    "INV-007": ["INV-001", "INV-002"],
    "INV-008": [],
    "INV-009": [],
}

# Explicit contribution notes for dependency view (approved narrative only)
CONTRIBUTES_TO: dict[str, list[str]] = {
    "INV-001": ["INV-003", "INV-007", "INV-004", "INV-005", "INV-006"],
    "INV-002": ["INV-003", "INV-004", "INV-005", "INV-007"],
    "INV-003": ["INV-004"],
    "INV-008": ["INV-003"],
}


@dataclass(frozen=True)
class InvestigationRecord:
    id: str
    title: str
    severity: str
    category: str
    status: str
    status_display: str
    owner: str
    depends_on: list[str]
    blocks: str
    opened_utc: str
    primary_source: str
    parent_investigations: list[str]
    wave: str
    merchant_impact: str
    could_explain: str
    next_required_gate: str
    last_updated: str
    case_path: str
    evidence_paths: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    registry_row: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_HEADER_FIELD_RE = re.compile(
    r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*$", re.MULTILINE
)
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_INV_FILE_RE = re.compile(r"^INV-\d{3}\.md$")


def _norm_status(raw: str) -> str:
    s = (raw or "").strip()
    # Strip parenthetical / em-dash suffixes: "Ready for Fix — WP-6..."
    for canon in STATUS_CANONICAL:
        if s == canon or s.startswith(canon):
            return canon
    # Common aliases
    low = s.lower()
    if "ready for fix" in low:
        return "Ready for Fix"
    if "root cause" in low:
        return "Root Cause Confirmed"
    if "investigating" in low:
        return "Investigating"
    if low.startswith("open"):
        return "Open"
    if "blocked" in low:
        return "Blocked"
    if low == "fixed" or "implementation" in low:
        return "Fixed"
    if "verified" in low or "verification" in low:
        return "Verified"
    if "closed" in low:
        return "Closed"
    return s or "Open"


def _parse_depends(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text or text in ("—", "-", "–", "none", "None"):
        return []
    # "INV-001 (time), INV-002 (identity)" or "INV-001, INV-002"
    ids = re.findall(r"INV-\d{3}", text)
    return list(dict.fromkeys(ids))


def _parse_header_table(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _HEADER_FIELD_RE.finditer(text):
        key = m.group(1).strip()
        val = m.group(2).strip()
        out[key] = val
    return out


def _parse_sections(text: str) -> dict[str, str]:
    matches = list(_SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[title] = text[start:end].strip()
    return sections


def _merchant_impact_blurb(sections: Mapping[str, str]) -> str:
    body = sections.get("Merchant Impact") or ""
    lines = [ln.strip("- ").strip() for ln in body.splitlines() if ln.strip()]
    for ln in lines:
        if ln.startswith("|") or ln.startswith("#"):
            continue
        if len(ln) > 20:
            return ln[:240]
    return (body[:240] + "…") if len(body) > 240 else body


def _could_explain(inv_id: str, sections: Mapping[str, str]) -> str:
    contrib = CONTRIBUTES_TO.get(inv_id) or []
    if contrib:
        return "Contributes to: " + ", ".join(contrib)
    # Soft note from symptoms first line
    symptoms = sections.get("Observed Symptoms") or ""
    for ln in symptoms.splitlines():
        t = ln.strip()
        if t and t[0].isdigit():
            return t[:200]
    return ""


def _next_gate(status: str, inv_id: str) -> str:
    if status == "Ready for Fix":
        if inv_id == "INV-001":
            return "Architecture Review of Reality Checkpoint V2 → authorize WP-7"
        return "Architecture authorization for next Work Package"
    if status == "Open":
        return "Investigation depth / Architectural review"
    if status == "Investigating":
        return "Root Cause Confirmed review"
    if status == "Root Cause Confirmed":
        return "Definition of Ready / Ready for Fix certification"
    if status == "Fixed":
        return "Verification evidence pack"
    if status == "Verified":
        return "Closure archive"
    if status == "Blocked":
        return "Unblock parent / external decision"
    return "Governance review"


def _file_mtime_iso(path: Path) -> str:
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        return ""


def _parse_registry_table() -> dict[str, dict[str, str]]:
    if not REGISTRY_PATH.is_file():
        return {}
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    rows: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        if not line.startswith("| INV-"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 7:
            continue
        inv_id = parts[0]
        rows[inv_id] = {
            "id": inv_id,
            "title": parts[1],
            "severity": parts[2],
            "category": parts[3],
            "status": parts[4],
            "owner": parts[5],
            "depends_on": parts[6],
            "case_file": parts[7] if len(parts) > 7 else "",
        }
    return rows


def load_investigation_case(path: Path) -> Optional[InvestigationRecord]:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    header = _parse_header_table(text)
    sections = _parse_sections(text)
    inv_id = header.get("Investigation ID") or path.stem
    status = _norm_status(header.get("Status", "Open"))
    depends = _parse_depends(header.get("Depends on", ""))
    # Prefer approved graph when present
    if inv_id in APPROVED_DEPENDENCIES:
        depends = list(APPROVED_DEPENDENCIES[inv_id])
    parents = list(depends)
    evidence: list[str] = []
    ev = sections.get("Evidence") or ""
    for m in re.finditer(r"`([^`]+)`", ev):
        evidence.append(m.group(1))
    # Related paths
    for key in ("Primary source",):
        if header.get(key):
            evidence.append(header[key])
    return InvestigationRecord(
        id=inv_id,
        title=header.get("Title") or path.stem,
        severity=(header.get("Severity") or "Medium").split()[0],
        category=header.get("Category") or "",
        status=status,
        status_display=STATUS_DISPLAY.get(status, status),
        owner=header.get("Owner") or "",
        depends_on=depends,
        blocks=header.get("Blocks") or "—",
        opened_utc=header.get("Opened (UTC)") or "",
        primary_source=header.get("Primary source") or "",
        parent_investigations=parents,
        wave=WAVE_BY_ID.get(inv_id, "Unassigned"),
        merchant_impact=_merchant_impact_blurb(sections),
        could_explain=_could_explain(inv_id, sections),
        next_required_gate=_next_gate(status, inv_id),
        last_updated=_file_mtime_iso(path),
        case_path=str(path.relative_to(ROOT)).replace("\\", "/"),
        evidence_paths=list(dict.fromkeys(evidence))[:24],
        sections={k: v[:12000] for k, v in sections.items()},
        registry_row={},
    )


def load_all_investigations() -> list[InvestigationRecord]:
    registry_rows = _parse_registry_table()
    records: list[InvestigationRecord] = []
    paths = sorted(INVESTIGATIONS_DIR.glob("INV-*.md"))
    for path in paths:
        if not _INV_FILE_RE.match(path.name):
            continue
        if path.name.endswith("_REVIEW.md"):
            continue
        rec = load_investigation_case(path)
        if rec is None:
            continue
        row = registry_rows.get(rec.id) or {}
        # Prefer registry severity/status when present (index authority)
        severity = (row.get("severity") or rec.severity).split()[0]
        status = _norm_status(row.get("status") or rec.status)
        enriched = InvestigationRecord(
            id=rec.id,
            title=row.get("title") or rec.title,
            severity=severity,
            category=row.get("category") or rec.category,
            status=status,
            status_display=STATUS_DISPLAY.get(status, status),
            owner=row.get("owner") or rec.owner,
            depends_on=rec.depends_on,
            blocks=rec.blocks,
            opened_utc=rec.opened_utc,
            primary_source=rec.primary_source,
            parent_investigations=rec.parent_investigations,
            wave=rec.wave,
            merchant_impact=rec.merchant_impact,
            could_explain=rec.could_explain,
            next_required_gate=_next_gate(status, rec.id),
            last_updated=rec.last_updated,
            case_path=rec.case_path,
            evidence_paths=rec.evidence_paths,
            sections=rec.sections,
            registry_row=row,
        )
        records.append(enriched)
    records.sort(key=lambda r: r.id)
    return records


def status_counts(records: Iterable[InvestigationRecord]) -> dict[str, int]:
    counts = {k: 0 for k in SUMMARY_STATUS_KEYS}
    for r in records:
        key = STATUS_DISPLAY.get(r.status, r.status)
        if key in counts:
            counts[key] += 1
        elif r.status in counts:
            counts[r.status] += 1
    return counts


def severity_counts(records: Iterable[InvestigationRecord]) -> dict[str, int]:
    counts = {k: 0 for k in SEVERITIES}
    for r in records:
        sev = r.severity if r.severity in counts else "Medium"
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def dependency_view(records: Iterable[InvestigationRecord]) -> dict[str, Any]:
    by_id = {r.id: r for r in records}
    edges = []
    for child, parents in APPROVED_DEPENDENCIES.items():
        for parent in parents:
            edges.append({"from": parent, "to": child, "kind": "depends_on"})
    # Soft inform edge INV-008 → INV-003
    edges.append(
        {
            "from": "INV-008",
            "to": "INV-003",
            "kind": "informs",
            "note": "eligibility taxonomy (soft)",
        }
    )
    notes = [
        "INV-001 directly explains or contributes to INV-003 and INV-007",
        "INV-001 contributes to INV-004, INV-005 and INV-006 (via time/trust surfaces)",
        "INV-002 remains independent from Time Authority",
        "INV-009 is an independent test-fixture investigation unless evidence proves otherwise",
    ]
    return {
        "edges": edges,
        "nodes": [
            {"id": r.id, "title": r.title, "severity": r.severity, "status": r.status_display}
            for r in by_id.values()
        ],
        "approved_notes": notes,
        "contributes_to": CONTRIBUTES_TO,
        "source": str(DEPENDENCY_GRAPH_PATH.relative_to(ROOT)).replace("\\", "/"),
    }


def filter_investigations(
    records: Iterable[InvestigationRecord],
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    wave: Optional[str] = None,
    parent: Optional[str] = None,
    merchant_trust: Optional[str] = None,
) -> list[InvestigationRecord]:
    out: list[InvestigationRecord] = []
    for r in records:
        if status:
            s = status.strip()
            if s not in (r.status, r.status_display) and not r.status.startswith(s):
                continue
        if severity and r.severity.lower() != severity.lower():
            continue
        if category and category.lower() not in r.category.lower():
            continue
        if wave and wave.lower() not in r.wave.lower():
            continue
        if parent:
            p = parent.strip().upper()
            if p not in r.parent_investigations and p not in r.depends_on:
                continue
        if merchant_trust:
            # Merchant trust impact band aliases severity (Critical/High/Medium/Low)
            if r.severity.lower() != merchant_trust.lower():
                continue
        out.append(r)
    return out


def build_investigation_dashboard_payload(
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    wave: Optional[str] = None,
    parent: Optional[str] = None,
    merchant_trust: Optional[str] = None,
) -> dict[str, Any]:
    all_recs = load_all_investigations()
    filtered = filter_investigations(
        all_recs,
        status=status,
        severity=severity,
        category=category,
        wave=wave,
        parent=parent,
        merchant_trust=merchant_trust,
    )
    return {
        "ok": True,
        "version": "v1",
        "read_only": True,
        "canonical_registry": str(REGISTRY_PATH.relative_to(ROOT)).replace("\\", "/"),
        "investigations_dir": str(INVESTIGATIONS_DIR.relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "counts": {
            "total": len(all_recs),
            "filtered": len(filtered),
            "by_status": status_counts(all_recs),
            "by_severity": severity_counts(all_recs),
        },
        "filters_applied": {
            "status": status or None,
            "severity": severity or None,
            "category": category or None,
            "wave": wave or None,
            "parent": parent or None,
            "merchant_trust": merchant_trust or None,
        },
        "investigations": [r.to_dict() for r in filtered],
        "dependency_view": dependency_view(all_recs),
        "filter_options": {
            "status": list(SUMMARY_STATUS_KEYS),
            "severity": list(SEVERITIES),
            "wave": sorted({r.wave for r in all_recs}),
            "category": sorted({r.category for r in all_recs if r.category}),
            "parent": sorted(
                {p for r in all_recs for p in r.parent_investigations} | {"—"}
            ),
            "merchant_trust": ["Critical", "High", "Medium", "Low"],
        },
    }


def get_investigation_detail(inv_id: str) -> Optional[dict[str, Any]]:
    inv_id = (inv_id or "").strip().upper()
    for r in load_all_investigations():
        if r.id == inv_id:
            d = r.to_dict()
            d["read_only"] = True
            d["canonical_case"] = r.case_path
            d["related_work_packages"] = _related_wps(inv_id)
            return d
    return None


def _related_wps(inv_id: str) -> list[str]:
    if inv_id != "INV-001":
        return []
    wps = sorted(INVESTIGATIONS_DIR.glob("WP-*.md"))
    return [str(p.relative_to(ROOT)).replace("\\", "/") for p in wps]


__all__ = [
    "APPROVED_DEPENDENCIES",
    "INVESTIGATIONS_DIR",
    "REGISTRY_PATH",
    "InvestigationRecord",
    "build_investigation_dashboard_payload",
    "filter_investigations",
    "get_investigation_detail",
    "load_all_investigations",
    "load_investigation_case",
    "severity_counts",
    "status_counts",
]
