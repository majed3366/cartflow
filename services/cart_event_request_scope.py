# -*- coding: utf-8 -*-
"""
طلب واحد ‎POST /api/cart-event‎: تخزين مؤقت لقراءات ‎DB‎ المتكررة + تخطي ‎create_all‎ الزائد بعد ‎warm‎.
"""
from __future__ import annotations

import contextvars
import logging
from typing import Any, Dict, Optional

log = logging.getLogger("cartflow")

_ctx: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "cartflow_cart_event_rq", default=None
)
_AFTER_COMMIT_REGISTERED = False


def cart_event_scope_active() -> bool:
    return _ctx.get() is not None


def cart_event_request_begin() -> None:
    """يُستدعى عند بدء المعالجة (بعد ‎warm‎ حيث ينطبق)."""
    _ensure_after_commit_listener()
    _ctx.set(
        {
            "stores": {},
            "reason": {},
            "reason_any": {},
            "cart_value": {},
            "abandoned_sess_cart": {},
            "profile_event_type": None,
            "profile_path": None,
        }
    )


def cart_event_profile_set_meta(
    *,
    event_type: Optional[str] = None,
    path: Optional[str] = None,
) -> None:
    d = _scope_dict()
    if not d:
        return
    if event_type is not None:
        d["profile_event_type"] = event_type
    if path is not None:
        d["profile_path"] = path


def cart_event_profile_take_meta() -> Dict[str, Any]:
    d = _scope_dict()
    if not d:
        return {}
    return {
        "event_type": d.get("profile_event_type"),
        "path": d.get("profile_path"),
    }


def cart_event_request_end() -> None:
    _ctx.set(None)


def cart_event_scope_maybe_skip_schema_create_all() -> bool:
    """
    بعد ‎_ensure_cartflow_api_db_warmed‎ في نفس طلب الـ‎API‎: تجنّب ‎db.create_all()‎
    داخل دوال مساعدة (يولّد ضغط مفرط على المحلّل/المتصفح للمخطط).
    """
    return cart_event_scope_active()


def cart_event_scope_invalidate_after_commit() -> None:
    d = _ctx.get()
    if not d:
        return
    d["reason"].clear()
    d["reason_any"].clear()
    d["cart_value"].clear()
    d["abandoned_sess_cart"].clear()


def _scope_dict() -> Optional[Dict[str, Any]]:
    return _ctx.get()


def scoped_store_contains(key: str) -> bool:
    d = _scope_dict()
    return d is not None and key in d["stores"]


def scoped_store_get(key: str) -> Any:
    return _scope_dict()["stores"][key]


def scoped_store_set(key: str, value: Any) -> None:
    d = _scope_dict()
    if d is not None:
        d["stores"][key] = value


def scoped_reason_contains(key: tuple[str, str]) -> bool:
    d = _scope_dict()
    return d is not None and key in d["reason"]


def scoped_reason_get(key: tuple[str, str]) -> Any:
    return _scope_dict()["reason"][key]


def scoped_reason_set(key: tuple[str, str], value: Any) -> None:
    d = _scope_dict()
    if d is not None:
        d["reason"][key] = value


def scoped_reason_any_contains(session_id: str) -> bool:
    d = _scope_dict()
    return d is not None and session_id in d["reason_any"]


def scoped_reason_any_get(session_id: str) -> Any:
    return _scope_dict()["reason_any"][session_id]


def scoped_reason_any_set(session_id: str, value: Any) -> None:
    d = _scope_dict()
    if d is not None:
        d["reason_any"][session_id] = value


def scoped_cart_value_contains(cart_id: str) -> bool:
    d = _scope_dict()
    return d is not None and cart_id in d["cart_value"]


def scoped_cart_value_get(cart_id: str) -> Any:
    return _scope_dict()["cart_value"][cart_id]


def scoped_cart_value_set(cart_id: str, value: Any) -> None:
    d = _scope_dict()
    if d is not None:
        d["cart_value"][cart_id] = value


def scoped_abandoned_list_contains(key: tuple[str, str]) -> bool:
    d = _scope_dict()
    return d is not None and key in d["abandoned_sess_cart"]


def scoped_abandoned_list_get(key: tuple[str, str]) -> List[Any]:
    return _scope_dict()["abandoned_sess_cart"][key]


def scoped_abandoned_list_set(key: tuple[str, str], value: List[Any]) -> None:
    d = _scope_dict()
    if d is not None:
        d["abandoned_sess_cart"][key] = value


def _ensure_after_commit_listener() -> None:
    global _AFTER_COMMIT_REGISTERED
    if _AFTER_COMMIT_REGISTERED:
        return
    try:
        from sqlalchemy import event
        from sqlalchemy.orm import Session

        @event.listens_for(Session, "after_commit", propagate=True)
        def _cart_event_after_commit(_session: Any) -> None:  # noqa: ANN401
            cart_event_scope_invalidate_after_commit()

        _AFTER_COMMIT_REGISTERED = True
    except Exception as exc:  # noqa: BLE001
        log.debug("cart_event after_commit listener skipped: %s", exc)
