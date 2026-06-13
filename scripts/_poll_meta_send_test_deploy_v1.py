# -*- coding: utf-8 -*-
"""Poll until meta-send-test endpoint is deployed."""
from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request

URL = "https://smartreplyai.net/admin/api/whatsapp/meta-send-test"


def probe() -> tuple[int, bool]:
    req = urllib.request.Request(URL, method="POST", data=b"{}")
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=25)
        return 200, True
    except urllib.error.HTTPError as exc:
        return exc.code, exc.code == 401
    except Exception:
        return 0, False


def main() -> int:
    for i in range(36):
        code, ok = probe()
        print(i, "status", code, "deployed=", ok)
        if ok:
            print("DEPLOYED")
            return 0
        time.sleep(15)
    print("TIMEOUT")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
