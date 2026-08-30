# -*- coding: utf-8 -*-
"""
Release-before-wait law.

A checked-out DB connection must not remain held across external HTTP,
sleep, or expensive non-DB work.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

log = logging.getLogger("cartflow")

_network_while_held_flag = False


def mark_network_while_held() -> None:
    global _network_while_held_flag
    _network_while_held_flag = True


def consume_network_while_held() -> bool:
    global _network_while_held_flag
    flagged = _network_while_held_flag
    _network_while_held_flag = False
    return flagged


def release_before_external_wait(*, reason: str = "external") -> None:
    """Return the scoped connection before network/sleep/CPU wait."""
    try:
        from services.db_session_lifecycle import release_scoped_db_session

        release_scoped_db_session()
    except Exception as exc:  # noqa: BLE001
        log.warning("[DB RESOURCE SAFETY] release_before_wait failed reason=%s err=%s", reason, exc)


@contextmanager
def external_wait(*, reason: str = "external") -> Iterator[None]:
    release_before_external_wait(reason=reason)
    try:
        yield
    finally:
        pass


__all__ = [
    "consume_network_while_held",
    "external_wait",
    "mark_network_while_held",
    "release_before_external_wait",
]
