# -*- coding: utf-8 -*-
"""
عزل جلسات SQLAlchemy عن طلبات HTTP ومهام asyncio/خلفية — إرجاع اتصالات الـ pool.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from extensions import db, remove_scoped_session

log = logging.getLogger("cartflow")

F = TypeVar("F", bound=Callable[..., Any])


def release_scoped_db_session() -> None:
    """إرجاع الاتصال: ‎rollback‎ ثم ‎scoped_session.remove()‎."""
    try:
        db.session.rollback()
    except (SQLAlchemyError, OSError, RuntimeError):
        pass
    remove_scoped_session()


def scoped_db_session_begin() -> None:
    """بداية عمل خلفي/مهمة: لا تُورّث جلسة الطلب السابق."""
    clear_request_scoped_orm_caches()
    remove_scoped_session()


@contextmanager
def isolated_db_session() -> Generator[Session, None, None]:
    """جلسة مستقلة (مثلاً تحديث كاش الودجيت) — تُغلق دائماً."""
    maker = sessionmaker(bind=db.engine, autocommit=False, autoflush=False)
    sess = maker()
    try:
        yield sess
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


def run_sync_background_db_task(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """مهمة FastAPI ‎BackgroundTasks‎ متزامنة — جلسة نظيفة ثم تنظيف."""
    scoped_db_session_begin()
    try:
        return fn(*args, **kwargs)
    except Exception:
        try:
            db.session.rollback()
        except (SQLAlchemyError, OSError, RuntimeError):
            pass
        raise
    finally:
        release_scoped_db_session()


def clear_request_scoped_orm_caches() -> None:
    """يفرغ كاش طلب ‎cart-event‎ الموروث عبر ‎contextvars‎ (يمنع صفوف ORM منفصلة بعد ‎remove()‎)."""
    try:
        from services.cart_event_request_scope import cart_event_request_end

        cart_event_request_end()
    except Exception:  # noqa: BLE001
        pass


async def release_db_before_async_wait() -> None:
    """قبل ‎asyncio.sleep‎ طويل: لا تُبقي اتصال الـ pool محجوزاً."""
    clear_request_scoped_orm_caches()
    release_scoped_db_session()
