# -*- coding: utf-8 -*-
"""
Living Store / production demo validation for Business Theme Engine V1.

Proves many facts → one theme; no duplicate theme types; no recommendations.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

BASE = "https://smartreplyai.net"
OUT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "product"
    / "business_themes_v1"
    / "living_store_validation.json"
)


def main() -> int:
    url = f"{BASE}/dev/business-themes?store=demo"
    with urlopen(url, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    types = [str(t or "") for t in (body.get("theme_types") or [])]
    summaries = [str(s or "") for s in (body.get("summaries_ar") or [])]
    blob = "\n".join(summaries)
    facts_in = int(body.get("facts_in") or 0)
    published = int(body.get("published_count") or 0)
    checks = {
        "ok_flag": bool(body.get("ok")),
        "published_positive": published > 0,
        "no_duplicate_theme_types": len(types) == len(set(types)),
        "facts_gte_themes": facts_in >= published,
        "has_conversion_or_shipping_or_return": any(
            t in types
            for t in (
                "product_conversion",
                "shipping_friction",
                "customer_return_behaviour",
            )
        ),
        "constitution_present": body.get("constitution")
        == "one_theme_one_owner_many_consumers",
        "no_recommendation": body.get("recommendation") is None,
        "no_waiting_total": "waiting_total" not in blob,
        "no_pi": body.get("product_intelligence") is False,
    }
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "facts_in": facts_in,
        "published_count": published,
        "collapsed_ratio": body.get("collapsed_ratio"),
        "theme_types": types,
        "titles_ar": body.get("titles_ar"),
        "summaries_ar": summaries,
        "primary_owners": body.get("primary_owners"),
        "checks": checks,
        "ok": all(checks.values()),
        "mx_note": (
            "Themes must visibly reduce repetition on Home + Decision Workspace. "
            "If not, recommend remove/redesign — do not keep architectural complexity."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT)
    print(json.dumps({"ok": report["ok"], "checks": checks}, ensure_ascii=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
