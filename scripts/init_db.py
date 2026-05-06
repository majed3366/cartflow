#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إنشاء جداول قاعدة البيانات (مرة واحدة) — يُنفّذ يدوياً: python scripts/init_db.py
لا يُشغّل تلقائياً عند إقلاع التطبيق.
"""
import os
import sys

# جذر المشروع
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.chdir(ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import models  # noqa: F401, E402
from extensions import db, init_database  # noqa: E402
from models import (  # noqa: F401, E402
    AbandonedCart,
    AdminAlert,
    MessageLog,
    ObjectionTrack,
    RecoveryEvent,
    Store,
)


def main() -> None:
    init_database()
    db.create_all()
    print("init_db: create_all() finished.")


if __name__ == "__main__":
    main()
