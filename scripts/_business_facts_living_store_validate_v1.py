# -*- coding: utf-8 -*-
"""
Living Store / production demo validation for Business Facts Extraction V1.

Proves natural extraction (not hardcoded product lists) via ORV → facts.
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
    / "business_facts_v1"
    / "living_store_validation.json"
)


def main() -> int:
    url = f"{BASE}/dev/business-facts?store=demo"
    with urlopen(url, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    meanings = [str(m or "") for m in (body.get("meanings_ar") or [])]
    blob = "\n".join(meanings)
    checks = {
        "has_attention_or_conversion": any(
            "اهتمام" in m or "تحويل" in m for m in meanings
        ),
        "has_shipping_effect": any("شحن" in m for m in meanings),
        "has_repeat_return": any("يعودون" in m or "مراراً" in m for m in meanings),
        "has_recovery_or_health": any(
            "استعادة" in m or "مشكلات تجارية" in m or "إتمام الشراء" in m
            for m in meanings
        ),
        "no_waiting_total": "waiting_total" not in blob,
        "no_recommendation_key": body.get("recommendation") is None,
        "facts_count_positive": int(body.get("facts_count") or 0) > 0,
    }
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "facts_count": body.get("facts_count"),
        "fact_types": body.get("fact_types"),
        "meanings_ar": meanings,
        "checks": checks,
        "ok": all(checks.values()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT)
    print(json.dumps({"ok": report["ok"], "checks": checks}, ensure_ascii=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
