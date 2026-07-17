# -*- coding: utf-8 -*-
"""Run Business Findings Engine V1 against demo fixture (and optional DB)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from services.business_findings_engine_v1 import (  # noqa: E402
    render_findings_report_markdown_v1,
    run_business_findings_engine_v1,
)

OUT = _REPO / "docs" / "business_findings"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
    md = render_findings_report_markdown_v1(pkg)
    (OUT / "BUSINESS_FINDINGS_DEMO_REPORT_V1.md").write_text(md, encoding="utf-8")
    (OUT / "business_findings_demo_package_v1.json").write_text(
        json.dumps(pkg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Acceptance summary
    findings = pkg.get("findings") or []
    families = sorted({f.get("family_key") for f in findings if f.get("family_key")})
    summary = {
        "ok": pkg.get("ok"),
        "finding_count": len(findings),
        "families": families,
        "family_count": len(families),
        "has_product": any("product" in str(f.get("family_key") or "") for f in findings),
        "has_hesitation": any("hesitation" in str(f.get("family_key") or "") for f in findings),
        "has_channel": any(
            "channel" in str(f.get("family_key") or "") for f in findings
        ),
        "has_insufficient_or_traffic_gap": any(
            f.get("status") == "insufficient_evidence"
            or "traffic" in str(f.get("finding_type") or "")
            for f in findings
        ),
        "contact_findings": sum(
            1
            for f in findings
            if f.get("finding_type") == "missing_contact_blocks_recovery_v1"
        ),
        "titles": [f.get("title") for f in findings],
    }
    (OUT / "business_findings_acceptance_summary_v1.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["finding_count"] >= 5 and summary["family_count"] >= 3 else 2


if __name__ == "__main__":
    raise SystemExit(main())
