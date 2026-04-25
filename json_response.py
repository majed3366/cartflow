# -*- coding: utf-8 -*-
"""JSON عربي ‎UTF-8‎ (بدل ‎ensure_ascii=True‎ الافتراضي)."""
from __future__ import annotations

import json
from typing import Any

from starlette.responses import JSONResponse


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"

    def render(self, content: Any) -> bytes:  # type: ignore[override]
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")


def j(content: Any, status_code: int = 200) -> UTF8JSONResponse:
    return UTF8JSONResponse(content=content, status_code=status_code)
