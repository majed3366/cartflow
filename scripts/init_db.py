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

from main import app  # noqa: E402
from extensions import db  # noqa: E402
from models import (  # noqa: F401, E402
    AbandonedCart,
    MessageLog,
    ObjectionTrack,
    RecoveryEvent,
    Store,
)


def main() -> None:
    with app.app_context():
        db.create_all()
        print("init_db: create_all() finished.")


if __name__ == "__main__":
    main()
