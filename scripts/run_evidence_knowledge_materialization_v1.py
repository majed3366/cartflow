#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controlled internal CLI — WP-ET-10.6 Evidence Knowledge Materialization Bridge.

Usage (from repo root, with app env loaded):

  python scripts/run_evidence_knowledge_materialization_v1.py \\
    --store-slug demo --mode dry_run --batch-limit 50

  python scripts/run_evidence_knowledge_materialization_v1.py \\
    --store-slug demo --mode execute --batch-limit 50 \\
    --include-validation-fixtures

Requires:
  CARTFLOW_EVIDENCE_KNOWLEDGE_MATERIALIZATION_V1=true
  CARTFLOW_EVIDENCE_KNOWLEDGE_MATERIALIZATION_EXECUTE=true  (execute only)

No public unauthenticated endpoint. No schedule. No outbound WhatsApp.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="WP-ET-10.6 demo Evidence→Knowledge materialization"
    )
    parser.add_argument("--store-slug", required=True, help="Must be demo")
    parser.add_argument(
        "--mode",
        choices=("dry_run", "execute"),
        default="dry_run",
        help="dry_run (default) or execute",
    )
    parser.add_argument("--batch-limit", type=int, default=50)
    parser.add_argument("--run-id", default="", help="Optional materialization_run_id")
    parser.add_argument(
        "--include-validation-fixtures",
        action="store_true",
        help="Include deterministic validation fixtures (still via real pipeline)",
    )
    parser.add_argument("--fixture-count", type=int, default=2)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass materialization flags (tests / emergency only)",
    )
    parser.add_argument("--as-of", default="")
    args = parser.parse_args(argv)

    # Ensure DB is initialized the same way as the app
    import models  # noqa: F401
    from extensions import db, init_database

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: DATABASE_URL is required", file=sys.stderr)
        return 2
    init_database()
    db.create_all()

    from services.evidence_truth.materialization_orchestrator_v1 import (
        run_evidence_knowledge_materialization_v1,
    )

    report = run_evidence_knowledge_materialization_v1(
        store_slug=args.store_slug,
        mode=args.mode,
        batch_limit=args.batch_limit,
        materialization_run_id=args.run_id,
        include_validation_fixtures=args.include_validation_fixtures,
        fixture_count=args.fixture_count,
        force=bool(args.force),
        as_of=args.as_of,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    if report.get("ok"):
        return 0
    if report.get("skipped"):
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
