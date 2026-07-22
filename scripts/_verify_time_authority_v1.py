# -*- coding: utf-8 -*-
"""Local/prod smoke for TABF V1 probe."""
from __future__ import annotations

import argparse
import json
import sys
from urllib.request import Request, urlopen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    args = ap.parse_args()
    url = f"{args.base.rstrip('/')}/dev/time-authority?store=demo"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    print(json.dumps({k: data.get(k) for k in (
        "ok", "as_of", "enabled", "replay_consistency", "scf_binding",
        "ordering_conflicts", "errors", "canonical_fingerprint",
    )}, indent=2, default=str))
    return 0 if data.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
