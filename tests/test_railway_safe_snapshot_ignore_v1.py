# -*- coding: utf-8 -*-
"""Guards for .railwayignore: exclude evidence, keep API/Merchant UI runtime."""
from __future__ import annotations

import fnmatch
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORE = ROOT / ".railwayignore"

REQUIRED = (
    "cartflow_api.py",
    "main.py",
    "start.py",
    "requirements.txt",
    "Dockerfile",
    "Procfile",
    "railway.api.toml",
    "railway.toml",
    "alembic.ini",
    "static/merchant_ui_v2_comms.js",
    "static/merchant_ui_v2_comms.css",
    "static/merchant_ui_v2_carts.js",
    "static/merchant_ui_v2_home.js",
    "static/merchant_ui_v2_workspace.js",
    "static/merchant_ui_v2_app.js",
    "templates/merchant_app_v2.html",
    "docs/investigations/PRODUCT_INVESTIGATION_REGISTRY.md",
)

MUST_IGNORE = (
    "docs/product/communication_product_composition_v1/screenshots/01_desktop_list.png",
    "docs/architecture/CARTFLOW_ARCHITECTURE_SURFACE_ALIGNMENT_AUDIT_V1.md",
    "tests/test_communication_product_composition_v1.py",
)


def load_patterns(text: str) -> list[str]:
    pats: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pats.append(line.replace("\\", "/"))
    return pats


def ignored(rel: str, patterns: list[str] | None = None) -> bool:
    rel = rel.replace("\\", "/").lstrip("./")
    pats = patterns if patterns is not None else load_patterns(IGNORE.read_text(encoding="utf-8"))
    for pat in pats:
        if _match(rel, pat):
            return True
    return False


def _match(rel: str, pat: str) -> bool:
    if pat.startswith("/*.") and "/" not in pat[2:]:
        return "/" not in rel and fnmatch.fnmatch(rel, pat[1:])
    if pat.endswith("/"):
        prefix = pat.rstrip("/")
        if prefix == "*_out":
            return any(fnmatch.fnmatch(seg, "*_out") for seg in rel.split("/"))
        return rel == prefix or rel.startswith(prefix + "/")
    if "/" in pat and "*" in pat:
        # gitignore-style: * does not cross '/'.
        name = Path(rel).name
        parent = str(Path(rel).parent).replace("\\", "/")
        pat_parent = str(Path(pat).parent).replace("\\", "/")
        return parent == pat_parent and fnmatch.fnmatch(name, Path(pat).name)
    if "/" in pat:
        return rel == pat
    return rel == pat or fnmatch.fnmatch(Path(rel).name if "/" not in pat else rel, pat)


class RailwaySafeSnapshotIgnoreV1Tests(unittest.TestCase):
    def test_ignore_file_exists(self) -> None:
        self.assertTrue(IGNORE.is_file())

    def test_required_runtime_not_ignored(self) -> None:
        for rel in REQUIRED:
            self.assertTrue((ROOT / rel).is_file(), rel)
            self.assertFalse(ignored(rel), f"must keep {rel}")

    def test_docs_investigations_not_matched_by_docs_star_md(self) -> None:
        self.assertFalse(
            ignored("docs/investigations/PRODUCT_INVESTIGATION_REGISTRY.md")
        )

    def test_evidence_and_tests_ignored(self) -> None:
        for rel in MUST_IGNORE:
            self.assertTrue((ROOT / rel).is_file(), rel)
            self.assertTrue(ignored(rel), f"must ignore {rel}")


if __name__ == "__main__":
    unittest.main()
