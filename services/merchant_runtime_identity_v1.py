# -*- coding: utf-8 -*-
"""Canonical Merchant UI runtime identity — diagnostics only, no secrets."""
from __future__ import annotations

import json
import os
from typing import Any, Mapping, MutableMapping

from services.deploy_build_info_v1 import resolve_deploy_git_sha
from services.merchant_setup_render_build import MERCHANT_SETUP_RENDER_BUILD
from services.merchant_ui_v2.flag_v1 import (
    COOKIE_MERCHANT_UI_V2,
    FLAG_MERCHANT_UI_V2,
    QUERY_MERCHANT_UI_V2,
    merchant_ui_selection_source,
    merchant_ui_v2_requested,
)

CANONICAL_ROUTE = "/dashboard"
CANONICAL_TEMPLATE = "merchant_app_v2.html"
CANONICAL_RENDERER = "merchant_ui_v2"
CANONICAL_UI_VERSION = "v2"
CANONICAL_SHELL = "utility-row+global-upbar+contextual-sidebar"
CANONICAL_HOME_PAINTER = "CartFlowUiV2Home"
CANONICAL_WORKSPACE_PAINTER = "CartFlowUiV2Workspace"
CANONICAL_HOME_ASSET = "merchant_ui_v2_home.js"
CANONICAL_WORKSPACE_ASSET = "merchant_ui_v2_workspace.js"
CANONICAL_DATA_HOME = "/api/dashboard/summary"
CANONICAL_DATA_WORKSPACE = "/api/cart-workspace/v1/projection"
REVIEW_BIND_ROUTE = "/dev/living-store-home-review"
IDENTITY_ROUTE = "/dev/merchant-runtime-identity"

HEADER_GIT_SHA = "X-CartFlow-Git-Sha"
HEADER_ROUTE = "X-CartFlow-Merchant-Route"
HEADER_UI_VERSION = "X-CartFlow-Merchant-UI-Version"
HEADER_UI = "X-CartFlow-Merchant-Ui"
HEADER_TEMPLATE = "X-CartFlow-Merchant-Template"
HEADER_RENDERER = "X-CartFlow-Merchant-Renderer"
HEADER_SHELL = "X-CartFlow-Merchant-Shell"
HEADER_HOME = "X-CartFlow-Merchant-Home-Painter"
HEADER_WORKSPACE = "X-CartFlow-Merchant-Workspace-Painter"
HEADER_ROLE = "X-CartFlow-Merchant-Role"

_PARITY_KEYS = (
    "renderer_family",
    "shell_family",
    "ui_version",
    "home_renderer_version",
    "workspace_renderer_version",
)


def _v2_identity(*, selection_source: str, role: str = "canonical") -> dict[str, Any]:
    return {
        "ok": True,
        "canonical": True,
        "role": role,
        "git_sha": resolve_deploy_git_sha(short=False),
        "ui_version": CANONICAL_UI_VERSION,
        "template_id": CANONICAL_TEMPLATE,
        "renderer_id": CANONICAL_RENDERER,
        "renderer_family": CANONICAL_RENDERER,
        "shell_version": CANONICAL_SHELL,
        "shell_family": "cf2-shell-v1",
        "home_renderer_version": CANONICAL_HOME_PAINTER,
        "workspace_renderer_version": CANONICAL_WORKSPACE_PAINTER,
        "home_asset": CANONICAL_HOME_ASSET,
        "workspace_asset": CANONICAL_WORKSPACE_ASSET,
        "data_home": CANONICAL_DATA_HOME,
        "data_workspace": CANONICAL_DATA_WORKSPACE,
        "setup_build": MERCHANT_SETUP_RENDER_BUILD,
        "selection_source": selection_source,
        "route": CANONICAL_ROUTE,
        "review_bind_route": REVIEW_BIND_ROUTE,
        "flag": FLAG_MERCHANT_UI_V2,
        "cookie": COOKIE_MERCHANT_UI_V2,
        "query": QUERY_MERCHANT_UI_V2,
        "env_raw": (os.environ.get(FLAG_MERCHANT_UI_V2) or "").strip() or None,
    }


