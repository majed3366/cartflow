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
    "POSTGRES_POOL_MAX_OVERFLOW",
    "POSTGRES_POOL_SIZE",
    "POSTGRES_POOL_TIMEOUT",
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

# Legacy names kept for imports. Live Postgres bounds come from db_pool_bounds_v1.
POSTGRES_POOL_SIZE = 5
POSTGRES_POOL_MAX_OVERFLOW = 5
POSTGRES_POOL_TIMEOUT = 5
POSTGRES_POOL_RECYCLE = 300


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
    from services.database_network_guard_v1 import assert_database_url_allowed
    from services.db_pool_bounds_v1 import resolve_pool_bounds

    raw_env = (os.getenv("DATABASE_URL") or "").strip()
    env_name = (os.getenv("ENV") or "").strip().lower()
    production_like = env_name in ("production", "prod", "staging", "preview")
    if url is None and production_like and not raw_env:
        assert_database_url_allowed("")

    u = (url or "").strip() or get_database_url()
    assert_database_url_allowed(u)
    connect: dict = {}
    engine_kw: dict[str, Any] = {}
    if u.startswith("sqlite:"):
        connect["check_same_thread"] = False
        # يقلّل ‎"database is locked"‎ عند ‎TestClient‎ / عدة خيوط على ‎Windows‎ مع نفس الملف.
        connect["timeout"] = 30.0
        # ‎QueuePool‎ الافتراضي يُنفّد الاتصالات في ‎pytest‎ الطويل على ‎SQLite‎؛ ‎NullPool‎ يغلق الاتصال عند الإرجاع.
        engine_kw["poolclass"] = NullPool
    else:
        bounds = resolve_pool_bounds()
        engine_kw["pool_size"] = bounds["pool_size"]
        engine_kw["max_overflow"] = bounds["max_overflow"]
        engine_kw["pool_timeout"] = bounds["pool_timeout"]
        engine_kw["pool_recycle"] = bounds["pool_recycle"]
        engine_kw["pool_reset_on_return"] = "rollback"
    _engine = create_engine(
        u,
        pool_pre_ping=not u.startswith("sqlite:"),
        connect_args=connect,
        **engine_kw,
    )
    factory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    from services.db_lifecycle_v1.request_session_scope import logical_request_scopefunc

    _Scoped = scoped_session(factory, scopefunc=logical_request_scopefunc)
    try:
        from services.db_lifecycle_v1.connection_trace import maybe_install_connection_trace

        maybe_install_connection_trace()
    except Exception:
        pass


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
