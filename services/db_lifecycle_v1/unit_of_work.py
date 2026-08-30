# -*- coding: utf-8 -*-
"""
Explicit short unit-of-work.

Read required truth → materialize primitives → close session →
non-DB work → reopen only for final persist.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional

log = logging.getLogger("cartflow")


def release_before_response(*, reason: str = "response") -> None:
    """INV-DB-01 / INV-DB-03: return the connection before render/encode."""
    try:
        from services.db_session_lifecycle import release_scoped_db_session

        release_scoped_db_session()
    except Exception as exc:  # noqa: BLE001
        log.debug("release_before_response reason=%s err=%s", reason, exc)


def close_request_uow_if_clean(*, reason: str = "clean_close") -> bool:
    """Release only when the scoped session has no pending writes (INV-DB-03)."""
    try:
        from extensions import db

        sess = db.session
        if sess.new or sess.dirty or sess.deleted:
            return False
    except Exception:  # noqa: BLE001
        pass
    release_before_response(reason=reason)
    return True


def close_request_uow(*, reason: str = "release") -> None:
    release_before_response(reason=reason)


@contextmanager
def short_db_phase(*, reason: str = "db_phase") -> Generator[Any, None, None]:
    """
    Yield the scoped session for a bounded DB phase, then always release.

    Callers must materialize primitives/DTOs before the context exits.
    """
    from extensions import db

    sess = db.session
    try:
        yield sess
    except Exception:
        try:
            sess.rollback()
        except Exception:  # noqa: BLE001
            pass
        raise
    finally:
        release_before_response(reason=reason)


def materialize_row(obj: Any, fields: tuple[str, ...]) -> Optional[dict[str, Any]]:
    if obj is None:
        return None
    out: dict[str, Any] = {}
    for name in fields:
        try:
            out[name] = getattr(obj, name, None)
        except Exception:  # noqa: BLE001
            out[name] = None
    return out


@contextmanager
def unit_of_work(*, purpose: str, read_only: bool = True) -> Generator[Any, None, None]:
    from extensions import db

    sess = db.session
    try:
        yield sess
        if read_only:
            try:
                sess.rollback()
            except Exception:  # noqa: BLE001
                pass
        else:
            sess.commit()
    except Exception:
        try:
            sess.rollback()
        except Exception:  # noqa: BLE001
            pass
        raise
    finally:
        release_before_response(reason=f"uow:{purpose}")


__all__ = [
    "close_request_uow",
    "close_request_uow_if_clean",
    "materialize_row",
    "release_before_response",
    "short_db_phase",
    "unit_of_work",
]
