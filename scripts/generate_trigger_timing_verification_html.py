# -*- coding: utf-8 -*-
"""Generate static HTML table of recommended trigger-template timings (visual QA)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.trigger_template_ui_defaults import (  # noqa: E402
    enrich_reason_entry_for_dashboard,
    format_delay_for_dashboard_ui,
)
from services.trigger_templates_dashboard import TRIGGER_TEMPLATE_PAGE_KEYS  # noqa: E402


def main() -> None:
    by_key = {}
    for key in TRIGGER_TEMPLATE_PAGE_KEYS:
        ent = enrich_reason_entry_for_dashboard(
            key, {"enabled": True, "message_count": 3, "messages": []}
        )
        by_key[key] = ent

    rows_html: list[str] = []
    summary: dict[str, list[str]] = {}
    for key in TRIGGER_TEMPLATE_PAGE_KEYS:
        r = by_key[key]
        mc = min(3, int(r.get("message_count") or 1))
        stage_parts: list[str] = []
        summary[key] = []
        for i in range(3):
            if i >= mc:
                stage_parts.append("<td class='off'>—</td>")
                continue
            msgs = r.get("messages") or []
            if i < len(msgs):
                d = float(msgs[i]["delay"])
                u = str(msgs[i]["unit"])
                disp = format_delay_for_dashboard_ui(d, u)
            else:
                disp = "—"
            summary[key].append(disp)
            stage_parts.append(
                "<td><div class='val'>"
                + disp
                + "</div><div class='lbl'>مرحلة "
                + str(i + 1)
                + "</div></td>"
            )
        rows_html.append("<tr><th>" + key + "</th>" + "".join(stage_parts) + "</tr>")

    html = (
        "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='utf-8' />"
        "<title>Trigger template timing defaults</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:24px;background:#f8fafc}"
        "table{border-collapse:collapse;width:100%;max-width:900px;background:#fff}"
        "th,td{border:1px solid #e2e8f0;padding:12px;text-align:center}"
        "th{background:#f1f5f9}.val{font-size:20px;font-weight:800;color:#15803d}"
        ".lbl{font-size:11px;color:#64748b;margin-top:4px}td.off{color:#cbd5e1}"
        ".note{font-size:12px;color:#64748b;margin-top:16px}</style></head><body>"
        "<h1>قوالب الاسترجاع — التوقيتات المقترحة (متجر جديد)</h1>"
        "<table><thead><tr><th>السبب</th><th>المرحلة 1</th><th>المرحلة 2</th>"
        "<th>المرحلة 3</th></tr></thead><tbody>"
        + "".join(rows_html)
        + "</tbody></table><p class='note'>"
        + json.dumps(summary, ensure_ascii=False)
        + "</p></body></html>"
    )
    out = ROOT / "docs" / "trigger_template_timing_defaults_verification.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
