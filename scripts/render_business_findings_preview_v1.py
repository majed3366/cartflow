# -*- coding: utf-8 -*-
"""Render a standalone merchant preview of Business Findings (not Home UI)."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from services.business_findings_engine_v1 import run_business_findings_engine_v1  # noqa: E402

OUT = _REPO / "docs" / "business_findings" / "preview"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
    cards = []
    for f in pkg.get("findings") or []:
        cards.append(
            f"""
            <article class="card">
              <p class="kicker">{html.escape(str(f.get("family_key") or ""))}</p>
              <h2>{html.escape(str(f.get("title") or ""))}</h2>
              <p class="summary">{html.escape(str(f.get("merchant_summary") or ""))}</p>
              <p class="meaning"><strong>المعنى التجاري:</strong> {html.escape(str(f.get("commercial_meaning") or ""))}</p>
              <p class="evidence"><strong>الدليل:</strong> {html.escape(str(f.get("evidence_summary") or ""))}</p>
              <p class="meta">الثقة: {html.escape(str(f.get("confidence_level") or ""))}
              · التوصية: {html.escape(str(f.get("recommendation_type") or ""))}
              · الصفحة: {html.escape(str(f.get("authoritative_surface") or ""))}</p>
              <p class="dir">{html.escape(str(f.get("recommended_direction") or ""))}</p>
            </article>
            """
        )
    home = pkg.get("home_candidates_v1") or {}
    home_rows = []
    for key, label in (
        ("most_important_finding", "الأهم الآن"),
        ("strongest_opportunity", "أقوى فرصة"),
        ("highest_value_action", "أعلى إجراء قيمة"),
        ("new_understanding", "فهم جديد"),
    ):
        brief = home.get(key) or {}
        home_rows.append(
            f"<li><strong>{label}:</strong> {html.escape(str(brief.get('title') or '—'))}</li>"
        )
    doc = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8"/>
  <title>نتائج تجارية — معاينة التاجر</title>
  <style>
    body {{ font-family: "Segoe UI", Tahoma, sans-serif; background:#f4f6f5; color:#14201c; margin:0; padding:24px; }}
    h1 {{ font-size:1.6rem; margin:0 0 8px; }}
    .sub {{ color:#4a5c55; margin-bottom:24px; }}
    .grid {{ display:grid; gap:16px; }}
    .card {{ background:#fff; border-radius:16px; padding:18px 20px; box-shadow:0 1px 0 rgba(0,0,0,.04); }}
    .kicker {{ color:#2f6f5e; font-size:.8rem; margin:0 0 6px; }}
    h2 {{ font-size:1.15rem; margin:0 0 10px; line-height:1.45; }}
    .summary {{ margin:0 0 10px; line-height:1.6; }}
    .meaning,.evidence,.dir,.meta {{ margin:6px 0; line-height:1.55; font-size:.95rem; }}
    .meta {{ color:#5a6b64; }}
    .home {{ background:#14352c; color:#f3faf7; border-radius:16px; padding:18px 20px; margin-bottom:20px; }}
    .home h2 {{ color:#fff; }}
    .home li {{ margin:8px 0; }}
  </style>
</head>
<body>
  <h1>نتائج تجارية مفيدة عن متجرك</h1>
  <p class="sub">معاينة محكومة من محرك النتائج التجارية — ليست إعادة تصميم للرئيسية.</p>
  <section class="home">
    <h2>مرشّحات الرئيسية (للاستهلاك لاحقاً)</h2>
    <ul>{"".join(home_rows)}</ul>
  </section>
  <div class="grid">{"".join(cards)}</div>
</body>
</html>
"""
    path = OUT / "merchant_findings_preview_v1.html"
    path.write_text(doc, encoding="utf-8")
    (OUT / "preview_meta.json").write_text(
        json.dumps(
            {
                "path": str(path),
                "finding_count": len(pkg.get("findings") or []),
                "families": sorted(
                    {
                        f.get("family_key")
                        for f in (pkg.get("findings") or [])
                        if f.get("family_key")
                    }
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
