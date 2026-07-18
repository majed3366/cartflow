# -*- coding: utf-8 -*-
"""Run Business Reasoning Engine V1 against Findings demo fixture and write report."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.business_reasoning_engine_v1 import (  # noqa: E402
    render_reasoning_report_markdown_v1,
    run_business_reasoning_engine_v1,
)


def main() -> int:
    pkg = run_business_reasoning_engine_v1(store_slug="demo", demo_fixture=True)
    md = render_reasoning_report_markdown_v1(pkg)
    out = ROOT / "docs" / "business_findings" / "BUSINESS_REASONING_DEMO_REPORT_V1.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"cards={len(pkg.get('reasoning_cards') or [])}")
    print(f"wrote={out}")
    for c in pkg.get("reasoning_cards") or []:
        print(f"- {c.get('reasoning_type')}: {c.get('headline')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
