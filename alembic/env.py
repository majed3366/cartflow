# -*- coding: utf-8 -*-
"""
بيئة ‎Alembic‎ — ‎DATABASE_URL‎ مثل ‎main.py‎ (بدون استيراد ‎ASGI app‎ كاملاً).
"""
from __future__ import annotations

import os
import sys
import tempfile
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# جذر المشروع
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from extensions import Base  # noqa: E402
import models  # noqa: F401, E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    _db = os.getenv("DATABASE_URL")
    _database_url = (_db or "").strip()
    if not _database_url:
        if os.name == "nt":
            _p = os.path.abspath(
                os.path.join(tempfile.gettempdir(), "cartflow.db")
            ).replace("\\", "/")
            _database_url = "sqlite:///" + _p
        else:
            _database_url = "sqlite:////tmp/cartflow.db"
    if _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)
    if _database_url.startswith("postgresql+asyncpg://"):
        _database_url = _database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg://", 1
        )
    return _database_url


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_database_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
