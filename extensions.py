# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import tempfile
from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    text,
    inspect,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    scoped_session,
    sessionmaker,
)
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

# ‎db‎: واجهة ‎session / engine / create_all‎ (نمط ORM شائع مع ‎SQLAlchemy‎)
if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session

__all__ = [
    "Base",
    "Boolean",
    "Column",
    "DateTime",
    "Float",
    "ForeignKey",
    "Integer",
    "String",
    "Text",
    "db",
    "func",
    "inspect",
    "init_database",
    "get_database_url",
    "remove_scoped_session",
    "text",
]


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


class Base(DeclarativeBase):
    pass


_engine: Optional[Engine] = None
_Scoped: Any = None


def init_database(url: Optional[str] = None) -> None:
    """إنشاء ‎Engine‎ + ‎scoped_session‎ (استدعِ بعد استيراد النماذج)."""
    global _engine, _Scoped
    u = (url or "").strip() or get_database_url()
    connect: dict = {}
    engine_kw: dict[str, Any] = {}
    if u.startswith("sqlite:"):
        connect["check_same_thread"] = False
        # ‎QueuePool‎ الافتراضي يُنفّد الاتصالات في ‎pytest‎ الطويل على ‎SQLite‎؛ ‎NullPool‎ يغلق الاتصال عند الإرجاع.
        engine_kw["poolclass"] = NullPool
    _engine = create_engine(
        u,
        pool_pre_ping=not u.startswith("sqlite:"),
        connect_args=connect,
        **engine_kw,
    )
    factory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    _Scoped = scoped_session(factory)


def remove_scoped_session() -> None:
    if _Scoped is not None:
        _Scoped.remove()


def _get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("init_database() was not called")
    return _engine


def _get_scoped() -> Any:
    if _Scoped is None:
        raise RuntimeError("init_database() was not called")
    return _Scoped


class _DB:
    @property
    def session(self) -> Any:
        return _get_scoped()

    @property
    def engine(self) -> Engine:
        return _get_engine()

    def create_all(self) -> None:
        Base.metadata.create_all(bind=_get_engine())

    @property
    def metadata(self) -> Any:
        return Base.metadata


db = _DB()
