# -*- coding: utf-8 -*-
"""CLI — Diagnostic Reasoning V1 materialization (off-path)."""
from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Diagnostic Reasoning V1 materialize")
    p.add_argument("--store", required=True, help="store_slug")
    p.add_argument("--execute", action="store_true", help="persist snapshots")
    p.add_argument("--enable", action="store_true", help="set feature flags in-process")
    args = p.parse_args(argv)
    if args.enable:
        os.environ["CARTFLOW_DIAGNOSTIC_REASONING_V1"] = "1"
        if args.execute:
            os.environ["CARTFLOW_DIAGNOSTIC_REASONING_EXECUTE"] = "1"

    # App context for DB
    from main import app  # noqa: PLC0415
    from services.diagnostic_reasoning_v1 import (  # noqa: PLC0415
        materialize_diagnostics_for_store_v1,
    )

    with app.app_context():
        result = materialize_diagnostics_for_store_v1(
            args.store,
            execute=bool(args.execute),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
