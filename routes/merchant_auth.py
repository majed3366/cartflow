# -*- coding: utf-8 -*-
"""Merchant auth HTML routes — login, signup, password reset."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.merchant_auth_http import merchant_cookie_name
from services.merchant_auth_v1 import (
    apply_password_reset,
    authenticate_merchant,
    ensure_merchant_auth_db_ready,
    is_development_env,
    register_merchant_account,
    request_password_reset,
    safe_redirect_path,
    session_cookie_value_for_user,
    validate_login_form,
    reset_token_is_valid,
    validate_reset_password_form,
    validate_signup_form,
)

log = logging.getLogger("cartflow")

_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_ROOT / "templates"))

router = APIRouter(tags=["merchant-auth"])


def _auth_ctx(request: Request, **extra: Any) -> dict[str, Any]:
    return {"request": request, **extra}


def _attach_session_cookie(response: HTMLResponse | RedirectResponse, value: str) -> None:
    secure = not is_development_env()
    response.set_cookie(
        key=merchant_cookie_name(),
        value=value,
        max_age=14 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def _clear_session_cookie(response: RedirectResponse) -> None:
    response.delete_cookie(merchant_cookie_name(), path="/")


@router.get("/login", response_class=HTMLResponse)
def merchant_login_get(
    request: Request,
    next: Optional[str] = Query(None),
    registered: Optional[str] = Query(None),
):
    return templates.TemplateResponse(
        request,
        "merchant_auth_login.html",
        _auth_ctx(
            request,
            next_path=safe_redirect_path(next),
            success_msg="تم إنشاء حسابك. سجّل الدخول للمتابعة."
            if registered
            else "",
        ),
    )


@router.post("/login")
def merchant_login_post(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    next: str = Form("/dashboard"),
):
    ensure_merchant_auth_db_ready()
    ok, err = validate_login_form(email, password)
    if not ok:
        return templates.TemplateResponse(
            request,
            "merchant_auth_login.html",
            _auth_ctx(request, error=err, email=email, next_path=safe_redirect_path(next)),
            status_code=400,
        )
    user = authenticate_merchant(email, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "merchant_auth_login.html",
            _auth_ctx(
                request,
                error="البريد أو كلمة المرور غير صحيحة.",
                email=email,
                next_path=safe_redirect_path(next),
            ),
            status_code=400,
        )
    dest = safe_redirect_path(next)
    resp = RedirectResponse(url=dest, status_code=303)
    _attach_session_cookie(resp, session_cookie_value_for_user(user))
    return resp


@router.get("/signup", response_class=HTMLResponse)
def merchant_signup_get(request: Request):
    return templates.TemplateResponse(
        request,
        "merchant_auth_signup.html",
        _auth_ctx(request),
    )


@router.post("/signup")
def merchant_signup_post(
    request: Request,
    merchant_name: str = Form(""),
    store_name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
):
    ensure_merchant_auth_db_ready()
    ua = (request.headers.get("user-agent") or "")[:120]
    ok, msg, errors = validate_signup_form(
        merchant_name=merchant_name,
        store_name=store_name,
        email=email,
        password=password,
        confirm_password=confirm_password,
    )
    if not ok:
        log.info(
            "[MERCHANT SIGNUP] http outcome=validate_fail fields=%s ua=%s",
            sorted(errors.keys()) if isinstance(errors, dict) else [],
            ua,
        )
        return templates.TemplateResponse(
            request,
            "merchant_auth_signup.html",
            _auth_ctx(
                request,
                error=msg,
                field_errors=errors,
                store_name=store_name,
                email=email,
            ),
            status_code=400,
        )
    reg_ok, reg_msg, user = register_merchant_account(
        merchant_name=merchant_name,
        store_name=store_name,
        email=email,
        password=password,
    )
    if not reg_ok or not user:
        log.info(
            "[MERCHANT SIGNUP] http outcome=create_fail reg_msg=%s ua=%s",
            (reg_msg or "")[:80],
            ua,
        )
        return templates.TemplateResponse(
            request,
            "merchant_auth_signup.html",
            _auth_ctx(
                request,
                error=reg_msg or "تعذر إنشاء الحساب.",
                store_name=store_name,
                email=email,
            ),
            status_code=400,
        )
    log.info("[MERCHANT SIGNUP] http outcome=success user_id=%s ua=%s", user.id, ua)
    dest = safe_redirect_path("/dashboard")
    resp = RedirectResponse(url=dest, status_code=303)
    _attach_session_cookie(resp, session_cookie_value_for_user(user))
    return resp


@router.get("/logout")
def merchant_logout_get():
    resp = RedirectResponse(url="/login", status_code=303)
    _clear_session_cookie(resp)
    return resp


@router.get("/forgot-password", response_class=HTMLResponse)
def merchant_forgot_password_get(request: Request):
    return templates.TemplateResponse(
        request,
        "merchant_auth_forgot_password.html",
        _auth_ctx(request),
    )


@router.post("/forgot-password")
def merchant_forgot_password_post(
    request: Request,
    email: str = Form(""),
):
    msg, dev_url = request_password_reset(email)
    return templates.TemplateResponse(
        request,
        "merchant_auth_forgot_password.html",
        _auth_ctx(
            request,
            success_msg=msg,
            dev_reset_url=dev_url if is_development_env() else None,
            email=email,
        ),
    )


@router.get("/reset-password", response_class=HTMLResponse)
def merchant_reset_password_get(request: Request, token: Optional[str] = Query(None)):
    invalid = not token or not reset_token_is_valid(token)
    return templates.TemplateResponse(
        request,
        "merchant_auth_reset_password.html",
        _auth_ctx(request, token=token or "", invalid_token=invalid),
    )


@router.post("/reset-password")
def merchant_reset_password_post(
    request: Request,
    token: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
):
    ok, msg, _row = validate_reset_password_form(
        token=token,
        password=password,
        confirm_password=confirm_password,
    )
    if not ok:
        return templates.TemplateResponse(
            request,
            "merchant_auth_reset_password.html",
            _auth_ctx(request, token=token, error=msg, invalid_token=True),
            status_code=400,
        )
    applied, apply_msg = apply_password_reset(token=token, password=password)
    if not applied:
        return templates.TemplateResponse(
            request,
            "merchant_auth_reset_password.html",
            _auth_ctx(request, token=token, error=apply_msg, invalid_token=True),
            status_code=400,
        )
    return RedirectResponse(url="/login?registered=1", status_code=303)