def _v1_identity(*, selection_source: str) -> dict[str, Any]:
    return {
        "ok": True,
        "canonical": False,
        "role": "rollback_only",
        "git_sha": resolve_deploy_git_sha(short=False),
        "ui_version": "v1",
        "template_id": "merchant_app.html",
        "renderer_id": "merchant_ui_v1",
        "renderer_family": "merchant_ui_v1",
        "shell_version": "legacy-rail+app-chrome",
        "shell_family": "v1-rail",
        "home_renderer_version": "HomeExecutiveSummaryV1",
        "workspace_renderer_version": "cart_workspace_merchant_v1",
        "home_asset": "home_executive_summary_v1.js",
        "workspace_asset": "cart_workspace_merchant_v1.js",
        "data_home": CANONICAL_DATA_HOME,
        "data_workspace": CANONICAL_DATA_WORKSPACE,
        "setup_build": MERCHANT_SETUP_RENDER_BUILD,
        "selection_source": selection_source,
        "route": CANONICAL_ROUTE,
        "review_bind_route": REVIEW_BIND_ROUTE,
        "flag": FLAG_MERCHANT_UI_V2,
        "cookie": COOKIE_MERCHANT_UI_V2,
        "query": QUERY_MERCHANT_UI_V2,
        "env_raw": (os.environ.get(FLAG_MERCHANT_UI_V2) or "").strip() or None,
    }


def build_canonical_identity(*, selection_source: str = "default") -> dict[str, Any]:
    return _v2_identity(selection_source=selection_source, role="canonical")


def build_merchant_runtime_identity(
    *,
    ui_v2: bool,
    selection_source: str,
) -> dict[str, Any]:
    if ui_v2:
        return _v2_identity(selection_source=selection_source)
    return _v1_identity(selection_source=selection_source)


def build_identity_from_request(request: Any) -> dict[str, Any]:
    query = getattr(request, "query_params", None) or {}
    cookies = getattr(request, "cookies", None) or {}
    ui_v2 = merchant_ui_v2_requested(query=query, cookies=cookies)
    source = merchant_ui_selection_source(query=query, cookies=cookies)
    return build_merchant_runtime_identity(ui_v2=ui_v2, selection_source=source)


def identity_json(identity: Mapping[str, Any]) -> str:
    return json.dumps(dict(identity), ensure_ascii=True, separators=(",", ":"))


def parity_tuple(identity: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(identity.get(k) or "") for k in _PARITY_KEYS)


def apply_merchant_runtime_identity_headers(
    response: Any,
    identity: Mapping[str, Any],
) -> Any:
    headers = getattr(response, "headers", None)
    if headers is None:
        return response
    headers[HEADER_GIT_SHA] = str(identity.get("git_sha") or "unknown")
    headers[HEADER_ROUTE] = str(identity.get("route") or CANONICAL_ROUTE)
    headers[HEADER_UI_VERSION] = str(identity.get("ui_version") or "")
    headers[HEADER_UI] = str(identity.get("ui_version") or "")
    headers[HEADER_TEMPLATE] = str(identity.get("template_id") or "")
    headers[HEADER_RENDERER] = str(identity.get("renderer_id") or "")
    headers[HEADER_SHELL] = str(identity.get("shell_version") or "")
    headers[HEADER_HOME] = str(identity.get("home_renderer_version") or "")
    headers[HEADER_WORKSPACE] = str(identity.get("workspace_renderer_version") or "")
    headers[HEADER_ROLE] = str(identity.get("role") or "")
    headers.setdefault("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
    return response


def attach_identity_to_template_context(
    ctx: MutableMapping[str, Any],
    identity: Mapping[str, Any],
) -> MutableMapping[str, Any]:
    ctx["merchant_runtime"] = dict(identity)
    ctx["merchant_runtime_json"] = identity_json(identity)
    return ctx


__all__ = [
    "CANONICAL_HOME_PAINTER",
    "CANONICAL_RENDERER",
    "CANONICAL_ROUTE",
    "CANONICAL_SHELL",
    "CANONICAL_TEMPLATE",
    "CANONICAL_UI_VERSION",
    "CANONICAL_WORKSPACE_PAINTER",
    "IDENTITY_ROUTE",
    "REVIEW_BIND_ROUTE",
    "apply_merchant_runtime_identity_headers",
    "attach_identity_to_template_context",
    "build_canonical_identity",
    "build_identity_from_request",
    "build_merchant_runtime_identity",
    "identity_json",
    "parity_tuple",
]
