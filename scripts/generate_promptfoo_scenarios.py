#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit promptfoo/tests.generated.yaml — root is a list of test cases (see promptfoo docs)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "promptfoo" / "tests.generated.yaml"

REASONS = [
    "price_high",
    "shipping",
    "warranty",
    "quality",
    "thinking",
    "human_support",
    "other",
]
NAMES = ["حقيقي أ", "SKU-241", "منتج تجريبي", "TrueSound", "عطر"]
VALUES = [49.0, 100.0, 500.0, 1500.0, 12000.0]


def main() -> None:
    lines = ["# Auto-generated — python scripts/generate_promptfoo_scenarios.py"]
    for i in range(50):
        r = REASONS[i % len(REASONS)]
        n = NAMES[i % len(NAMES)]
        v = VALUES[i % len(VALUES)]
        lines.append("- vars:")
        lines.append(f"    case_id: {i}")
        lines.append(f"    reason_tag: {r}")
        lines.append(f"    product_name: {n}")
        lines.append(f"    cart_value: {v}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
