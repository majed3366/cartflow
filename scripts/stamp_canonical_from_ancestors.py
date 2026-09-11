# -*- coding: utf-8 -*-
"""Stamp alembic_version from known production ancestors to f10. Never upgrade."""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("CARTFLOW_REFUSE_CREATE_ALL", "1")


def main() -> int:
    execute = "--execute" in sys.argv
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        print(json.dumps({"ok": False, "error": "database_url_missing"}))
        return 2
    from services.migration_lineage_integrity_v1.stamp import stamp_canonical_from_ancestors

    out = stamp_canonical_from_ancestors(database_url=url, execute=execute)
    print(json.dumps({k: v for k, v in out.items() if k != "graph"} | {"graph_ok": (out.get("graph") or {}).get("ok")}, default=str))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
